# LedgerGuard / Agent Firewall — Final Product & Technical Specification

**Status:** FINAL DIRECTION — freeze scope unless core feasibility fails.
**Event:** LA Hacks 2026
**Primary track:** Applied Intelligence
**Company challenge:** Intuit — QuickBooks: Reimagining Accounting With System One Models
**Working product name:** LedgerGuard (name candidates in Appendix A)
**Subtitle:** A System One firewall for autonomous financial agents.

---

## 1. Executive summary

LedgerGuard is a real-time financial safety layer that sits inside an autonomous accounting agent's execution loop.
Before an AI agent performs a financial action, LedgerGuard evaluates the proposed action against business context,
accounting state, history, and user intent.

System One/Jev provides fast, typed, probabilistic judgments for ambiguous semantic risk. A deterministic policy
engine then converts those signals into one of four software actions:

- `ALLOW`
- `REQUIRE_APPROVAL`
- `REQUEST_CONTEXT`
- `BLOCK`

**Core principle: System One handles judgment. Code handles authority.**

The product is not another accounting chatbot, transaction categorizer, fraud detector, or full QuickBooks clone.
It is execution-time safety infrastructure for autonomous financial agents.

## 2. Problem

QuickBooks and modern accounting products already automate categorization, matching, reporting, insights, and
recurring workflows. The next problem is trust.

When an autonomous agent is allowed to take financial actions, a bad decision can create duplicate payments,
mis-posted transactions, unauthorized destination changes, incorrect ledger entries, or expensive month-end cleanup.

The key question: **"Should this proposed financial action be allowed to execute right now?"**
LedgerGuard answers that question before the action touches the ledger or payment workflow.

- **Primary user:** small-business owner, bookkeeper, or finance operator using increasingly autonomous accounting workflows.
- **Job to be done:** "I want AI to automate routine financial work without silently making high-impact accounting mistakes."

## 3. Hero user story

User instruction: *"Pay all outstanding vendor bills due today."*

The financial agent proposes three actions:

| Case | Action | Context | Expected |
|---|---|---|---|
| A | Adobe — $149 | Normal vendor, normal account, normal amount | `ALLOW` |
| B | Acme Supplies — $18,400 | Invoice legitimate, but payment instructions changed yesterday to a new bank account | `REQUIRE_APPROVAL` |
| C | AWS — $4,210 | A similar $4,206 obligation for the same billing period was recorded two days ago | `BLOCK` (or MATCH_EXISTING, depending on scenario setup) |

The demo proves the agent can continue autonomously on safe actions while risky or ambiguous actions are
intercepted in real time.

## 4. Why System One is central

System One is the core semantic decision layer, not a decorative classifier. It fits because:

- The output must be machine-consumable decisions, not prose.
- Every proposed action may require several judgments at once.
- The judgments are contextual and too fuzzy for brittle hand-written rules alone.
- Confidence/probability matters: the software must decide when to act autonomously versus escalate.
- The decision must be fast enough to run inside an agent execution loop.
- Typed output reduces parsing/format failure compared with free-form generation.

**Boundary:** do not use System One for facts that normal code can calculate exactly.

| Deterministic code | System One |
|---|---|
| amount thresholds, date math, exact duplicate IDs, account allowlists, hard payment limits, unsupported currency, malformed fields, known policy violations | goal-action alignment, semantic duplicate-obligation risk, contextual counterparty/payment-change risk, missing-context judgment, action anomaly relative to business history |

## 5. System architecture

```
User Intent
    |
    v
Autonomous Financial Agent
    |
    v
Proposed Financial Action
    |
    v
+--------------------------------------------------+
|                 LEDGERGUARD                      |
|  1. Deterministic Pre-Checks                     |
|  2. Context Builder                              |
|  3. System One / Jev Semantic Risk Evaluation    |
|  4. Deterministic Policy Engine                  |
|  5. Audit Record                                 |
+--------------------------------------------------+
    |
    +-----------+------------------+-----------------+
    v           v                  v                 v
  ALLOW   REQUIRE_APPROVAL   REQUEST_CONTEXT       BLOCK
    |
    v
Simulated Execution
```

No real money movement is required for the hackathon demo.

## 6. Decision flow

1. Agent proposes an action (e.g. `PAY_VENDOR_BILL`).
2. Deterministic pre-checks run: absolute hard limit, missing required data, unsupported recipient, malformed request.
3. Context builder assembles compact financial state. Do not send the full ledger; send only relevant state.
4. System One evaluates multiple semantic questions in one request.
5. Policy engine combines hard rules + model probabilities/confidence.
6. Final action is produced: `ALLOW` / `REQUIRE_APPROVAL` / `REQUEST_CONTEXT` / `BLOCK`.
7. An audit record stores model signals, thresholds, final policy decision, and latency.

## 7. System One question set (P0)

| Key | Question |
|---|---|
| `goal_alignment` | Is the proposed financial action consistent with the user's stated goal and constraints? |
| `duplicate_obligation_risk` | Is this action likely to pay, post, or record a financial obligation that has already been satisfied or represented? |
| `counterparty_change_risk` | How risky or unusual is the proposed counterparty or payment destination given the available business history and context? |
| `missing_context` | Is important information missing such that autonomous execution would be unsafe? |
| `action_anomaly` | How unusual is this proposed action relative to this business's normal financial behavior? |

Use the sponsor-supported System One question types that best fit each decision (yes/no, choice, or score).
Confirm the exact current API schema before implementation. Do not collapse everything into one generic
"Is this safe?" question; decomposition into independent signals is the technical story.

## 8. Core data contracts

**ProposedAction:** `action_id`, `action_type`, `timestamp`, `amount`, `currency`, vendor/counterparty,
destination/account metadata, source document or invoice reference, `proposed_category` (if relevant),
`agent_goal`, `agent_reasoning_summary` (optional, not trusted as fact).

**CandidateMatch:** `ledger_id`, `date`, `amount`, `vendor`, `category`, `description`, `status`.

**BusinessContext:** `business_type`, account, vendor history, historical amount statistics, previous payment
destinations, known accounting patterns, user-defined constraints.

**AccountingState:** `proposed_action`, `candidate_matches`, `business_context`, relevant recent ledger history,
deterministic features.

**RiskAssessment:** `goal_alignment` probability/confidence, `duplicate_obligation` probability/confidence,
`counterparty_change` score/confidence, `missing_context` probability/confidence, `action_anomaly`
score/confidence, `model_name`, `latency_ms`.

**PolicyDecision:** `final_action`, `reason_codes`, `triggered_thresholds`, `provider`, `audit_id`.

**FinalAction enum:** `ALLOW`, `REQUIRE_APPROVAL`, `REQUEST_CONTEXT`, `BLOCK`.

## 9. Decision provider interface

All decision backends expose the same interface so evaluation is apples-to-apples:

```
DecisionProvider.evaluate(AccountingState) -> RiskAssessment
```

Implementations: `SystemOneProvider`, `LLMBaselineProvider`, `RulesProvider`.
Do not duplicate the pipeline per provider:
same state → different provider → same `RiskAssessment` contract → same policy engine → comparable metrics.

## 10. Deterministic policy engine

The model never directly executes financial actions. Illustrative policy (thresholds must be tuned on evaluation data):

```python
if hard_rule_violation:
    BLOCK
elif duplicate_obligation_probability >= T_DUPLICATE_BLOCK:
    BLOCK
elif counterparty_change_risk >= T_COUNTERPARTY_REVIEW:
    REQUIRE_APPROVAL
elif missing_context_probability >= T_CONTEXT:
    REQUEST_CONTEXT
elif minimum_confidence < T_CONFIDENCE:
    REQUIRE_APPROVAL
else:
    ALLOW
```

Thresholds are configuration, not scattered magic numbers. Keep them in one policy config.
Log which threshold caused the decision.

## 11. Backend tech stack

- Python 3.12+, FastAPI, Pydantic
- System One: TypeSafe Jev via `/v1/systemone`; use `/v1/models` to discover the model name (don't hard-code an unverified alias)
- pandas and/or PyArrow
- SQLite (move to PostgreSQL only if a real requirement appears)
- Server-Sent Events for real-time UI
- httpx async
- pytest, pytest-asyncio
- Evaluation: pandas, scikit-learn metrics, custom latency/cost/coverage metrics
- Config: `.env` locally, env vars in deployment, never commit secrets

## 12. Frontend tech stack

React, TypeScript, Vite. React Query or a very small custom fetch layer. Recharts or lightweight charting.
No heavy state management unless necessary. Frontend on Vercel. Backend on Render, Railway, or a reliable
local/public tunnel — choose reliability over architecture purity.

## 13. Backend API

| Endpoint | Purpose |
|---|---|
| `GET /api/dashboard` | `actions_processed`, `allowed`, `require_approval`, `request_context`, `blocked`, `safe_autonomous_execution_rate`, `median_latency_ms`, current provider |
| `GET /api/actions` | Filters: `final_action`, `risk`, `provider`, `scenario` |
| `GET /api/actions/{action_id}` | Proposed action, relevant context, candidate matches, risk assessment, final policy decision, audit details |
| `POST /api/actions/{action_id}/resolve` | Simulated human approval/review; no real financial side effects |
| `POST /api/demo/run` | Runs a named demo scenario |
| `GET /api/stream` | SSE events: `action_received`, `precheck_complete`, `system_one_started`, `risk_assessment_ready`, `policy_decision`, `execution_simulated` |
| `GET /api/benchmarks` | Measured benchmark results. Never return fabricated placeholder numbers as experimental results |

## 14. Frontend / interface spec

**Do not build a chat-first UI.** The hero experience is a live operations + safety console.

**Screen 1 — Live Agent Firewall Dashboard.** Top cards: actions evaluated, safe autonomous execution rate,
approval required, blocked, median decision latency. Main live feed columns:
Action | Amount | Counterparty | Decision | Key risk | Latency. (Example rows in the original spec are
illustrative layout only, not measurements.)

**Screen 2 — Action Detail Drawer.**
- A. Proposed action: who/what, amount, requested action, agent goal
- B. Relevant context: historical vendor behavior, candidate existing obligations, recent payment destination, policy constraints
- C. System One signals (bars/badges): goal alignment, duplicate obligation, counterparty-change risk, missing context, action anomaly
- D. Policy result: large final status, reason codes, threshold triggered, model latency

**Screen 3 — Human Review Queue.** Only ambiguous/high-risk actions. Reviewer buttons simulate:
Approve, Reject, Request more info, Match existing.

**Screen 4 — Benchmark / Evaluation.** Compare Rules vs conventional LLM structured-output baseline vs
System One/Jev on measured unsafe-action escape rate, safe autonomous execution coverage, accuracy/F1 where
meaningful, p50/p95 latency, cost estimate if reliably measurable. Hero visualization:
**Safe Automation Coverage vs. Unsafe Escape Rate.**

## 15. UI principles

- A judge should understand the product in under 10 seconds.
- Avoid finance-dashboard clutter and generic chatbots.
- One visual hierarchy: proposed action → risk signals → final decision.
- Semantic color (safe / warning / blocked), always paired with text/icon for accessibility.
- Do not invent model confidence values in the live product. Show real outputs or clearly labeled mocked demo data.
- Preserve an audit trail.

## 16. Dataset strategy

Use the sponsor-provided synthetic QuickBooks dataset as the base. Do not rebuild a dataset from scratch.
Add disclosed stress-test scenarios only when needed for evaluation. For every injected case record:
source event(s), exact modification, reason, expected ground-truth action, scenario category.

Recommended stress scenarios:

1. Duplicate Stripe deposit
2. Payroll journal entry + bank-feed settlement representing the same obligation
3. Internal transfer incorrectly treated as a new expense
4. Ambiguous vendor with insufficient business-purpose context
5. Abnormally large but potentially legitimate vendor payment
6. Personal-looking expense mixed into business activity
7. Vendor payment instructions changed shortly before payment
8. Similar invoice with small amount/date differences representing the same obligation
9. Agent action inconsistent with explicit user constraint
10. Safe ordinary vendor payment (control cases)

Detailed recipes: `docs/SCENARIOS.md`. Disclosure log: `docs/MODIFICATIONS.md`.

## 17. Evaluation plan (summary)

P0 baselines: `RulesProvider`, `LLMBaselineProvider`, `SystemOneProvider`, all on the same `AccountingState`
and final policy contract.

**Primary metric: Safe Autonomous Execution Coverage** — at a chosen maximum unsafe-action escape threshold,
the percentage of legitimate actions that execute without human review.

Additional: unsafe action escape rate, dangerous action prevention rate, human-review rate, precision/recall/F1,
p50/p95 latency, estimated cost per 1K actions (if measured honestly), calibration by confidence bucket.

Principle: System One does not need to be perfect; the system should know when not to trust a decision.
Uncertainty becomes a software control primitive. Full plan: `docs/EVAL_PLAN.md`.

## 18. Benchmark fairness

Same scenarios, same input information, same labels, same final action space, same policy layer where possible,
no hidden extra context for one provider, consistent cold/warm latency measurement, enough repeated runs,
disclosed sample size. Never fabricate numbers. Report mixed results honestly. A valid win can be similar quality
at lower latency or cost, better calibrated coverage, better structured reliability, or a better overall
safety/throughput tradeoff.

## 19. Repository structure

```
ledgerguard/
  backend/app/{main.py, api/, models/, providers/, policy/, services/, db/, graph/, tools/}
  backend/tests/
  frontend/src/{pages, components, api, types}
  data/{raw|company-*, scenarios, labeled}
  evaluation/{run_eval.py, results/}
  docs/{PRODUCT_SPEC, TECH_SPEC, API_CONTRACT, EVAL_PLAN, DEMO_SCRIPT, CODING_ASSISTANT_RULES}.md
  README.md
```

## 20. Required project documents

| Doc | Must contain | Owner |
|---|---|---|
| `PRODUCT_SPEC.md` | problem, target user, user story, scope, non-goals, success criteria, screens | Mira |
| `TECH_SPEC.md` | architecture, System One role, deterministic vs probabilistic boundary, data contracts, provider abstraction, policy engine, persistence, SSE flow | Yizhe |
| `API_CONTRACT.md` | endpoints, request/response schemas, error cases, enums, one canonical example per endpoint | Yizhe |
| `EVAL_PLAN.md` | scenarios, labels, baselines, metrics, methodology, fairness rules, real-measurement results table | Anish (written) |
| `DEMO_SCRIPT.md` | exact demo sequence, three hero cases, spoken transitions, fallback screenshots/video | Kubra |
| `CODING_ASSISTANT_RULES.md` | implementation constraints | written |

## 21. Coding assistant rules

See `docs/CODING_ASSISTANT_RULES.md` (rules 1–30 plus project-specific data rules).

## 22. Scope

- **P0 — must ship:** sponsor dataset loaded; `ProposedAction`/`AccountingState` contracts; SystemOneProvider;
  RulesProvider; LLMBaselineProvider (or one credible conventional LLM baseline); PolicyEngine; three hero
  scenarios; live dashboard; action detail view; benchmark script; real measured latency + safety metrics; demo script.
- **P1 — if P0 is stable:** SSE live replay, human review queue, additional scenarios, calibration/coverage chart, audit history.
- **P2 — stretch:** context-gathering agent (ask a targeted question when `missing_context` is high, update state,
  re-evaluate), richer planner, external messaging, multi-agent negotiation, production auth.

## 23. Non-goals

Full QuickBooks clone, tax preparation, full cash-flow forecasting, generic finance chatbot, complete fraud
detection platform, invoice negotiation, real bank integration, real payment execution, custom foundation-model
training, complex multi-agent ecosystem, unnecessary RAG.

## 24. Team ownership

- **Yizhe:** backend architecture, FastAPI, SystemOneProvider, PolicyEngine, SSE, provider abstraction, integration/evaluation plumbing.
- **Mira:** React/Vite dashboard, product/data workflow, action detail + review experience, business framing, KPI/evaluation presentation, integration support.
- **Anish:** scenario generation, labeling, RulesProvider, LLM baseline, evaluation scripts, benchmark data/results. See `docs/workstreams/ANISH.md`.
- **Kubra:** UI polish, charts, deployment, integration testing, demo video, pitch deck.

Adjust based on actual strengths.

## 25. Execution order

- **Phase 0 (30–45 min) — feasibility gate:** obtain API key; `GET /v1/models`; `POST /v1/systemone`; run 10–20
  ambiguous finance-action examples; verify outputs have useful separation/confidence. If this fails, redesign
  questions before building more UI.
- **Phase 1:** load dataset, define contracts, SystemOneProvider, PolicyEngine, CLI test (action → risk → decision).
- **Phase 2:** scenario generator, RulesProvider, LLM baseline, initial evaluation.
- **Phase 3 (parallel):** dashboard, action detail, review queue.
- **Phase 4:** SSE replay, integration.
- **Phase 5:** benchmark view, final measurements.
- **Phase 6:** deployment, demo rehearsal, video/pitch.

## 26. Hero demo script

1. **Safe action — Adobe $149.** Normal vendor and pattern → `ALLOW`.
   *"LedgerGuard stays out of the way when the agent's action is routine and well-supported."*
2. **Changed payment destination — Acme Supplies $18,400.** Legitimate invoice; destination changed yesterday → `REQUIRE_APPROVAL`.
   *"The invoice itself is valid. The semantic risk comes from the changed payment context, so the agent is paused before execution."*
3. **Semantic duplicate obligation — AWS $4,210.** Similar obligation for the same billing period already
   represented with slightly different amount/date → `BLOCK` or MATCH_EXISTING.
   *"This is not a trivial exact duplicate. LedgerGuard evaluates whether the two records represent the same underlying obligation."*

Then show the benchmark (Rules vs conventional LLM vs System One).
End: *"System One handles judgment. Code handles authority."*

## 27. Challenge fit — Q&A

- **What is the Intuit challenge asking for?** A meaningful use of System One that creates new customer value in
  accounting, ideally enabling an experience conventional ML or GenAI made too slow, expensive, difficult, or
  impractical, with realistic evaluation against relevant alternatives.
- **What new experience does LedgerGuard enable?** Semantic safety checks inside every autonomous financial-agent
  action before execution, rather than after-the-fact review or month-end cleanup.
- **Why not just a rules engine?** Hard rules stay in code. System One handles only ambiguous contextual judgments
  (same obligation? risky destination change in context? matches user intent? key context missing?).
- **Why not a conventional LLM?** It is a baseline; LedgerGuard needs machine-oriented typed decisions with
  probabilities/confidence at latency/cost that fits a repeated execution loop. We benchmark rather than assume.
- **Why do probabilities matter?** High-confidence low-risk actions proceed; low-confidence or high-risk cases
  escalate. Confidence becomes part of deterministic software control.
- **Customer value?** Safer automation, fewer duplicate/unsafe actions, less manual review and reconciliation,
  more confidence in autonomous accounting.
- **What makes System One essential?** Remove it and the low-latency semantic risk layer is gone. Rules are too
  brittle for ambiguous context; conventional LLM calls may be too slow/costly for repeated machine-to-machine
  decisions. The benchmark tests this directly.
- **Sponsor data?** The synthetic QuickBooks dataset is the base state, plus a small set of clearly disclosed
  adversarial/ambiguous scenarios.
- **How do we prove the unlock?** Side-by-side evaluation of Rules, LLM baseline, and System One on the same
  labeled scenarios: unsafe-action escape, safe autonomous coverage, latency, other quality metrics.
- **What if System One isn't more accurate?** It can still win on the overall quality/latency/cost/calibration
  tradeoff that makes execution-time checks practical. We report honestly.
- **Why Applied Intelligence?** AI applied directly to a real operational problem: safely automating
  financial-agent actions.

## 28. Acceptance criteria

Demo-ready only if: Jev is called successfully on real project scenarios; at least three labeled hero scenarios
work end to end; the UI shows real risk signals and policy decisions; no model output directly executes an action;
benchmark results come from actual runs; the audience can see why ambiguous cases need contextual judgment; the
demo completes without real-money systems; a fallback recording exists.

## 29. Primary risks and mitigations

| Risk | Mitigation |
|---|---|
| Jev outputs not discriminative | Simplify/rewrite questions, reduce state noise, separate decisions, test early |
| Looks like generic fraud detection | Frame around agent execution safety and accounting workflow trust |
| Rules solve all demo examples | Include genuinely ambiguous semantic cases, not only exact thresholds |
| Scope explosion | Enforce P0/P1/P2 and non-goals |
| Live API outage | Cache labeled demo cases, record fallback video, fail safely |
| Unfair benchmark | Same state, labels, action space; documented methodology |

## 30. Final pitch

"QuickBooks is becoming increasingly autonomous. The next problem is not whether AI can make accounting
decisions — it is whether software should trust those decisions enough to execute them.

LedgerGuard is a real-time System One firewall for autonomous financial agents. Before an agent action touches
the ledger or payment workflow, Jev evaluates contextual risks such as goal alignment, duplicate obligations,
payment-destination changes, missing context, and behavioral anomalies. A deterministic policy engine then allows,
escalates, requests context, or blocks the action.

System One handles judgment. Code handles authority."

## 31. References

- LA Hacks tracks: <https://live.lahacks.com/tracks>
- Intuit sponsor brief: "QuickBooks: Reimagining Accounting With System One Models" — meaningful System One
  unlock, clear customer value, realistic evaluation against relevant alternatives, synthetic data may be extended
  with disclosure.
- TypeSafe: <https://typesafe.ai/>
- TypeSafe API docs: <https://api.typesafe.ai/docs> — verify at build time: `GET /v1/models`, `POST /v1/systemone`,
  multiple named questions per request, typed outputs with probability/confidence.

## 32. LangChain / LangGraph integration

**Purpose:** LangGraph is the workflow orchestration layer; LangChain is a selective integration/tooling layer.
Neither weakens System One's role.

```
User Goal -> LangGraph Financial Agent -> Plan / Proposed Action -> LedgerGuard Firewall
   (pre-checks -> context builder -> System One -> policy engine)
   ALLOW            -> execute_action -> END
   REQUIRE_APPROVAL -> interrupt() -> human review  -> resume -> execute / block
   REQUEST_CONTEXT  -> interrupt() -> ask for context -> build_context -> re-evaluate
   BLOCK            -> blocked_terminal -> END
```

**LangGraph does:** represent the long-running workflow, persist state between steps, route on `PolicyDecision`,
pause for approval or missing context, resume from the same state, coordinate lifecycle/retries/terminal states.

**LangGraph must not:** replace PolicyEngine, make final authorization decisions, bypass SystemOneProvider,
approve an action based on LLM text, or become a large multi-agent hierarchy.

**Nodes:** `parse_goal`, `plan_action`, `build_context`, `hard_precheck`, `system_one_evaluate`, `policy_decide`,
`human_review`, `request_context`, `execute_action`, `blocked_terminal`.

**AgentState (small, explicit):** `user_goal`, `proposed_action`, `accounting_state`, `risk_assessment`,
`policy_decision`, `human_response`, `execution_result`, `audit_id`, `current_scenario`, `error_state`.

**Human-in-the-loop:** `REQUIRE_APPROVAL`/`REQUEST_CONTEXT` use explicit pause/resume; resume rather than replan.
Missing-context loop (P1/P2): ask one targeted question → update `AccountingState` → rebuild context → re-run
System One → re-run PolicyEngine.

**LangChain uses:** (1) `LLMBaselineProvider` structured output mapped into `RiskAssessment`; (2) tool wrappers
(`get_open_bills`, `get_vendor_history`, `get_candidate_matches`, `get_recent_ledger_entries`, `simulate_payment`,
`request_context`); (3) optional planner abstractions. LangChain must not become the authorization layer, replace
System One, hide business logic in prompts, or add chains where a function suffices.

**Repo additions:** `backend/app/graph/{state, graph, routing}.py`, `graph/nodes/*.py`,
`backend/app/tools/{accounting, vendor, ledger, execution}.py`.
Boundaries: `providers/` intelligence, `policy/` authority, `graph/` orchestration, `tools/` facts + simulated
actions, `api/` HTTP, `services/` reusable business/data services.

**LangGraph scope:** P0 basic StateGraph + policy routing + ALLOW/BLOCK terminals (if time allows);
P1 REQUIRE_APPROVAL interrupt/resume, persisted state, review-queue integration; P2 REQUEST_CONTEXT loop,
context-gathering agent, richer planning. Never delay System One integration, evaluation, or the hero demo for it.

**Pitch line:** "LangGraph orchestrates. LangChain connects. System One judges. Policy code authorizes. LedgerGuard protects."

---

## Appendix A — Name candidates (undecided)

| Name | Why it fits |
|---|---|
| **Preflight** | Checks an agent's financial actions before they execute. "Preflight checks financial agents before they act." |
| **LedgerGate** | The name itself communicates accounting + execution gate. |
| Countercheck | A second check on the agent's proposed action; subtle finance connection. |
| Interlock | A safety mechanism that prevents execution until conditions are satisfied. |
| Clearance | Every action needs clearance before proceeding. |
| Holdpoint | Pauses risky actions at the moment a decision matters. |
| TallyGate | Playful accounting name. |
| LedgerLock | Strong security feel, but emphasizes blocking over safe automation. |

Until the team decides, code and docs use **LedgerGuard**.
