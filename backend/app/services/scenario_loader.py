"""JSONL scenario loading with source-lineage validation."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.data.store import NormalizedAccountingStore
from backend.app.models.accounting import RecordType
from backend.app.models.scenario import Scenario


def load_scenarios(path: Path) -> tuple[Scenario, ...]:
    scenarios: list[Scenario] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        scenario = Scenario.model_validate_json(line)
        if scenario.scenario_id in seen:
            raise ValueError(f"duplicate scenario_id at line {line_number}")
        seen.add(scenario.scenario_id)
        scenarios.append(scenario)
    return tuple(scenarios)


def validate_scenario_lineage(scenario: Scenario, store: NormalizedAccountingStore) -> None:
    ids = {
        record.source_id
        for record_type in RecordType
        for record in store.records(scenario.source_company_id, record_type)
    }
    missing = set(scenario.source_record_ids) - ids
    if missing:
        raise ValueError(f"scenario source records not found: {sorted(missing)}")
    if scenario.proposed_action.company_id != scenario.source_company_id:
        raise ValueError("scenario action crosses company scope")
    serialized_action = json.dumps(scenario.inference_action().model_dump(mode="json"))
    if "expected_action" in serialized_action or "expected_risk_flags" in serialized_action:
        raise ValueError("scenario labels leaked into inference action")
