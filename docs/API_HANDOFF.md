# LedgerGuard API Handoff

**Audience:** Mira / frontend integration  
**Contract version:** API `1.0.0`, event schema `1`, workflow state `1`

## Start and inspect

```bash
.venv/bin/uvicorn backend.app.main:app --reload
```

- API base: `http://127.0.0.1:8000/api`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `GET /api/health`

The default server loads the official local dataset from `data/raw/hackathon-100` and
uses `data/ledgerguard.sqlite3`. Override these with `LEDGERGUARD_DATASET` and
`LEDGERGUARD_DB_PATH`.

## Stable routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | Provider/scenario readiness |
| `POST` | `/api/demo/run` | Run a named scenario through the real pipeline |
| `GET` | `/api/actions` | Filtered, paginated audit list |
| `GET` | `/api/actions/{action_id}` | Sanitized context, outcome, policy, audit, review, execution |
| `POST` | `/api/actions/{action_id}/resolve` | Approve, reject, or provide context |
| `GET` | `/api/dashboard` | Persisted operational counts and median provider latency |
| `GET` | `/api/benchmarks` | Measured artifacts only; explicit `not_run` when empty |
| `GET` | `/api/stream` | SSE replay followed by live events |

`GET /api/actions` accepts `final_action`, `reason_code`, `provider`, `scenario`,
`limit` (1–100), and `offset`. `count` is the returned page size; `total` is the exact
filtered total.

## Demo request

```json
{
  "scenario_id": "safe-normal-payment-001",
  "provider": "rules",
  "idempotency_key": "ui-demo-001"
}
```

Available scenarios are `safe-normal-payment-001`, `semantic-duplicate-001`,
`destination-change-001`, `missing-context-001`, `goal-mismatch-001`, and
`high-amount-plausible-001`. Providers registered by the default service are `rules`,
`gemini`, and `system_one`; the external providers return typed fail-safe outcomes when
credentials or upstream service are unavailable.

## Decision and resolution contract

`policy_decision.final_action` is one of:

- `ALLOW`: simulated execution may be present.
- `REQUIRE_APPROVAL`: show review UI; submit the exact `assessment_hash` returned by the action.
- `REQUEST_CONTEXT`: show missing-context UI; send only supported action fields plus provenance.
- `BLOCK`: terminal; never show an execute control.

Approval example:

```json
{
  "resolution": "approve",
  "actor": "reviewer@example.com",
  "assessment_hash": "<exact policy_decision.assessment_hash>"
}
```

Context example:

```json
{
  "resolution": "provide_context",
  "actor": "operator@example.com",
  "updates": {"vendor_id": "vend-supplier"},
  "provenance": "Operator confirmed vendor from receipt"
}
```

A stale approval returns HTTP `409` with `code: STALE_REVIEW_RESPONSE`. Duplicate
resolution or a resolution for the wrong state returns `409`.

## Error contract

```json
{
  "code": "ACTION_NOT_FOUND",
  "message": "action not found",
  "retryable": false,
  "audit_id": null
}
```

Handle `404`, `409`, `422`, and `500` using `code`; do not parse the human-readable
message. Provider failure details are sanitized: the UI receives provider, stable code,
retryability, latency, model name, and outcome, but not raw upstream messages or secrets.

## Reason-code catalog

Hard safety reasons: `HARD_LIMIT_EXCEEDED`, `UNSUPPORTED_CURRENCY`,
`UNSUPPORTED_ACTION_TYPE`, `CROSS_COMPANY_CONTEXT`, `UNKNOWN_ACCOUNT`,
`EXACT_PAID_DOCUMENT_DUPLICATE`, `MISSING_REQUIRED_REFERENCE`.

Semantic/policy reasons: `DUPLICATE_RISK`, `GOAL_MISMATCH`,
`COUNTERPARTY_CHANGE_RISK`, `MISSING_CONTEXT`, `ACTION_ANOMALY`, `LOW_CONFIDENCE`,
`POLICY_ALLOW`, plus typed provider codes such as `PROVIDER_TIMEOUT`,
`PROVIDER_UNAVAILABLE`, and `PROVIDER_INVALID_RESPONSE`.

## SSE contract

Connect to `/api/stream`. Each event has an SSE `id`, an `event` name, and JSON `data`:

```json
{
  "event_id": 12,
  "action_id": "action-...",
  "audit_id": "audit-...",
  "type": "policy_decision",
  "timestamp": "2026-10-17T12:00:00+00:00",
  "schema_version": "1",
  "payload": {"final_action": "ALLOW", "reason_codes": ["POLICY_ALLOW"]}
}
```

Event names are `action_received`, `precheck_complete`, `provider_started`,
`risk_assessment_ready`, `policy_decision`, `execution_simulated`, `review_required`,
`review_resolved`, `context_requested`, `context_supplied`, and `action_blocked`. Event IDs are monotonic.
Reconnect with `last_event_id=<last seen id>`; SQLite replays later events before the
live subscription. Native browser `Last-Event-ID` headers are also supported. Heartbeat
comments are emitted on idle connections. Treat SSE as UI
notification only and refetch action detail after reconnect.

## UI states

- Loading: keep the action pending until the POST completes; SSE can animate persisted milestones.
- Empty list: render a real empty state when `items=[]` or benchmark `status=not_run`.
- Provider failure: display the stable provider code and route to review; never imply execution.
- Recorded benchmarks: label values as measured and show `sample_size`, provider/model, and run time.
- SSE failure: retry and refetch detail; it does not change the persisted workflow result.

## Contract verification

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_contract.py \
  backend/tests/test_event_bus.py backend/tests/test_persistence_failure.py
```

These tests cover the three hero flows, OpenAPI paths, validation/errors, filtering,
idempotency, restart-readable audit state, stale review rejection, provider timeout,
SSE ordering/replay/slow-consumer cleanup, and persistence failure before execution.

For black-box Uvicorn instructions and the runnable smoke test, see
[`FASTAPI_TESTING.md`](./FASTAPI_TESTING.md).
