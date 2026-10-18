from pathlib import Path

import httpx
import pytest

from backend.app.db import AuditRepository
from backend.app.main import PROJECT_ROOT, create_app
from backend.app.models.risk import ProviderFailure, ProviderFailureCode
from backend.app.policy import PolicyEngine
from backend.app.providers import ProviderRegistry, RulesProvider
from backend.app.services.application import LedgerGuardApplication
from backend.app.services.context_builder import ContextBuilder


def make_service(
    tmp_path: Path,
    normalized_store,
    *,
    repository=None,
    benchmark_dir=None,
    checkpoint_path=None,
):
    providers = ProviderRegistry()
    providers.register("rules", RulesProvider())
    return LedgerGuardApplication(
        repository or AuditRepository(tmp_path / "audit.sqlite3"),
        ContextBuilder(normalized_store), providers, PolicyEngine(),
        scenarios_path=PROJECT_ROOT / "data/scenarios/scenarios.jsonl",
        benchmark_dir=benchmark_dir or tmp_path / "no-benchmarks",
        checkpoint_path=checkpoint_path,
    )


def client_for(service):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test"
    )


class TimeoutProvider:
    async def evaluate(self, state):
        return ProviderFailure(
            provider="timeout-test",
            code=ProviderFailureCode.TIMEOUT,
            message="secret upstream detail must not be returned",
            retryable=True,
            latency_ms=10,
        )


@pytest.mark.asyncio
async def test_health_validation_not_found_and_empty_benchmarks(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    async with client_for(service) as client:
        health = await client.get("/api/health")
        assert health.json() == {"status": "ok", "providers": ["rules"], "scenario_count": 6}
        missing = await client.get("/api/actions/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["code"] == "ACTION_NOT_FOUND"
        invalid = await client.post("/api/demo/run", json={})
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "VALIDATION_ERROR"
        benchmarks = await client.get("/api/benchmarks")
        assert benchmarks.json() == {"status": "not_run", "runs": []}

        schema = (await client.get("/openapi.json")).json()
        expected_paths = {
            "/api/health", "/api/actions", "/api/actions/{action_id}",
            "/api/actions/{action_id}/resolve", "/api/demo/run",
            "/api/benchmarks", "/api/dashboard", "/api/stream",
        }
        assert expected_paths <= set(schema["paths"])
        demo_schema = schema["paths"]["/api/demo/run"]["post"]["responses"]["200"]
        assert demo_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ActionDetailResponse"
        )
        actions_schema = schema["paths"]["/api/actions"]["get"]["responses"]["200"]
        assert actions_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ActionListResponse"
        )
        validation_schema = schema["paths"]["/api/demo/run"]["post"]["responses"]["422"]
        assert validation_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ErrorResponse"
        )

        preflight = await client.options(
            "/api/demo/run",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_safe_hero_flow_idempotency_filters_and_persistence(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    async with client_for(service) as client:
        body = {
            "scenario_id": "safe-normal-payment-001", "provider": "rules",
            "idempotency_key": "safe-run-1",
        }
        first = await client.post("/api/demo/run", json=body)
        assert first.status_code == 200
        detail = first.json()
        assert detail["policy_decision"]["final_action"] == "ALLOW"
        assert detail["execution_result"]["status"] == "SIMULATED"
        assert detail["execution_authorization"]["authorization_type"] == "POLICY_ALLOW"
        policy_event = next(
            event for event in detail["audit_events"] if event["type"] == "policy_decision"
        )
        assert policy_event["created_at"] <= detail["execution_authorization"]["created_at"]
        assert "raw_metadata" not in str(detail)
        assert "sim_" not in str(detail)
        second = await client.post("/api/demo/run", json=body)
        assert second.json()["action_id"] == detail["action_id"]
        conflict = await client.post(
            "/api/demo/run",
            json={
                "scenario_id": "semantic-duplicate-001", "provider": "rules",
                "idempotency_key": "safe-run-1",
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"
        listing = await client.get("/api/actions", params={"final_action": "ALLOW"})
        assert listing.json()["count"] == 1
        assert listing.json()["total"] == 1
        no_wildcard = await client.get("/api/actions", params={"reason_code": "%"})
        assert no_wildcard.json()["total"] == 0
        dashboard = await client.get("/api/dashboard")
        assert dashboard.json()["counts"]["ALLOW"] == 1

    reopened = AuditRepository(tmp_path / "audit.sqlite3")
    restarted = make_service(tmp_path, normalized_store, repository=reopened)
    persisted = restarted.get_action(detail["action_id"])
    assert persisted["execution_result"]["execution_id"] == detail["execution_result"]["execution_id"]


@pytest.mark.asyncio
async def test_review_hero_flow_stale_guard_and_approval(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    async with client_for(service) as client:
        response = await client.post(
            "/api/demo/run",
            json={"scenario_id": "destination-change-001", "provider": "rules"},
        )
        detail = response.json()
        assert detail["policy_decision"]["final_action"] == "REQUIRE_APPROVAL"
        action_id = detail["action_id"]
        stale = await client.post(
            f"/api/actions/{action_id}/resolve",
            json={
                "resolution": "approve", "actor": "reviewer@example.com",
                "assessment_hash": "stale",
            },
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "STALE_REVIEW_RESPONSE"
        approved = await client.post(
            f"/api/actions/{action_id}/resolve",
            json={
                "resolution": "approve", "actor": "reviewer@example.com",
                "assessment_hash": detail["policy_decision"]["assessment_hash"],
            },
        )
        assert approved.status_code == 200
        assert approved.json()["execution_result"]["status"] == "SIMULATED"
        assert approved.json()["execution_authorization"]["authorization_type"] == "HUMAN_APPROVAL"
        duplicate = await client.post(
            f"/api/actions/{action_id}/resolve",
            json={
                "resolution": "approve", "actor": "reviewer@example.com",
                "assessment_hash": detail["policy_decision"]["assessment_hash"],
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_context_request_can_be_resolved_with_provenance(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    async with client_for(service) as client:
        response = await client.post(
            "/api/demo/run",
            json={"scenario_id": "missing-context-001", "provider": "rules"},
        )
        detail = response.json()
        assert detail["policy_decision"]["final_action"] == "REQUEST_CONTEXT"
        resolved = await client.post(
            f"/api/actions/{detail['action_id']}/resolve",
            json={
                "resolution": "provide_context",
                "actor": "operator@example.com",
                "updates": {"vendor_id": "vend-supplier"},
                "provenance": "Operator confirmed vendor from receipt",
            },
        )
        assert resolved.status_code == 200
        payload = resolved.json()
        assert payload["execution_result"]["status"] == "SIMULATED"
        assert payload["human_response"]["provenance"] == "Operator confirmed vendor from receipt"


@pytest.mark.asyncio
async def test_duplicate_hero_flow_and_sse_replay_order(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    async with client_for(service) as client:
        response = await client.post(
            "/api/demo/run",
            json={"scenario_id": "semantic-duplicate-001", "provider": "rules"},
        )
        detail = response.json()
        assert detail["policy_decision"]["final_action"] == "BLOCK"
        assert detail["execution_result"] is None
        types = [event["type"] for event in detail["audit_events"]]
        assert types == ["action_received", "precheck_complete", "policy_decision", "action_blocked"]
        stream = await client.get("/api/stream", params={"once": "true"})
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert "event: action_received" in stream.text
        assert "event: action_blocked" in stream.text
        assert stream.text.index("event: action_received") < stream.text.index("event: action_blocked")

        first_event_id = detail["audit_events"][0]["event_id"]
        resumed = await client.get(
            "/api/stream", params={"once": "true", "last_event_id": first_event_id}
        )
        assert f"id: {first_event_id}\n" not in resumed.text
        assert f"id: {first_event_id + 1}\n" in resumed.text

        header_resumed = await client.get(
            "/api/stream", params={"once": "true"},
            headers={"Last-Event-ID": str(first_event_id)},
        )
        assert f"id: {first_event_id}\n" not in header_resumed.text
        assert f"id: {first_event_id + 1}\n" in header_resumed.text


@pytest.mark.asyncio
async def test_provider_timeout_fails_safe_without_execution_or_secret_leak(
    tmp_path, normalized_store
) -> None:
    service = make_service(tmp_path, normalized_store)
    service.providers.register("timeout", TimeoutProvider())
    async with client_for(service) as client:
        response = await client.post(
            "/api/demo/run",
            json={"scenario_id": "safe-normal-payment-001", "provider": "timeout"},
        )
    assert response.status_code == 200
    detail = response.json()
    assert detail["policy_decision"]["final_action"] == "REQUIRE_APPROVAL"
    assert detail["policy_decision"]["reason_codes"] == ["PROVIDER_TIMEOUT"]
    assert detail["execution_result"] is None
    assert "secret upstream detail" not in response.text


@pytest.mark.asyncio
async def test_benchmark_endpoint_returns_only_measured_artifacts(tmp_path, normalized_store) -> None:
    benchmark_dir = tmp_path / "benchmarks"
    benchmark_dir.mkdir()
    (benchmark_dir / "measured.json").write_text(
        '{"run_id":"r1","created_at":"2026-10-17T00:00:00Z","provider":"rules",'
        '"model_name":"rules-v1","sample_size":6,"metrics":{"accuracy":1.0},'
        '"measured_cost_usd":null}', encoding="utf-8",
    )
    service = make_service(tmp_path, normalized_store, benchmark_dir=benchmark_dir)
    async with client_for(service) as client:
        payload = (await client.get("/api/benchmarks")).json()
    assert payload["status"] == "measured"
    assert payload["runs"][0]["metrics"] == {"accuracy": 1.0}


@pytest.mark.asyncio
async def test_sse_replays_more_than_one_repository_page(tmp_path, normalized_store) -> None:
    service = make_service(tmp_path, normalized_store)
    scenario = service.scenarios["safe-normal-payment-001"]
    action = scenario.inference_action().model_copy(update={"action_id": "bulk-events"})
    service.repository.create_received(
        action, audit_id="bulk-audit", provider="rules",
        scenario_id=scenario.scenario_id, idempotency_key=None,
    )
    for index in range(125):
        service.repository.append_event(
            action.action_id, "bulk-audit", "bulk_event", {"index": index}
        )
    async with client_for(service) as client:
        stream = await client.get("/api/stream", params={"once": "true"})
    assert stream.text.count("event: bulk_event") == 125
    assert "id: 125\n" in stream.text


@pytest.mark.asyncio
async def test_pending_review_can_resume_after_service_restart(tmp_path, normalized_store) -> None:
    checkpoint_path = tmp_path / "workflow.sqlite3"
    repository_path = tmp_path / "audit.sqlite3"
    first_service = make_service(
        tmp_path, normalized_store,
        repository=AuditRepository(repository_path), checkpoint_path=checkpoint_path,
    )
    async with client_for(first_service) as client:
        pending = (
            await client.post(
                "/api/demo/run",
                json={"scenario_id": "destination-change-001", "provider": "rules"},
            )
        ).json()
    await first_service.aclose()

    second_service = make_service(
        tmp_path, normalized_store,
        repository=AuditRepository(repository_path), checkpoint_path=checkpoint_path,
    )
    async with client_for(second_service) as client:
        resumed = await client.post(
            f"/api/actions/{pending['action_id']}/resolve",
            json={
                "resolution": "approve", "actor": "restart-reviewer@example.com",
                "assessment_hash": pending["policy_decision"]["assessment_hash"],
            },
        )
    assert resumed.status_code == 200
    assert resumed.json()["execution_result"]["status"] == "SIMULATED"
    await second_service.aclose()
