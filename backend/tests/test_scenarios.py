import json
from pathlib import Path

from backend.app.data import QuickBooksDatasetLoader, QuickBooksNormalizer
from backend.app.data.store import NormalizedAccountingStore
from backend.app.models import ScenarioType
from backend.app.services.scenario_loader import load_scenarios, validate_scenario_lineage


SCENARIOS = Path("data/scenarios/scenarios.jsonl")


def test_six_scenario_types_are_valid_and_labels_do_not_leak() -> None:
    scenarios = load_scenarios(SCENARIOS)
    assert len(scenarios) == 6
    assert {item.scenario_type for item in scenarios} == set(ScenarioType)
    for scenario in scenarios:
        view = json.dumps(scenario.inference_action().model_dump(mode="json"))
        assert "expected_action" not in view
        assert "expected_risk_flags" not in view
    destination = next(item for item in scenarios if item.scenario_type is ScenarioType.PAYMENT_DESTINATION_CHANGE)
    assert destination.synthetic_fields
    assert destination.proposed_action.destination.is_synthetic


BENCHMARK = Path("data/scenarios/benchmark.jsonl")


def test_benchmark_set_extends_every_scenario_type(dataset_root) -> None:
    demo = load_scenarios(SCENARIOS)
    benchmark = load_scenarios(BENCHMARK)
    demo_ids = {item.scenario_id for item in demo}
    assert demo_ids <= {item.scenario_id for item in benchmark}
    assert len(benchmark) > len(demo)
    assert {item.scenario_type for item in benchmark} == set(ScenarioType)
    store = NormalizedAccountingStore(
        QuickBooksDatasetLoader(dataset_root), QuickBooksNormalizer()
    )
    for scenario in benchmark:
        view = json.dumps(scenario.inference_action().model_dump(mode="json"))
        assert "expected_action" not in view
        assert "expected_risk_flags" not in view
        validate_scenario_lineage(scenario, store)


def test_all_scenario_lineage_exists_in_real_dataset(dataset_root) -> None:
    store = NormalizedAccountingStore(
        QuickBooksDatasetLoader(dataset_root), QuickBooksNormalizer()
    )
    for scenario in load_scenarios(SCENARIOS):
        validate_scenario_lineage(scenario, store)
