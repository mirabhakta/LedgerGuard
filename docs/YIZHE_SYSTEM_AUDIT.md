# Yizhe Backend / AI Infrastructure System Audit

**Audit date:** 2026-10-17 America/Los_Angeles  
**Scope:** Phase 1–7, with emphasis on Yizhe-owned policy, integration, LangGraph, persistence, execution authority, evaluation plumbing, FastAPI, and SSE.

## Verified story

```text
scenario/API input
  -> official sponsor YAML normalization
  -> company-scoped AccountingState
  -> Rules / Gemini / System One provider contract
  -> deterministic PolicyEngine
  -> LangGraph route / interrupt / resume
  -> durable authorization
  -> simulated execution only
  -> SQLite audit + REST detail + SSE
```

## Areas checked

| Area | Checks |
|---|---|
| Dataset/normalization | missing files, malformed YAML, duplicate/blank company IDs, schema drift, Decimal/date safety, company-scoped IDs, ground-truth stripping |
| Context/retrieval | as-of visibility, no future leakage, cross-company exclusion, bounded history/candidates, recent tie ordering, deterministic hashes |
| Providers | request shape, structured validation, model discovery, retry/timeout/status mapping, secret-safe messages, no policy/label leakage |
| Policy | threshold boundaries, rule priority, config hashes, hard failures, low confidence, provider failure, unsafe fallback configuration |
| Evaluation | immutable case/state hashes, policy hash equality, metrics denominators, JSON/CSV serialization, measured-only outputs |
| LangGraph | four routes, hard-precheck short circuit, typed interrupts, stale review, context rebuild, checkpoint schema, exception fail-safe |
| Execution | independent action/decision guard, human hash binding, durable authorization-before-intent, idempotency, interrupted-intent recovery |
| SQLite | WAL, cross-connection idempotency, restart readability, checkpoint restart/resume, integrity check, filter exactness |
| FastAPI | typed OpenAPI, 404/409/422/500 contract, pagination, filters, CORS, provider sanitization, hero flows |
| SSE | real node-time events, ordering, native `Last-Event-ID`, >100 event replay, replay/live race avoidance, heartbeat, bounded queue cleanup |

## Confirmed issues fixed during this audit

1. Provider failure fallback could be configured as `ALLOW`; it is now restricted to approval or block.
2. OpenAPI responses were untyped arbitrary objects; stable response models now cover actions, decisions, audit, authorization, benchmarks, and dashboard.
3. SSE replay stopped after 100 events and ignored the browser `Last-Event-ID` header; replay now paginates and supports header/query cursors.
4. Replay had a subscribe gap; live subscription is now installed before replay.
5. SSE milestones were emitted after workflow completion; events now originate at LangGraph node boundaries.
6. Pending review/context could not resume after process restart; the default app now uses a durable SQLite LangGraph checkpointer.
7. Duplicate terminal resolution was accepted; state transition and per-action concurrency guards now return `409`.
8. Execution authorization existed only in memory; policy/human authorization is now persisted before execution intent.
9. A failed simulated execution completion left an unrecoverable `INTENT`; retry now recovers the same persisted execution identity.
10. Idempotency was only process-local and allowed key reuse for another scenario; SQLite conflict handling is cross-connection safe and mismatched reuse returns `409`.
11. Reason-code filtering used wildcard `LIKE`; it now uses exact SQLite JSON membership.
12. Pagination returned only page count; API now exposes both `count` and `total`.
13. Equal-score candidate matches preferred older records; ties now prefer the most recent record.
14. Duplicate/blank company IDs could silently corrupt index scope; loader now rejects them.
15. Transport exception text could be stored in provider failures; external error details are now replaced with stable safe messages.
16. Key financial/domain models silently ignored unknown fields; they now forbid extra fields.
17. Browser frontend requests lacked CORS support; origins are now explicit and environment-configurable.

## Actual black-box evidence

A real Uvicorn server was started against an isolated SQLite database and tested over HTTP:

- health: `200`, three providers, six scenarios;
- CORS preflight: `200`, exact localhost origin;
- safe flow: `ALLOW -> POLICY_ALLOW -> SIMULATED`;
- destination change: `REQUIRE_APPROVAL`, stale guard tested, approval produced `HUMAN_APPROVAL -> SIMULATED`;
- semantic duplicate: `BLOCK`, no authorization, no execution;
- actions pagination: `count=2`, `total=3` during the run;
- SSE replay from `Last-Event-ID: 15` started at event 16;
- Rules benchmark endpoint returned the measured six-case artifact;
- a pending approval survived a full Uvicorn stop/start and then executed once;
- audit database integrity: `ok`, 4 actions / 28 events / 3 authorizations / 3 executions;
- checkpoint database integrity: `ok`, 33 checkpoints;
- dependency check: `No broken requirements found`.

Final automated verification after the Gemini migration: **106 passed, 3 external
credential-gated live tests skipped**; Python compileall and dependency consistency
checks also passed.

Measured local latency from the black-box run:

- first cold company context request: about 18.4 seconds;
- subsequent warm scenario requests: about 0.07–0.09 seconds;
- approval resume: about 0.02–0.09 seconds.

The cold-start cost comes from lazy parsing/normalization of the large sponsor YAML dataset, not provider latency.

## Residual risks / explicit limits

These are not hidden as completed production features:

- External Gemini/System One live correctness, latency, and cost remain credential/network gated.
- Evaluation has six curated scenarios; this is demo evidence, not statistical production validation.
- First-company cold start is too slow for an unrehearsed demo; warm up or persist normalized data.
- SQLite + in-process SSE is a single-instance architecture. Run one worker for the hackathon.
- Multi-worker live SSE needs a shared broadcaster; SQLite replay only repairs state after reconnect.
- Authentication/role authorization is intentionally absent from hackathon P0.
- Rate limiting, request-size limits, backups, migrations tooling, tracing, and production secret management remain deployment work.
- No real financial posting exists; execution is intentionally simulated.
- No long-duration load/soak benchmark has been claimed.

## Demo recommendation

Use `rules` as the guaranteed offline path, prewarm company-001, keep one Uvicorn worker, preserve the measured benchmark label, and show external provider failure as a safe `REQUIRE_APPROVAL` outcome rather than hiding it.
