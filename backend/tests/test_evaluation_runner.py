import json

import pytest

from backend.app.models import FinalAction, PrecheckResult
from backend.app.policy import PolicyEngine
from backend.app.providers.rules import RulesProvider
from backend.app.services.context_builder import accounting_state_hash
from backend.app.services.evaluation_runner import (
    EvaluationCase, EvaluationRunner, assert_fair_comparison,
)
from backend.tests.test_rules_provider import _state


def _case(case_id="case-1", expected=FinalAction.ALLOW):
    state = _state()
    return EvaluationCase(
        scenario_id=case_id, scenario_version="1", source_record_ids=("b1",),
        expected_action=expected, expected_risk_flags=(), state=state,
        state_hash=accounting_state_hash(state), precheck=PrecheckResult(hard_violation=False),
    )


@pytest.mark.asyncio
async def test_runner_writes_standard_json_and_csv(tmp_path) -> None:
    run = await EvaluationRunner(PolicyEngine()).run(
        (_case(),), RulesProvider(), output_dir=tmp_path
    )
    assert run.sample_size == 1
    assert run.measured_cost_usd is None
    json_files = list(tmp_path.glob("*.json"))
    csv_files = list(tmp_path.glob("*.csv"))
    assert len(json_files) == len(csv_files) == 1
    payload = json.loads(json_files[0].read_text())
    assert payload["sample_size"] == 1
    assert "NaN" not in json_files[0].read_text()


@pytest.mark.asyncio
async def test_state_hash_mismatch_aborts_run() -> None:
    broken = _case().model_copy(update={"state_hash": "bad"})
    with pytest.raises(ValueError, match="state hash mismatch"):
        await EvaluationRunner(PolicyEngine()).run((broken,), RulesProvider())


@pytest.mark.asyncio
async def test_fairness_guard_rejects_label_or_policy_mismatch() -> None:
    runner = EvaluationRunner(PolicyEngine())
    baseline = await runner.run((_case(),), RulesProvider())
    changed_label = await runner.run(
        (_case(expected=FinalAction.BLOCK),), RulesProvider()
    )
    with pytest.raises(ValueError):
        assert_fair_comparison((baseline, changed_label))
    baseline_config = PolicyEngine().config
    altered_policy = await EvaluationRunner(
        PolicyEngine(
            config=baseline_config.model_copy(update={"version": f"{baseline_config.version}-altered"})
        )
    ).run((_case(),), RulesProvider())
    with pytest.raises(ValueError, match="policy config"):
        assert_fair_comparison((baseline, altered_policy))
