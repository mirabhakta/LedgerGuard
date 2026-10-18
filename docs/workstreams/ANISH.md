# Workstream — Anish: Scenarios, Labels, Baselines, Evaluation

Spec references: `docs/FINAL_SPEC.md` §16–18, §22, §24–25. Contracts: `docs/BACKEND_INTERFACE_CONTRACTS.md`.
Rules: `AGENTS.md`, `docs/CODING_ASSISTANT_RULES.md`.

## 1. What I own — status

| Deliverable | Path | Status |
|---|---|---|
| Sponsor data loader (read-only, strips leaky fields) | `backend/app/services/sponsor_data.py` | done |
| Context assembly for `Scenario.original_data` (shared with the live app) | `backend/app/services/accounting_context.py` | done |
| Seeded scenario generator + hero cases | `evaluation/generate_scenarios.py` → `data/scenarios/` | done (seed 1337) |
| Labels + disclosure log | scenario labels, `docs/MODIFICATIONS.md` | done; 20% label review pending |
| `RulesProvider` | `backend/app/providers/rules.py` | done |
| `LLMBaselineProvider` | `backend/app/providers/llm.py` | done; needs an API key to run |
| Shared question wording | `backend/app/providers/questions.py` | done (System One should import it) |
| Metrics | `backend/app/services/metrics.py` | done |
| Leakage audit | `evaluation/leakage.py` | done (eval aborts on leaks) |
| Evaluation runner | `evaluation/run_eval.py` | done |
| Benchmark results | `evaluation/results/<run_id>/` | rules measured; LLM + System One pending |
| Evaluation plan + results table | `docs/EVAL_PLAN.md` | rules row filled |

The canonical contract files (`backend/app/models/*`, `policy/config.py`, `policy/engine.py`,
`services/context_builder.py`, `providers/base.py`, `providers/helpers.py`) are committed verbatim from the
contract doc, with one fix: `CandidateMatch.date` is annotated `dt.date` because the bare `date` annotation is
shadowed by the field name and Pydantic cannot build the model. Yizhe owns these files.

Not mine: `SystemOneProvider`, deterministic pre-checks, FastAPI routes, LangGraph, frontend.

## 2. Commands

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m pytest                                              # 41 tests
.venv/bin/python -m evaluation.generate_scenarios --seed 1337           # needs data/company-*/
.venv/bin/python -m evaluation.run_eval --providers rules,llm,system_one \
  --dev data/scenarios/dev.jsonl --test data/scenarios/test.jsonl --hero data/scenarios/hero.jsonl
```

For the LLM baseline, set `LLM_BASELINE_BASE_URL`, `LLM_BASELINE_MODEL`, `LLM_BASELINE_API_KEY` (see
`.env.example`; export them, the runner does not read `.env`). Pass `--price-in-per-mtok`, `--price-out-per-mtok`,
and `--price-date` from the provider's published price to get $/1K actions; otherwise cost is reported as null.

## 3. How the eval plugs into the contracts

```
Scenario (data/scenarios/*.jsonl)
  -> build_accounting_state(scenario)                 # same function as the live app
  -> provider.evaluate(state) -> RiskAssessment       # once per scenario per repeat
  -> PolicyEngine().decide(state, assessment, PrecheckResult(), PolicyConfig(...))
```

- `system_one` is loaded from `backend.app.providers.system_one.SystemOneProvider` (uses `.from_env()` if it
  exists, else the no-arg constructor). Until that module exists it is skipped and listed in the manifest.
- The threshold sweep builds `PolicyConfig` objects and re-runs only `decide`, never the provider.

## 4. RulesProvider design

Uses only `AccountingState`. All constants in `RulesConfig`, tuned on dev.

| Signal | Heuristic |
|---|---|
| `duplicate_obligation_risk` | Closest candidate (same counterparty or ledger match): ≤ 2% amount and ≤ 5 days → 0.92; ≤ 5% and ≤ 10 days → 0.65; else 0.05 |
| `counterparty_change_risk` | Destination changed and first seen ≤ 14 days ago → 0.9; never-paid payee → 0.6; else 0.05 |
| `missing_context_risk` | Payments: base 0.1, +0.35 no source document, +0.3 unknown payee, +0.25 short/vague memo |
| `action_anomaly_risk` | Robust z of amount vs vendor median scaled into [0, 1]; ≥ 2× median → 0.85; personal-merchant or transfer keywords → 0.85 |
| `goal_misalignment_risk` | Regex over `user_constraints.rules`: "do not pay X" naming the payee, or "only pay <role>" not matching the payee → 0.95; else 0.05 |

## 5. LLMBaselineProvider design

- One `POST {base_url}/chat/completions` per action via httpx (OpenAI-compatible), `temperature=0`,
  `response_format` = strict JSON schema mirroring the five `RiskSignal`s, 20 s timeout, 1 retry.
- System prompt asks the five questions from `providers/questions.py`; user message is
  `state.model_dump_json(exclude={"scenario_id"})`.
- Any timeout, HTTP error, invalid JSON, missing or out-of-range field → `provider_error_assessment(...)`
  (`had_error=True`) → `PolicyEngine` returns `REQUIRE_APPROVAL` with `fail_safe_triggered`.
- Records token usage (`last_usage`) for cost; confidence is self-reported and disclosed as such.

## 6. Tests (`backend/tests/`)

| File | Covers |
|---|---|
| `test_policy_engine.py` | each threshold, config-driven thresholds, low confidence, provider-error fail-safe, precheck block |
| `test_rules_provider.py` | each heuristic on crafted states, schema validity |
| `test_llm_provider.py` | valid parse, malformed JSON / missing signal / out of range / missing confidence, HTTP 503, timeout, retry recovery, env check; all via `httpx.MockTransport` |
| `test_metrics.py` | coverage, escape, prevention, review, false-block, accuracy, F1, percentiles, Wilson CI |
| `test_scenarios.py` | recipe labels, acceptable actions, unique opaque ids, disjoint company splits, hero cases, no label leakage, leaky-field stripping |

## 7. Remaining checklist

- [ ] Phase 0 with Yizhe: pick 10–20 dev scenarios across categories for the Jev feasibility gate
- [ ] Run the LLM baseline on dev + test (`--repeats 3` on a subset for stability); fill `docs/EVAL_PLAN.md` §8
- [ ] Run System One once `SystemOneProvider` lands; fill §8
- [ ] Generate 2 more seeds and report spread across seeds
- [ ] 20% label review by two teammates; record agreement in `docs/EVAL_PLAN.md` §2
- [ ] Hand `summary.json` / `curve.csv` to Mira and Kubra for the benchmark page and deck

## 8. Definition of done

- Every number in UI/deck traces to a `run_id` in `evaluation/results/`.
- All three providers run through the same `build_accounting_state` → `PolicyEngine` path.
- Test split frozen before tuning; leakage check passes.
- All injections disclosed in `docs/MODIFICATIONS.md`.
- Results include sample sizes and seeds, and report tradeoffs honestly, including where System One loses.
