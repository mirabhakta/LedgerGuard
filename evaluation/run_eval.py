"""Run reproducible LedgerGuard provider evaluations from the command line."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.app.data import QuickBooksDatasetLoader, QuickBooksNormalizer
from backend.app.data.store import NormalizedAccountingStore
from backend.app.models.accounting import RecordType
from backend.app.policy import PolicyEngine, run_prechecks
from backend.app.providers import (
    GeminiBaselineProvider, OpenJevProvider, RulesProvider, SystemOneProvider,
)
from backend.app.services.context_builder import ContextBuilder
from backend.app.services.evaluation_runner import EvaluationCase, EvaluationRunner
from backend.app.services.scenario_loader import load_scenarios


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", choices=("rules", "gemini", "system_one", "openjev"), default="rules"
    )
    parser.add_argument("--dataset", type=Path, default=Path("data/raw/hackathon-100"))
    parser.add_argument("--scenarios", type=Path, default=Path("data/scenarios/scenarios.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()

    store = NormalizedAccountingStore(
        QuickBooksDatasetLoader(args.dataset), QuickBooksNormalizer()
    )
    context_builder = ContextBuilder(store)
    policy = PolicyEngine()
    cases: list[EvaluationCase] = []
    for scenario in load_scenarios(args.scenarios):
        action = scenario.inference_action()
        state = context_builder.build(action)
        account_ids = frozenset(
            record.source_id for record in store.records(action.company_id, RecordType.ACCOUNT)
        )
        precheck = run_prechecks(
            action, state, policy.config, known_account_ids=account_ids
        )
        cases.append(EvaluationCase.from_scenario(scenario, state, precheck))

    providers = {
        "rules": RulesProvider,
        "gemini": GeminiBaselineProvider,
        "system_one": SystemOneProvider,
        "openjev": OpenJevProvider,
    }
    provider = providers[args.provider]()
    try:
        run = await EvaluationRunner(policy).run(tuple(cases), provider, output_dir=args.output)
    finally:
        close = getattr(provider, "aclose", None)
        if close is not None:
            await close()
    print(json.dumps(run.metrics.model_dump(mode="json"), indent=2, allow_nan=False))


if __name__ == "__main__":
    asyncio.run(main())
