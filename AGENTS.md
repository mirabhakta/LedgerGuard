# AGENTS.md — LedgerGuard

Instructions for any coding assistant (Cursor, Claude Code, Codex, etc.) working in this repository.
Read this file fully before changing code. Scope is **frozen**; see `docs/FINAL_SPEC.md` for the source of truth.

## What this project is

LedgerGuard is an execution-time safety firewall for autonomous financial (accounting) agents, built for
LA Hacks 2026 — Intuit challenge "QuickBooks: Reimagining Accounting With System One Models"
(Applied Intelligence track).

Before an agent performs a financial action (e.g. pay a vendor bill), LedgerGuard evaluates the proposed
action and returns exactly one of:

`ALLOW` | `REQUIRE_APPROVAL` | `REQUEST_CONTEXT` | `BLOCK`

> **System One handles judgment. Code handles authority.**
> LangGraph orchestrates. LangChain connects. System One judges. Policy code authorizes. LedgerGuard protects.

It is **not** a chatbot, a transaction categorizer, a fraud-detection platform, or a QuickBooks clone.

## Pipeline (do not reorder or merge stages)

```
Proposed action
  -> 1. Deterministic pre-checks        (code: limits, malformed fields, exact dupes, allowlists)
  -> 2. Context builder                 (code: compact AccountingState, never the full ledger)
  -> 3. DecisionProvider.evaluate()     (System One / LLM baseline / Rules -> RiskAssessment)
  -> 4. PolicyEngine                    (code: thresholds from one config -> PolicyDecision)
  -> 5. Audit record                    (signals, thresholds, reason codes, latency)
  -> Simulated execution only
```

System One (TypeSafe Jev, `POST /v1/systemone`, model name discovered via `GET /v1/models`) answers five
separate semantic questions per action: `goal_alignment`, `duplicate_obligation_risk`,
`counterparty_change_risk`, `missing_context`, `action_anomaly`. Never collapse them into one "is this safe?".

## Hard rules (non-negotiable)

Full numbered list: `docs/CODING_ASSISTANT_RULES.md`. The ones most often violated:

1. **No scope changes, no chatbot UI.** The hero UI is a live operations/safety console.
2. **No new infrastructure** (Kafka, Redis, k8s, vector DB, microservices, event bus) without explicit approval.
3. **System One lives only behind `SystemOneProvider`.** No Jev calls from route handlers, graph nodes, or UI.
4. **Final authority is `PolicyEngine`.** Model / LLM / LangGraph output never executes or authorizes an action.
5. **Deterministic facts in code** (arithmetic, dates, thresholds, exact matches, allowlists). Semantic judgment in providers.
6. **Never fabricate** benchmark numbers, probabilities, confidences, costs, or latencies — in code, UI, docs, or pitch.
   Mock data must be visibly labeled as mock.
7. **No real money movement.** Execution is a sandbox state transition.
8. **Never commit secrets.** Use `.env` locally (gitignored) and env vars in deployment.
9. **Typed Pydantic contracts.** Every provider returns the same `RiskAssessment` schema.
10. **Contract changes** must update `docs/API_CONTRACT.md` and both backend and frontend in the same change.
11. **Every decision records reason codes and the triggering threshold(s).** Thresholds live in one policy config.
12. **Fail safe.** If System One / the LLM / the workflow engine is unavailable or returns malformed output,
    the action goes to `REQUIRE_APPROVAL` (or `BLOCK`), never silent `ALLOW`.
13. **Benchmark fairness.** Rules, LLM, and System One get the identical `AccountingState`, labels, action space,
    and policy layer. No hidden extra context for any provider.
14. **No label leakage.** Strip `provenance_note`, `sim_*`, `source_document_id`, and scenario labels from any
    state sent to a provider.
15. **Prefer plain Python** over LangChain abstractions; keep LangGraph nodes small and single-purpose; no
    supervisor/multi-agent hierarchies.

## Repository layout (target)

```
backend/app/
  api/          HTTP surface only (FastAPI routes)
  models/       Pydantic contracts: action, state, risk, policy
  providers/    base.py (DecisionProvider), system_one.py, llm.py, rules.py
  policy/       engine.py, config.py  (deterministic authority)
  services/     context_builder, scenario_loader, replay, audit, metrics
  graph/        LangGraph orchestration only (state, graph, routing, nodes/)
  tools/        fact retrieval + simulated actions
  db/           SQLite models/session
backend/tests/
frontend/src/   React + TypeScript + Vite (pages, components, api, types)
data/           sponsor dataset (company-001..100, gitignored) + scenarios/ + labeled/
evaluation/     run_eval.py, results/ (machine-readable JSON/CSV, real runs only)
docs/           specs, contracts, eval plan, demo script, workstreams
```

## Stack

Backend: Python 3.12+, FastAPI, Pydantic, httpx (async), SQLite, SSE, pandas/PyArrow, pytest(-asyncio).
Orchestration: LangGraph (+ SQLite checkpointer for human-in-the-loop). LangChain only where it helps
(LLM baseline structured output, tool wrappers). Frontend: React, TypeScript, Vite, Recharts.
Evaluation: pandas, scikit-learn, custom safety/coverage/latency metrics.

## Sponsor dataset — conventions you must respect

- Location: `data/company-XXX/rwm-v4/world-<dataset_id>/*.yaml` (lookup `dataset_id` in `data/index.json`).
  Schema: `SCHEMA.md` inside each company dir; overview: `data/DATA_README.md`.
- 100 synthetic companies, 7 profiles, one year of books ending early Oct 2026. **IDs are company-scoped** —
  always key by `(company_id, id)`.
- Money is decimal strings (`"1234.56"`). Use `Decimal` or integer cents, never floats, for money math.
- Bank `amount` is already signed (+ in, − out). The bank feed matches the books exactly (no natural mess).
- Vendors have **no payment-destination / bank-account fields** and there are **no Adobe/AWS/Acme vendors**:
  hero cases and destination-change scenarios are injected and must be disclosed (`docs/MODIFICATIONS.md`).
- Do not use `hidden/` data (organizer-only; not in our copy).
- Do not commit the raw dataset (~400 MB).
- Any modification to sponsor data must be logged in `docs/MODIFICATIONS.md` (source events, exact change,
  reason, expected label, category).

## Scope priority

- **P0:** dataset loaded, contracts, SystemOneProvider, RulesProvider, LLMBaselineProvider, PolicyEngine,
  three hero scenarios, live dashboard, action detail, benchmark script, real latency + safety metrics, demo script.
- **P1:** SSE live replay, human review queue (LangGraph interrupt/resume), more scenarios, coverage chart, audit history.
- **P2 (stretch):** REQUEST_CONTEXT loop, richer planner. Never delay P0 for P1/P2.

## Ownership

| Area | Owner |
|---|---|
| Backend architecture, FastAPI, SystemOneProvider, PolicyEngine, SSE, provider abstraction, LangGraph | Yizhe |
| React dashboard, action detail, review queue, KPI presentation | Mira |
| Scenario generation, labeling, RulesProvider, LLM baseline, evaluation scripts, benchmark results | Anish — see `docs/workstreams/ANISH.md` |
| UI polish, charts, deployment, integration testing, demo video, pitch deck | Kubra |

## Docs index

- `docs/FINAL_SPEC.md` — frozen product + technical spec (source of truth)
- `docs/CODING_ASSISTANT_RULES.md` — full numbered implementation constraints (1–30)
- `docs/EVAL_PLAN.md` — scenarios, labels, baselines, metrics, fairness, results table
- `docs/SCENARIOS.md` — scenario file format and injection recipes against the sponsor data
- `docs/MODIFICATIONS.md` — disclosure log for every change to sponsor data
- `docs/workstreams/ANISH.md` — Anish's workstream: deliverables, interfaces, checklist

## Testing expectations

Add tests for: policy thresholds, provider response parsing, malformed model responses (must fail safe),
scenario ground truth / label integrity, label-leakage checks, and API response schemas.
Evaluation scripts must be reproducible and write JSON/CSV to `evaluation/results/`.
