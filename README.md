# LedgerGuard

A System One firewall for autonomous financial agents (LA Hacks 2026, Intuit
challenge). Semantic providers produce risk signals; deterministic policy code is
the only component allowed to authorize simulated execution.

## Quickstart

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --reload
```

The default FastAPI service registers `rules`, `gemini`, and `system_one`.
Local secrets belong in `.env`, which is ignored by Git; copy `.env.example` and
never commit real API keys.

## Frontend

The React/Vite client for the dashboard, review queue, live demo, and benchmarks lives in
[`frontend/`](./frontend/README.md) and consumes only the routes in `docs/API_HANDOFF.md`.

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to 127.0.0.1:8000
```

## Documentation

- `docs/architecture.md`: current backend architecture and authority boundaries.
- `docs/API_HANDOFF.md`: stable REST/SSE frontend contract.
- `docs/FASTAPI_TESTING.md`: local, live-provider, and smoke-test commands.
- `docs/ANISH_EVALUATION_IMPORT.md`: integration status of the scenario and
  benchmark artifacts imported from Anish's workstream.
- `docs/EVAL_PLAN.md`, `docs/SCENARIOS.md`, and `docs/MODIFICATIONS.md`: imported
  evaluation methodology, labels, and disclosure records.
