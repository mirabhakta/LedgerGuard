# LedgerGuard

A System One firewall for autonomous financial agents (LA Hacks 2026, Intuit challenge). Before an agent's
financial action executes, LedgerGuard returns `ALLOW`, `REQUIRE_APPROVAL`, `REQUEST_CONTEXT`, or `BLOCK`.
System One handles judgment; deterministic policy code handles authority.

Start with `AGENTS.md` and `docs/FINAL_SPEC.md`.

## Quickstart (backend + evaluation)

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m pytest
.venv/bin/python -m evaluation.run_eval --providers rules,llm,system_one \
  --dev data/scenarios/dev.jsonl --test data/scenarios/test.jsonl --hero data/scenarios/hero.jsonl
```

Regenerating scenarios requires the sponsor dataset in `data/company-*/` (not committed):
`python -m evaluation.generate_scenarios --seed 1337`.

Data changes are disclosed in `docs/MODIFICATIONS.md`; evaluation methodology and measured results are in
`docs/EVAL_PLAN.md`.
