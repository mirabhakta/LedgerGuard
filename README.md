# LedgerGuard

### A financial firewall for autonomous AI agents

**LedgerGuard checks what an AI agent is about to do with a business's money before the action is allowed to proceed.** Built for the **Intuit QuickBooks challenge at LA Hacks 2026**, it combines fast semantic risk assessment with deterministic financial policies, explainable decisions, human review, and an auditable execution trail.

Instead of discovering a duplicate payment or suspicious vendor change after the fact, LedgerGuard evaluates the proposed action **inside the agent's workflow**. Models identify contextual risks; a separate policy engine decides what is permitted. **AI models never authorize payments.**

> **Hackathon prototype:** All execution is simulated. LedgerGuard does not transfer funds or connect to a live QuickBooks payment account.

### Live Demo

🌐 **[Launch LedgerGuard](http://149.28.71.193/)**

> Hosted on a cloud server. The demo uses HTTP rather than HTTPS.

## The problem

As financial AI agents automate bill payments and bookkeeping, a plausible-looking action can still be wrong. A vendor invoice may already be paid, payment instructions may have changed unexpectedly, or the agent may be missing information it needs to act safely. Ordinary rules can catch known violations, but struggle with ambiguous financial context. LLM-only approvals introduce their own reliability and control problems.

LedgerGuard separates **understanding risk** from **granting permission**.

## How it works

```text
AI agent proposes a financial action
                 |
                 v
        Deterministic pre-checks
                 |
                 v
    Relevant QuickBooks context + history
                 |
                 v
      Semantic risk assessment
   (System One / Gemini / baselines)
                 |
                 v
      Deterministic PolicyEngine
                 |
       +---------+---------+----------+
       |         |         |          |
     ALLOW    APPROVAL   CONTEXT     BLOCK
       |         |         |          |
   Simulated   Human      Request   Deny
   execution   review     details   action
                 |
                 v
       Persistent audit + live events
```

The provider evaluates signals such as semantic duplicates, counterparty or destination changes, goal-action mismatch, missing context, and anomalous actions. It returns structured risk assessments and confidence values, **not** execution authority. The policy engine applies hard rules and thresholds to produce one of four decisions:

| Decision | Meaning |
|---|---|
| `ALLOW` | Action satisfies policy; simulated execution may proceed. |
| `REQUIRE_APPROVAL` | A human must review and explicitly approve or reject it. |
| `REQUEST_CONTEXT` | More information is needed before a new evaluation. |
| `BLOCK` | The proposed action is prohibited. |

Timeouts, invalid model responses, and unavailable providers fail safely rather than silently becoming `ALLOW` decisions.

## What you can explore

- **Live demo:** Run example financial-agent actions through the decision pipeline.
- **Dashboard and action history:** Inspect action outcomes, policy decisions, and recorded activity.
- **Human review:** Approve or reject actions requiring intervention; supply missing context where supported.
- **Real-time event feed:** Follow processing milestones through Server-Sent Events (SSE).
- **Provider benchmarks:** Compare rules, Gemini, System One, and OpenJev baselines using a shared evaluation contract and recorded measurements. Unrun benchmarks are displayed as such, not as fabricated results.
- **Audit trail:** Review decision reasons, provider metadata, and simulated outcomes.

The backend exposes these workflows; the availability and appearance of individual screens depend on the current frontend build.

## AI providers and safety architecture

| Component | Role |
|---|---|
| **System One (TypeSafe/Jev)** | Semantic risk-signal provider. Requires valid external credentials and availability. |
| **Gemini** | General-purpose LLM baseline producing the same risk-assessment schema. |
| **Rules** | Deterministic comparison baseline. |
| **OpenJev** | Separate local-model baseline; **not** the official hosted Jev service. |
| **PolicyEngine** | Sole authority for final allow/review/context/block decisions. |
| **LangGraph** | Orchestrates routing and human-intervention workflows; does not grant financial permission. |

For fair comparison, providers operate against the same structured accounting context and the same policy decision layer. The architecture also enforces an execution gate: actions without an `ALLOW` decision or valid explicit approval cannot execute, even in simulation.

## Data and Evaluation

LedgerGuard is built around the **Intuit QuickBooks Hackathon 2026 dataset**, comprising synthetic accounting records from 100 companies. The data includes accounts payable and other accounting entities, with records normalized to company-scoped identifiers and precise decimal amounts.

Some fraud-like scenarios require information not available in the original accounting records, such as vendor payment-destination changes. These additions are **explicitly labeled synthetic scenario extensions**, not represented as native QuickBooks fields. Scenario provenance and evaluation labels are tracked separately from model inputs to avoid label leakage.

Benchmarks are designed to compare decision quality, latency, failures, and routing behavior on the same scenarios. Results should only be interpreted as measured when the relevant benchmark has actually been executed.

## Tech Stack

- **Frontend:** React, TypeScript, Vite
- **API:** Python, FastAPI, REST, Server-Sent Events
- **Workflow:** LangGraph
- **Risk providers:** TypeSafe System One / Jev, Gemini, Rules, OpenJev
- **Policy:** Deterministic Python rules and thresholds
- **Storage and audit:** SQLite
- **Data:** QuickBooks synthetic accounting records, scenario overlays
- **Evaluation:** Provider-neutral scenario and benchmark tooling

## Getting Started

### Requirements

- Python 3.12
- Node.js and npm
- The sponsor dataset for dataset-backed scenarios
- Optional API keys for live external providers

### 1. Clone and set up the backend

```bash
git clone https://github.com/mirabhakta/LedgerGuard.git
cd LedgerGuard
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

For Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` instead.

### 2. Configure the environment

```bash
cp .env.example .env
```

Set any required provider credentials in `.env` and keep that file private. Never commit API keys. Rules-based evaluation and offline tests do not require live external-provider credentials. Consult `.env.example` for the supported settings.

By default, the API expects the sponsor dataset at `data/raw/hackathon-100` and stores runtime data in `data/ledgerguard.sqlite3`. Use `LEDGERGUARD_DATASET` and `LEDGERGUARD_DB_PATH` to override these locations.

### 3. Run backend tests and API

```bash
PYTHONPATH=. pytest -q
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

- API: `http://127.0.0.1:8000/api`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

### 4. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to the local FastAPI backend.

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service and provider readiness |
| `POST` | `/api/demo/run` | Run a named simulation scenario |
| `GET` | `/api/actions` | List recorded actions and audit summaries |
| `GET` | `/api/actions/{action_id}` | Inspect a specific action and decision |
| `POST` | `/api/actions/{action_id}/resolve` | Submit approval, rejection, or missing context |
| `GET` | `/api/dashboard` | Operational metrics |
| `GET` | `/api/benchmarks` | Recorded benchmark artifacts |
| `GET` | `/api/stream` | Replay and subscribe to live SSE events |

The demo includes normal payment, duplicate payment, destination change, missing context, goal mismatch, and unusual amount scenarios. See [API handoff documentation](docs/API_HANDOFF.md) for complete request/response contracts and stable reason codes.

## Project Structure

```text
backend/              FastAPI, domain models, providers, policy, workflows, persistence
frontend/             React/Vite application
data/                 Dataset loading and local data assets
evaluation/           Scenarios, benchmark runners, metrics
integrations/photon/  Photon integration workstream
docs/                 Architecture, contracts, data, testing, evaluation plans
tools/                Developer and integration utilities
```

## Documentation

- [Architecture and authority boundaries](docs/architecture.md)
- [Frontend/API contract](docs/API_HANDOFF.md)
- [FastAPI testing guide](docs/FASTAPI_TESTING.md)
- [Dataset report](docs/DATASET_REPORT.md)
- [Evaluation plan](docs/EVAL_PLAN.md)
- [Scenario documentation](docs/SCENARIOS.md)
- [Scenario modifications and provenance](docs/MODIFICATIONS.md)
- [Evaluation integration status](docs/ANISH_EVALUATION_IMPORT.md)

## Scope and Limitations

LedgerGuard is a hackathon demonstration, **not a production payment processor or a live QuickBooks integration**. It currently focuses on evaluated financial-agent actions and simulated execution. Real-world deployment would require additional authentication, authorization, integration security, operational safeguards, and validation. Photon messaging/calling is an integration workstream; do not assume notifications are operational without verifying its live configuration.

---

**Built at LA Hacks 2026 for the Intuit QuickBooks challenge.**
