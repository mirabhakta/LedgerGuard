# Coding Assistant Rules

Give these rules to any coding assistant working on LedgerGuard. `AGENTS.md` (auto-loaded by most tools)
summarizes the most important ones; this file is the complete list. Source: `docs/FINAL_SPEC.md` §21 and §32.

## Core rules

1. **Do not change product scope.** The product is an execution-time firewall for autonomous financial-agent actions.
2. **Do not turn the project into a chatbot.**
3. **Do not add new infrastructure without a concrete requirement.** No Kafka, Redis, Kubernetes, vector DB,
   microservice split, or complex event bus unless explicitly approved.
4. **Keep System One behind `DecisionProvider`.** No Jev API calls directly from route handlers or UI code.
5. **Keep final authority in the deterministic `PolicyEngine`.** Model output must never directly execute an action.
6. **Distinguish deterministic facts from semantic judgment.** Do arithmetic, exact matching, thresholds, and known
   constraints in code.
7. **Never fabricate benchmark results, probabilities, costs, or latency.**
8. **Never simulate real fund movement.** All execution actions are demo/sandbox state transitions.
9. **Never commit API keys or secrets.**
10. **Use typed Pydantic models for backend contracts.**
11. **Keep frontend/backend contracts stable.** If a contract changes, update `docs/API_CONTRACT.md` and both sides.
12. **Prefer simple implementations that are demo-stable.**
13. **Every provider must return the same `RiskAssessment` schema.**
14. **Every final decision must record reason codes and triggering thresholds.**
15. **Add tests for:**
    - policy thresholds
    - provider parsing
    - malformed model response handling
    - scenario ground truth
    - API response schema
16. **If System One is unavailable:** fail safely to `REQUIRE_APPROVAL` for actions that require semantic judgment.
    Do not silently auto-allow.
17. **No claims that System One is always correct.** Typed output/schema reliability is not the same as semantic correctness.
18. **Keep all measured values reproducible.** Evaluation scripts output machine-readable JSON/CSV results.

## LangGraph / LangChain rules

19. LangGraph coordinates workflow only; it must not replace `PolicyEngine`.
20. System One must remain behind `SystemOneProvider`.
21. No graph node may execute a financial action unless `PolicyDecision` explicitly authorizes it.
22. `REQUIRE_APPROVAL` and `REQUEST_CONTEXT` must use explicit workflow state. Do not rely on hidden conversational memory.
23. LangChain LLM output may support planning or baseline evaluation, but it is never final authorization authority.
24. Keep graph nodes small, single-purpose, and individually testable.
25. Do not create supervisor/multi-agent hierarchies unless explicitly approved.
26. Prefer normal Python functions over LangChain abstractions when no orchestration/tool benefit exists.
27. Human review must preserve the original action, risk signals, and policy reason codes for auditability.
28. Resumed workflows must not silently recompute or mutate financial facts without recording the update.
29. If the workflow engine fails or state cannot be restored, fail safely to `REQUIRE_APPROVAL`/`BLOCK` rather than auto-executing.
30. LangGraph/LangChain integration must not change benchmark fairness. Rules, LLM, and System One providers still
    receive the same relevant `AccountingState`.

## Data and evaluation rules (project-specific additions)

31. Every change to the sponsor dataset is logged in `docs/MODIFICATIONS.md` with source event(s), exact
    modification, reason, expected ground-truth action, and scenario category.
32. Never send label-bearing or simulation-provenance fields to a provider: `provenance_note`, any `sim_*` field,
    `source_document_id`, `expected_action`, `scenario_category`, injection notes.
33. Freeze the test split (by company) before tuning prompts, questions, rules, or policy thresholds. Tune on dev only.
34. Treat IDs as company-scoped and money as `Decimal`/integer cents.
35. Do not commit the raw sponsor dataset (`data/company-*/`).
