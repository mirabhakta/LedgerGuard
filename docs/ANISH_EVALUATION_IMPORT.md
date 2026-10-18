# Anish Evaluation Import Status

The scenario, label, disclosure, and measured Rules benchmark artifacts from
`docs/anish-eval-workstream` are preserved without replacing the current backend
contracts.

## Preserved artifacts

- `data/scenarios/dev.jsonl`: 256 generated development cases.
- `data/scenarios/test.jsonl`: 279 frozen test cases.
- `data/scenarios/hero.jsonl`: 3 demo cases.
- `data/scenarios/splits.json`: company-disjoint split metadata.
- `docs/SCENARIOS.md` and `docs/MODIFICATIONS.md`: recipes and disclosures.
- `evaluation/results/20261018T012911Z/`: canonical measured Rules snapshot.

The three older duplicate Rules result directories were omitted. The canonical
snapshot reports 90.3% safe autonomous coverage and 32.8% unsafe escape on 279
test cases. It is a preliminary baseline, not a production safety claim; the
documented 20% label review is still pending.

## Contract decision

The current runtime contracts in `backend/app/models/`, the deterministic
`PolicyEngine`, `ContextBuilder`, FastAPI/LangGraph layers, and the `rules`,
`gemini`, and `system_one` providers remain authoritative.

The legacy OpenAI-compatible provider, duplicate domain models, generator,
sponsor loader, and evaluation runner from the independent branch were not
merged because they use incompatible action types, risk fields, and scenario
schemas. Keeping those executable files would make the combined repository fail
test collection and could reverse risk semantics.

## Required follow-up

1. Implement a versioned adapter from the imported JSONL schema to the current
   `Scenario` and `ProposedAction` contracts.
2. Rebuild each `AccountingState` through the current context boundary and run
   leakage checks on `AccountingState.inference_view()`.
3. Evaluate Rules, Gemini, and System One using the same state and current
   `PolicyEngine`.
4. Emit artifacts compatible with `GET /api/benchmarks` and publish only
   measured runs with sample size, run ID, model identity, and label-review status.
