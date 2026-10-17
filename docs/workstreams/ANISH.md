# Workstream — Anish: Scenarios, Labels, Baselines, Evaluation

Spec references: `docs/FINAL_SPEC.md` §16–18, §22, §24–25. Rules: `AGENTS.md`, `docs/CODING_ASSISTANT_RULES.md`.

## 1. What I own

| Deliverable | Path | Priority |
|---|---|---|
| Dataset loader for scenario generation (read-only over sponsor YAML) | `backend/app/services/scenario_loader.py` (shared with Yizhe) | P0 |
| Seeded scenario generator + hero cases | `data/scenarios/generate.py` → `data/scenarios/{hero,dev,test,precheck}.jsonl`, `splits.json` | P0 |
| Labels + disclosure log | scenario `label` blocks, `docs/MODIFICATIONS.md` | P0 |
| `RulesProvider` | `backend/app/providers/rules.py` | P0 |
| `LLMBaselineProvider` | `backend/app/providers/llm.py` | P0 |
| Evaluation runner + metrics | `evaluation/run_eval.py`, `backend/app/services/metrics.py` | P0 |
| Benchmark results (real runs only) | `evaluation/results/<run_id>/` | P0 |
| Evaluation plan + results table | `docs/EVAL_PLAN.md` | P0 |
| Coverage-vs-escape curve data, calibration buckets | `curve.csv`, `summary.json` | P1 |
| Additional scenarios beyond the 10 categories | `data/scenarios/` | P1 |

Not mine (don't build, just consume): `SystemOneProvider`, `PolicyEngine` + config, Pydantic contracts in
`backend/app/models/`, context builder, FastAPI routes, LangGraph, frontend.

## 2. Interfaces I depend on (agree with Yizhe early)

```python
# backend/app/providers/base.py  (owned by Yizhe)
class DecisionProvider(Protocol):
    name: str
    async def evaluate(self, state: AccountingState) -> RiskAssessment: ...
```

- `AccountingState`, `RiskAssessment`, `PolicyDecision`, `FinalAction` from `backend/app/models/`.
- `PolicyEngine.decide(state, assessment, precheck_result, config) -> PolicyDecision` with thresholds passed in
  via a config object (needed so the eval can sweep thresholds without editing code).
- `build_accounting_state(scenario) -> AccountingState` from the context builder. **The eval uses the same
  function as the live app** — no eval-only serialization.
- `RiskAssessment` must carry, per signal: a value in [0, 1] and a confidence in [0, 1], plus `model_name`,
  `latency_ms`, and an error/fallback flag so the policy can fail safe on malformed provider output.

Until those exist, I write against these signatures and stub minimal versions locally (not committed as the real
implementation).

## 3. RulesProvider design

Goal: the strongest honest non-AI baseline, not a straw man. Uses only fields in `AccountingState`.

| Signal | Heuristic | Confidence |
|---|---|---|
| `duplicate_obligation_risk` | Same vendor (normalized name or id) **and** amount within 2% **and** date within 7 days or same billing month among candidate matches / recent ledger → 0.9; amount within 5% & same month → 0.6; else 0.05 | 0.9 when exact-ish match, 0.6 otherwise |
| `counterparty_change_risk` | Destination `first_seen` within 14 days of `as_of_date` and differs from the vendor's prior destination → 0.85; vendor never paid before → 0.5; else 0.05 | 0.8 |
| `missing_context` | No source document ref, empty/very short memo or line description, or vendor never seen → 0.7; else 0.1 | 0.6 |
| `action_anomaly` | Robust z-score of amount vs vendor history (median/MAD); category not in vendor's historical categories; personal-merchant keyword list → scaled 0–1 | 0.7 |
| `goal_alignment` | Keyword/regex checks of `user_constraints` (vendor names, categories like "utilities", "only", "do not") vs action fields → 0.1 if a constraint keyword is violated, else 0.9 | 0.5 |

All rule constants live in one module-level config dataclass, tuned on dev only. Money math in `Decimal`.

## 4. LLMBaselineProvider design

- One chat-completions call per action through an OpenAI-compatible endpoint (httpx async; LangChain
  `with_structured_output` is acceptable but not required). Base URL, model, and API key from env:
  `LLM_BASELINE_BASE_URL`, `LLM_BASELINE_MODEL`, `LLM_BASELINE_API_KEY`.
- System prompt: the same five questions, word-for-word aligned with the Jev question set; user content: the
  `AccountingState` JSON produced by the shared context builder (identical to what Jev receives).
- JSON-schema structured output mirroring `RiskAssessment` signals: for each signal `{value: float, confidence: float}`.
- `temperature=0`, fixed `max_tokens`, request timeout (e.g. 20 s), at most 1 retry on schema failure; retries
  and timeouts are counted, not hidden.
- Malformed or failed responses → return an assessment flagged `error=True` (no invented values) so the policy
  engine routes to `REQUIRE_APPROVAL`.
- Record `latency_ms`, `tokens_in`, `tokens_out`, model id returned by the API.
- Self-reported confidence is disclosed as "verbalized confidence" in results.

## 5. Evaluation runner

```bash
python -m evaluation.run_eval \
  --scenarios data/scenarios/test.jsonl \
  --providers rules,llm,system_one \
  --seeds 1337,2024,7 \
  --threshold-grid evaluation/threshold_grid.json \
  --out evaluation/results/
```

- Providers are resolved by name; an unavailable provider (missing key/endpoint) is **skipped and reported as
  skipped**, never filled with placeholders.
- Runs the label-leakage check first and aborts on failure.
- Concurrency 1 for latency runs; separate optional throughput run.
- Writes `manifest.json`, `per_action.csv`, `summary.json`, `curve.csv`, `confusion_<provider>.csv`
  (formats in `docs/EVAL_PLAN.md` §5).
- `GET /api/benchmarks` and the frontend benchmark page read the latest `summary.json` / `curve.csv` verbatim.

## 6. Tests I add (`backend/tests/`)

- `test_scenarios.py` — every scenario parses; `expected_action ∈ acceptable_actions`; categories match recipe
  defaults; hero cases present with expected labels; test/dev company sets are disjoint.
- `test_label_leakage.py` — serialized `AccountingState` for every scenario contains no forbidden keys and no
  data dated on/after `as_of_date`.
- `test_rules_provider.py` — each heuristic fires on a minimal crafted state; output validates as `RiskAssessment`.
- `test_llm_provider_parsing.py` — valid JSON → assessment; malformed JSON, missing fields, out-of-range values,
  timeout → `error=True` (and policy yields `REQUIRE_APPROVAL`). Uses recorded/mocked HTTP responses, no network.
- `test_metrics.py` — coverage, escape, review rate, macro-F1, percentile math on hand-computed fixtures.

## 7. Checklist by phase

**Phase 0 (with Yizhe, first 45 min):** hand-write 10–20 ambiguous finance actions from the dataset (mix of
categories 4, 5, 7, 8, 9) for the Jev feasibility gate; record raw outputs; check separation.

**Phase 1:**
- [ ] Agree contracts/signatures in §2 with Yizhe
- [ ] Loader: read one company's vendors, bills, bill_payments, bank_transactions, journal_entries; strip `sim_*`/`provenance_note`/`source_document_id`
- [ ] Pick hero company; draft hero A/B/C

**Phase 2:**
- [ ] Generator for categories 10, 8, 7 first (hero-adjacent), then 1–6, 9
- [ ] Freeze `splits.json` + test labels; fill `docs/MODIFICATIONS.md`
- [ ] `RulesProvider` + tests
- [ ] `LLMBaselineProvider` + parsing tests
- [ ] First eval run with Rules (needs PolicyEngine) → first real numbers

**Phase 5:**
- [ ] Full test run, all providers, ≥ 3 seeds; threshold sweep; curve
- [ ] Populate `docs/EVAL_PLAN.md` §8 from `summary.json` with `run_id`s
- [ ] Hand Mira/Kubra the result files for the benchmark page and deck

## 8. Definition of done

- Every number in UI/deck traces to a `run_id` in `evaluation/results/`.
- Rules and LLM providers return the shared `RiskAssessment` schema and pass their tests.
- Test split was frozen before tuning; leakage check passes.
- All injections disclosed in `docs/MODIFICATIONS.md`.
- Results include sample sizes, seeds, and honest tradeoffs (including where System One loses).
