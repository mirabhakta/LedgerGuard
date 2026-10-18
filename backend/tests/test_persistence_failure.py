import httpx
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from backend.app.db import AuditRepository
from backend.app.main import create_app
from backend.app.policy import PolicyEngine, run_prechecks
from backend.tests.test_api_contract import make_service
from backend.app.providers import RulesProvider
from backend.app.tools import PersistentSimulatedExecutionTool


class FailingIntentRepository(AuditRepository):
    def begin_execution(self, action_id, execution_id, audit_id):
        raise RuntimeError("injected persistence failure")


class FailCompletionOnceRepository(AuditRepository):
    failed = False

    def complete_execution(self, result):
        if not self.failed:
            self.failed = True
            raise RuntimeError("injected completion failure")
        return super().complete_execution(result)


@pytest.mark.asyncio
async def test_execution_intent_persistence_failure_never_executes(tmp_path, normalized_store) -> None:
    repository = FailingIntentRepository(tmp_path / "failed.sqlite3")
    service = make_service(tmp_path, normalized_store, repository=repository)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/demo/run",
            json={"scenario_id": "safe-normal-payment-001", "provider": "rules"},
        )
    assert response.status_code == 500
    assert response.json()["code"] == "WORKFLOW_ERROR"
    action_id = repository.list_actions(limit=1, offset=0)[0]["action_id"]
    assert repository.get_execution(action_id) is None


def test_idempotent_insert_is_safe_across_separate_database_connections(
    tmp_path, normalized_store
) -> None:
    path = tmp_path / "concurrent.sqlite3"
    repositories = (AuditRepository(path), AuditRepository(path))
    service = make_service(tmp_path, normalized_store, repository=repositories[0])
    scenario = service.scenarios["safe-normal-payment-001"]
    barrier = Barrier(2)

    def insert(index: int) -> str:
        action = scenario.inference_action().model_copy(
            update={"action_id": f"concurrent-{index}"}
        )
        barrier.wait()
        return repositories[index].create_received(
            action,
            audit_id=f"audit-{index}",
            provider="rules",
            scenario_id=scenario.scenario_id,
            idempotency_key="shared-key",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(insert, range(2)))
    assert results[0] == results[1]
    assert repositories[0].count_actions() == 1
    for repository in repositories:
        repository.close()


@pytest.mark.asyncio
async def test_simulated_execution_recovers_same_persisted_intent_after_completion_failure(
    tmp_path, normalized_store
) -> None:
    repository = FailCompletionOnceRepository(tmp_path / "recover.sqlite3")
    service = make_service(tmp_path, normalized_store, repository=repository)
    scenario = service.scenarios["safe-normal-payment-001"]
    action = scenario.inference_action().model_copy(update={"action_id": "recover-action"})
    repository.create_received(
        action, audit_id="recover-audit", provider="rules",
        scenario_id=scenario.scenario_id, idempotency_key=None,
    )
    state = service.context_builder.build(action)
    precheck = run_prechecks(action, state, service.policy.config)
    outcome = await RulesProvider().evaluate(state)
    decision = PolicyEngine().decide(
        action, precheck, outcome, audit_id="recover-audit"
    )
    tool = PersistentSimulatedExecutionTool(repository)
    with pytest.raises(RuntimeError, match="completion failure"):
        tool.execute(action, decision)
    intent = repository.get_execution_intent(action.action_id)
    assert intent is not None
    recovered = tool.execute(action, decision)
    assert recovered.execution_id == intent["execution_id"]
    assert recovered.status == "SIMULATED"
