# System One Feasibility Gate

**Owner:** Yizhe  
**Checked:** 2026-10-17 (America/Los_Angeles)  
**Status:** Adapter and offline contract verified; live semantic spike blocked by missing API key.

## Verified official contract

The current TypeSafe OpenAPI document reports API version `0.2.0` at
`https://api.typesafe.ai/openapi.json`.

- Authentication: `Authorization: Bearer <API_KEY>`.
- Discovery: `GET /v1/models` returns `{ "models": [{ "name", "description", "release_date" }] }`.
- Evaluation: `POST /v1/systemone` requires `model`, `state`, and a non-empty named `questions` object.
- LedgerGuard uses five `score` questions. Each has three ordered criteria; the response score is
  normalized from the documented `0..2` range into `0..1`, while the API's independent
  `confidence` value is retained.
- A successful response requires `model`, all five named answers, and `usage`. Missing, renamed,
  mistyped, or out-of-range answers are rejected rather than defaulted.

## LedgerGuard questions

1. `goal_alignment` — high means strongly aligned with the goal and constraints.
2. `duplicate_obligation_risk` — high means strong duplicate evidence.
3. `counterparty_change_risk` — high means a suspicious or unsupported change.
4. `missing_context` — high means decision-critical context is absent.
5. `action_anomaly` — high means highly anomalous relative to supplied history.

No policy threshold or final action is included in the provider request. The shared
`AccountingState.inference_view()` is used, excluding raw generator metadata and `sim_*` truth.

## Reliability behavior

The adapter performs authenticated model discovery before its first evaluation and does not assume
an alias. Timeouts, network errors, authentication failures, rate limits, invalid requests,
unavailability, model-discovery failures, and malformed responses become typed `ProviderFailure`
values. They never become a synthetic low-risk assessment.

## Verification completed

Offline tests use `httpx.MockTransport` and cover discovery, exact request shape, valid parsing,
missing/wrong/out-of-range answers, HTTP 401/403/422/429/5xx, timeouts, network errors, absent
configuration, and empty model lists. The live test is opt-in via
`RUN_TYPESAFE_LIVE_TESTS=1` and never logs the API key.

## Live spike limitation and decision

`TYPESAFE_API_KEY` was not present in the execution environment on 2026-10-17. Therefore no honest
claim can yet be made about account-visible models, 10–20-case signal separation, live latency, or
semantic quality. The gate decision is **provisionally proceed with the adapter, but do not treat
System One as production-validated** until the opt-in live suite and the planned real-case spike run
with a project key.

When a key is available, run:

```bash
RUN_TYPESAFE_LIVE_TESTS=1 TYPESAFE_API_KEY=... .venv/bin/python -m pytest -m live -q
```

Then record the discovered model identity, sample lineage/count, warm/cold latency distribution,
signal separation, and any API limitations here. Do not store the key or authorization header.
