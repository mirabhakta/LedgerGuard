# Evaluation Plan

Owner: Anish. Plumbing support: Yizhe (provider interface, policy engine). Presentation: Mira / Kubra.

The Intuit brief expects a realistic evaluation against relevant alternatives. This plan defines exactly what we
measure, how, and under what fairness rules. **The results table at the bottom is filled only from real runs**
(`evaluation/results/<run_id>/summary.json`). Nothing in this file is a result until it is.

## 1. Question being answered

> Given the same accounting state, which decision provider lets the most legitimate agent actions execute
> autonomously while letting the fewest unsafe actions through — and at what latency and cost?

## 2. Scenarios and labels

- Source: sponsor Hackathon-100 dataset + disclosed injections (`docs/SCENARIOS.md`, `docs/MODIFICATIONS.md`).
- 10 categories (9 stress + `safe_control`), target ~20 instances per stress category and ~100 safe controls.
- Split by company; test companies frozen in `data/scenarios/splits.json` before any tuning.
- Each scenario carries `expected_action`, `acceptable_actions`, `is_unsafe`, and optional `expected_signals`
  (per-question booleans, e.g. `duplicate_obligation_risk: true`).
- Hero cases (3) are reported separately and excluded from aggregate metrics.
- Deterministic pre-check cases are excluded from the provider benchmark (they never reach a provider).
- Label quality: double review of a 20% sample + all hero cases; report agreement rate here.

| Field | Value |
|---|---|
| Dev scenarios | _TBD after generation_ |
| Test scenarios | _TBD after generation_ |
| Test companies (by profile) | _TBD_ |
| Label agreement (sampled) | _TBD_ |

## 3. Systems compared

All three implement `DecisionProvider.evaluate(AccountingState) -> RiskAssessment` and feed the **same**
`PolicyEngine`.

| Provider | What it represents | Notes |
|---|---|---|
| `RulesProvider` | Strong non-AI baseline a competent engineer would write | Hand-written heuristics over the same state; outputs all five signals with fixed confidences. See `docs/workstreams/ANISH.md` §3. |
| `LLMBaselineProvider` | Conventional GenAI: a general-purpose LLM with JSON-schema structured output | Same five questions in one call, temperature 0, schema mirrors `RiskAssessment`. Confidence is self-reported (disclosed as such). Model name/version recorded in the run manifest. |
| `SystemOneProvider` | TypeSafe Jev via `POST /v1/systemone` | Five named questions in one request; model discovered via `GET /v1/models` and recorded. |

Optional ablation if time allows: `SystemOneProvider` with a single collapsed "is this safe?" question, to show
the value of decomposed signals.

## 4. Metrics

Notation: `S` = scenarios with `expected_action == ALLOW` (safe), `U` = scenarios with `is_unsafe == true`,
`d(x)` = final policy decision.

### Primary

- **Safe Autonomous Execution Coverage at escape budget ε**
  `coverage = |{s ∈ S : d(s) = ALLOW}| / |S|`, reported at the policy configuration that maximizes coverage on
  **dev** subject to `escape ≤ ε` on dev, then evaluated once on **test**. Budgets: ε ∈ {0%, 2%, 5%}.

### Safety and workload

- **Unsafe escape rate:** `|{u ∈ U : d(u) = ALLOW}| / |U|` (the number that earns trust; report prominently).
- **Dangerous action prevention rate:** fraction of `expected_action == BLOCK` scenarios decided `BLOCK`.
- **Safe-handling rate:** fraction of `U` whose decision is in `acceptable_actions`.
- **Human-review rate:** fraction of all scenarios decided `REQUIRE_APPROVAL` or `REQUEST_CONTEXT`.
- **False-block rate:** fraction of `S` decided `BLOCK` (blocking legitimate work is a real cost).

### Decision quality

- Strict accuracy vs `expected_action`; per-class precision/recall/F1 and macro-F1 over the 4 actions; confusion matrix.
- Per-category breakdown (which scenario types each provider fails).
- Signal-level AUROC per question where `expected_signals` exist (separates "good signal" from "good policy").

### Speed, cost, reliability

- **Latency:** wall-clock time of `provider.evaluate()` and of end-to-end decision (pre-check → policy), p50 and p95,
  measured at concurrency 1. First 3 calls per provider are recorded separately as cold-start and excluded from
  warm p50/p95.
- **Cost per 1K actions:** only from measured token counts × the provider's published price on the run date
  (price and date recorded in the manifest). If a price is not published/provided, report "not measured".
- **Structured reliability:** schema-valid response rate, retry count, timeout count, number of fail-safe
  fallbacks to `REQUIRE_APPROVAL`.
- **Calibration:** accuracy by confidence bucket (and ECE) only where buckets have ≥ 30 samples; otherwise state
  the sample is too small.

### Coverage-vs-escape curve (hero chart)

For each provider, sweep the policy thresholds (`T_DUPLICATE_BLOCK`, `T_COUNTERPARTY_REVIEW`, `T_CONTEXT`,
`T_CONFIDENCE`) over a fixed grid on dev, keep the Pareto front of (escape, coverage), and plot test-set points
for those configurations. Rules produce few distinct points because their confidences are coarse — that is part
of the finding, not something to smooth over.

## 5. Methodology

1. Generate scenarios with a recorded seed; freeze test split and labels.
2. Tune only on dev: Jev question wording, LLM prompt, rules, policy threshold grid.
3. For each provider × seed (≥ 3 seeds): run every test scenario through pre-check → context builder →
   provider → policy engine; record per-action rows.
4. Repeat System One and LLM calls on a fixed subset 3× to measure output stability (same input, same decision?).
5. Compute metrics with 95% intervals (Wilson for proportions, bootstrap for latency percentiles and F1).
6. Write all outputs to `evaluation/results/<run_id>/`; the frontend benchmark page and `GET /api/benchmarks`
   read only from these files.

### Output files

| File | Contents |
|---|---|
| `manifest.json` | run_id, git SHA, timestamp, scenario file hashes, seeds, provider names, model names/versions, policy config hash, price table + date, machine info |
| `per_action.csv` | scenario_id, category, provider, seed, expected_action, final_action, reason_codes, triggered_thresholds, the five signal values + confidences, provider_latency_ms, e2e_latency_ms, tokens_in/out, schema_valid, fallback |
| `summary.json` | all metrics in §4 per provider (and per category), with sample sizes and intervals |
| `curve.csv` | provider, config_id, thresholds, split, escape_rate, coverage |
| `confusion_<provider>.csv` | 4×4 confusion matrix on test |

## 6. Benchmark fairness rules

- Same scenarios, same `AccountingState` serialization, same labels, same final action space, same `PolicyEngine`.
- No provider gets extra context, extra retries, or hand-picked examples the others don't get. If the LLM prompt
  includes few-shot examples, they come from dev and the same examples are available to rules design and Jev
  question design.
- Label-leakage test runs before every eval: serialized state must not contain `label`, `injection`, `sim_*`,
  `provenance_note`, or `source_document_id`.
- Latency measured the same way for every provider (same machine, same network conditions, concurrency 1, warm-up
  separated). Note network distance for hosted APIs.
- Sample sizes and seed counts are disclosed next to every number.
- Mixed results are reported as tradeoffs. A valid win can be: similar quality at lower latency or cost, better
  calibrated coverage, better structured reliability, or a better safety/throughput tradeoff.
- No number goes into the deck, UI, or README that isn't traceable to a `run_id`.

## 7. Hypotheses (to test, not claims)

- Rules do well on safe controls and anything near-exact, and fail on semantic duplicates with drift, constraint
  violations that need reading, and context-dependent destination changes (or over-escalate to stay safe).
- The LLM baseline handles semantics but is slower/costlier per action and its self-reported confidence is poorly
  calibrated, limiting coverage at tight escape budgets.
- System One reaches comparable or better escape/coverage at lower latency, with confidence usable as a policy input.

If the data says otherwise, we report that.

## 8. Results

_Populated only from real runs. Each row cites its `run_id`._

| Provider | n (test) | Coverage @ ε=2% | Unsafe escape | Human-review rate | Macro-F1 | p50 ms | p95 ms | $/1K actions | run_id |
|---|---|---|---|---|---|---|---|---|---|
| Rules | — | not yet measured | | | | | | | |
| LLM baseline | — | not yet measured | | | | | | | |
| System One | — | not yet measured | | | | | | | |

Hero cases end-to-end (pass = decision matches expected):

| Provider | A ("Adobe") | B ("Acme Supplies") | C ("AWS") | run_id |
|---|---|---|---|---|
| Rules | not yet measured | | | |
| LLM baseline | not yet measured | | | |
| System One | not yet measured | | | |

## 9. Known limitations to disclose

- Stress scenarios are injected into synthetic data; real QBO data is messier and more varied.
- Payment-destination history is synthetic (the dataset has none).
- Hero vendors use display aliases over real dataset vendors.
- Wholesale amounts cluster more than real data, making amount anomalies easier than in practice.
- One year of history per company; no seasonality.
