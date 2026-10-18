# LedgerGuard Frontend

React + TypeScript + Vite application implementing the Paper design file
**"LedgerGuard — LA Hacks 2026"** on top of the real FastAPI backend.

## Screens

| Route | Screen | Paper artboard |
|---|---|---|
| `/` | Landing — Precision Marketing Page | Landing — Precision Marketing Page |
| `/dashboard` | Dashboard — Policy Ledger | Dashboard — Policy Ledger |
| `/dashboard/actions/:id` | Action detail / audit trail drawer | Dashboard — Action Drawer Open |
| `/review` | Review queue (approval + context tabs) | Review Queue — Human Holds |
| `/demo` | Live demo (evaluation pipeline + SSE) | Live Demo — Evaluation Pipeline |
| `/benchmarks` | Measured benchmark runs | Benchmarks — Measured Runs |
| (all app screens) | Loading / empty / error / disconnected states | System States — loading · empty · error · disconnected |

## Run it

```bash
# 1. Backend (from the repository root)
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api/*` to `http://127.0.0.1:8000` (see `vite.config.ts`).
To point at another backend, either set `LEDGERGUARD_API_URL` for the proxy target or
`VITE_API_BASE_URL` for a direct connection.

Production build: `npm run build` (type-checked with `tsc -b`, output in `dist/`).

## Integration notes

- **Contracts.** Every type in `src/api/types.ts` mirrors `backend/app/api/models.py`;
  every call in `src/api/client.ts` maps 1:1 to a route documented in
  `docs/API_HANDOFF.md`. No endpoints are invented.
- **SSE.** `src/api/stream.tsx` holds one `EventSource` per session. Events are named
  (`event: policy_decision`), so listeners are registered per type. The stream is
  notification-only: each event invalidates TanStack Query caches and the persisted
  detail is refetched. Reconnects pass `?last_event_id=` and the cursor is persisted in
  `localStorage`.
- **Honesty rules encoded in the UI.**
  - Execution is always labeled `SIMULATED` — no real payment rail exists.
  - Benchmarks render only artifacts returned by `GET /api/benchmarks`; `status: not_run`
    is a real empty state, never placeholder numbers.
  - `median_provider_latency_ms` is labeled *provider* latency (it is not end-to-end).
  - Provider failures show only the sanitized fields (`provider`, `code`, `retryable`,
    `latency_ms`, `model_name`) and explicitly state the fail-safe routing.
- **Resolution rules.** Approve/Reject submit the exact `policy_decision.assessment_hash`
  and surface `409 STALE_REVIEW_RESPONSE` / `INVALID_STATE_TRANSITION` with dedicated
  copy. `provide_context` is only offered on `REQUEST_CONTEXT` actions and is limited to
  the eight fields the workflow accepts (`CONTEXT_UPDATE_FIELDS`).
- **Demo runs** send `idempotency_key: ui-demo-<scenario>-<uuid>` so a double submit can
  never create two executions; each intentional run gets a fresh key.
- **States.** `src/components/StatePanels.tsx` implements the four documented states:
  loading skeleton, real empty states, error surfaces keyed by stable `code`, and the
  SSE-disconnected banner.

## Design tokens

`src/styles.css` mirrors the Paper token set (`--color-paper`, `--color-ink*`,
`--color-allow/approval/context/block`, `--font-ui` Archivo, `--font-mono` IBM Plex Mono).
Fonts are self-hosted via `@fontsource` so the demo works offline.
