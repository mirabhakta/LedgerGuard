# OpenJev local provider

LedgerGuard exposes OpenJev as provider name `openjev`. It is an independent,
open-source System One-style baseline; it is **not** the official TypeSafe Jev model
and its masked-logit probabilities are not RLCD-calibrated. Benchmark reports must
keep `openjev` and `system_one` as separate providers.

## Architecture boundary

```text
AccountingState.inference_view()
        -> OpenJevProvider
        -> local OpenJev POST /v1/systemone
        -> five normalized risk signals
        -> PolicyEngine
        -> ALLOW / REQUIRE_APPROVAL / REQUEST_CONTEXT / BLOCK
```

OpenJev estimates risk only. It never receives policy thresholds, final decisions,
execution authorization, simulator fields, or private provenance notes. The existing
deterministic prechecks and `PolicyEngine` remain authoritative.

## 1. Run OpenJev separately

Follow the upstream OpenJev installation instructions in a separate checkout and run
its server on the loopback interface. The LedgerGuard adapter expects:

- `GET /health`
- `POST /v1/systemone`
- default address `http://127.0.0.1:8771`
- default model `Qwen/Qwen3-0.6B`

The first inference may download/load model weights and be much slower than later
requests. Do not expose the development server directly to a public network.

Verify it before starting LedgerGuard:

```bash
curl -sS http://127.0.0.1:8771/health | jq
```

Expected shape:

```json
{"status":"ok","engine_loaded":false,"model_id":"Qwen/Qwen3-0.6B"}
```

`engine_loaded` may be either `false` (lazy loading) or `true`.

## 2. Configure LedgerGuard

`.env.example` already contains safe local defaults:

```dotenv
OPENJEV_BASE_URL=http://127.0.0.1:8771
OPENJEV_MODEL=Qwen/Qwen3-0.6B
```

No API key is required for the local upstream server. `OPENJEV_API_KEY` is optional
and only intended for a trusted reverse proxy placed in front of OpenJev. Never commit
a real key.

`OPENJEV_MODEL` pins the expected `/health` model. A mismatch fails closed instead of
silently mixing benchmark results from different models.

## 3. Test

Contract and failure tests do not load a model or use the network:

```bash
PYTHONPATH=. .venv/bin/pytest -q backend/tests/test_openjev_provider.py
```

With the local OpenJev server already running, execute the opt-in end-to-end test:

```bash
RUN_OPENJEV_LIVE_TESTS=1 PYTHONPATH=. \
  .venv/bin/pytest -q -m live backend/tests/test_openjev_live.py
```

Then exercise the complete FastAPI pipeline:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```bash
curl -sS -X POST http://127.0.0.1:8000/api/demo/run \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"safe-normal-payment-001","provider":"openjev"}' | jq
```

## 4. Benchmark without conflating providers

```bash
PYTHONPATH=. .venv/bin/python -m evaluation.run_eval \
  --provider openjev \
  --output evaluation/results
```

Record the exact OpenJev commit, model ID, device, dtype, scenario dataset version,
and cold/warm status alongside results. Compare it with `rules`, `gemini`, and
`system_one` as a distinct baseline; do not label it “Jev” or present its confidence
as calibrated.

## Troubleshooting

- `UNAVAILABLE`: OpenJev is not listening at `OPENJEV_BASE_URL`, crashed, or is still
  starting.
- `TIMEOUT`: model loading/inference exceeded the 120-second read timeout. Warm the
  server once or configure a faster supported device.
- `MODEL_DISCOVERY_ERROR`: `/health` is malformed or its model differs from
  `OPENJEV_MODEL`.
- `INVALID_RESPONSE`: answer names, score ranges, probability distribution, content
  type, or response model violated the adapter contract.
- macOS memory pressure: stop other model processes or choose a smaller compatible
  model; never weaken LedgerGuard's fail-closed validation to hide an OOM.
