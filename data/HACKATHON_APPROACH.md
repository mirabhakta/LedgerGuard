# QuickBooks × System One Hackathon: Approach to Win

> Goal: pick one idea, prove it with a realistic evaluation, and demo it live.
> This doc covers how to choose the idea, what to build, how to evaluate it, and how to pitch it.

---

## 0. TL;DR

**Recommended project: "Close the Books in Seconds."**
This is a continuous, per-transaction reasoning layer that finds, explains, and fixes bookkeeping problems across an entire ledger, then answers cash questions on the cleaned books in real time.

Why this wins against the rubric:

| Judging principle | How we hit it |
|---|---|
| **Meaningful technical unlock** | Fast, cheap models make it feasible to reason over *every* transaction and to run *generate → verify → retry* loops against the ledger. Sampling plus a big LLM is too slow and costly for that. Classical ML can't explain or handle free-text. |
| **Clear customer value** | Bookkeeping, reconciliation, and "is my cash OK?" are the core jobs of a QuickBooks user and of their accountant. |
| **Realistic evaluation** | The dataset's books are *perfectly clean and balanced*, so they serve as ground truth. We inject disclosed mess and score exactly against the original. Few teams will have labels this strong. |
| **System-One spirit / compatible API** | We build against a thin OpenAI-compatible model interface, so Jev, SemIf, Ollaya, or a small open model can plug in. We report quality vs. latency vs. cost for each. |

**The one-line pitch:** *"Today a QuickBooks book gets reviewed by sampling, by a person, at month-end. With a fast model, every transaction gets reasoned about the moment it lands, and every fix is machine-verified against the ledger before it's proposed."*

---

## 1. What we know about the data

All of this comes from `DATA_README.md`, `SCHEMA.md`, and `index.json`.

- **100 synthetic companies**, one year each, ending Oct 2026, in QuickBooks-shaped YAML.
- **Scale** (sum over all companies): ~84k invoices, ~144k customer payments, ~40k bills, ~36k bill payments, ~28k sales receipts, ~152k journal entries, ~235k bank transactions, ~26k payroll runs, plus aging reports.
- **Mix**: 7 business shapes (wholesale 22, construction/project 22, recurring services 16, POS 14, mixed 12, appointments 10, nonprofit 4), 71 industries, 3 size tiers.
- **Financial health**: 27 companies lost money and 7 are flagged `distressed`. That gives natural "at-risk" cases.
- **Payment behavior** varies per company: most customers pay late, some pay early, and a slice of invoices is written off. This is a real learnable signal for collections.
- **Reports are precomputed**: P&L (monthly), balance sheet (quarterly), and AR/AP aging. They double as consistency checks for any fix we propose.
- **`hidden/` is not in our copy.** It is organizer-only, so don't plan on using personas or management decisions.

### Data traps to design around (these are in the README's limitations)

| Limitation | Consequence for us |
|---|---|
| **Books and bank feed are perfectly clean** (no unmatched/duplicate lines) | There is no mess to fix as shipped, so **we must inject mess**. We have the clean original, so scoring is exact. |
| **Bank memos are generic** ("Vendor bill paid", "Wages paid") | Real bank feeds have noisy descriptors. We have to generate realistic ones, or matching is trivial. |
| **Only 1 year of history** | No year-over-year or seasonality. Use temporal splits *inside* the year (e.g. train on days 0–270, test on 270–365). |
| **One line per invoice, one invoice per payment, no tax/credit memos/refunds** | Simpler than real QBO. Say so explicitly, and don't claim generalization we haven't tested. |
| **First/last monthly P&L entries are partial months** | Check `full_calendar_month` and `days_covered` before trend claims. |
| **IDs are company-scoped** | Always key lookups by `(company_id, id)`. |
| **Wholesale prices cluster** more than organic data | Be careful with price-anomaly benchmarks, because they are easier here than in the real world. |

---

## 2. How to choose the idea (the framework)

Score each candidate 1–5 on the four things the judges care about, plus feasibility. Do this together in the first 30 minutes.

| Criterion | Question to ask |
|---|---|
| **Unlock** | Would this be impractical with classical ML *or* a big LLM at normal latency and cost? |
| **Value** | Would a QuickBooks owner or bookkeeper pay for this or change their workflow? |
| **Measurability** | Can we get exact ground truth from this dataset (or by modifying it) in hours, not days? |
| **Demo-ability** | Is there a 2-minute live moment where speed is *visible*? |
| **Feasibility** | Can 2–4 people finish it in the time available? |

### Candidate ideas, scored

| # | Idea | Unlock | Value | Measurability | Demo | Feasibility | Verdict |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| A | **Ledger repair + bank reconciliation + categorization with verifier loops** (the recommendation) | 5 | 5 | **5** | 4 | 4 | **Primary** |
| B | **Instant cash runway / what-if copilot** ("Can I hire someone in March?") with per-invoice collections reasoning | 4 | 5 | 4 | **5** | 4 | **Secondary layer on A** |
| C | **Always-on anomaly/fraud watchdog** (duplicates, odd vendors, round-dollar bills, drift) | 4 | 4 | 4 | 3 | 5 | Fold into A as detectors |
| D | **Cross-company benchmarking** ("how do I compare with 100 peers?") | 3 | 4 | 2 | 4 | 4 | Optional demo flourish |
| E | **Plain-language financial Q&A** over the books | 2 | 4 | 5 | 3 | 5 | **Avoid as the headline.** It's the obvious baseline for conventional GenAI and weak on "unlock." Use it only as a sanity benchmark. |
| F | **Tax-prep assistant** | 3 | 4 | 1 | 2 | 2 | **Avoid.** The data has no payroll taxes, sales tax, or real tax detail. |

**Decision rule:** build A as the core. B is cheap once A exists, because it runs on the cleaned books and gives the demo its emotional peak. C's detectors are a few extra checks inside A.

### Why A beats the alternatives

1. **Strongest evaluation story.** The dataset's guarantee that the books balance and the feed matches exactly means that we know the right answer for every injected error. Most teams will be stuck evaluating by vibes or LLM-as-judge.
2. **The unlock is real and defensible.** Doing one verified reasoning pass per transaction across ~235k bank lines, or three candidate fixes per ambiguous item, is a *throughput and cost* problem. That is exactly where "System One" speed matters.
3. **Customer value is obvious.** Reconciliation and cleanup are painful, recurring, and sit at the core of QuickBooks and its accountant channel.

---

## 3. The product: "Close the Books in Seconds"

### 3.1 User story

> A bookkeeper opens a client's QuickBooks file at month-end. 600 bank lines are uncategorized, a few invoices look duplicated, and the P&L feels off. They click **Close**. In seconds, every item is matched, categorized, or flagged with a plain-English reason and a verified one-click fix. The owner then asks "will I make payroll in 6 weeks?" and gets an answer with the invoices that decide it.

### 3.2 Pipeline

```
 Raw books + noisy bank feed
            │
            ▼
 ┌─────────────────────────┐
 │ 1. Cheap candidate gen  │  rules, exact/fuzzy match, amount+date windows,
 │    (classical, free)    │  vendor-name normalization → narrows each item to k candidates
 └────────────┬────────────┘
              ▼
 ┌─────────────────────────┐
 │ 2. Fast-model reasoning │  one call per ambiguous item (fan-out, parallel)
 │    (System One)         │  inputs: item + candidates + company context
 │                         │  outputs: decision, confidence, short rationale
 └────────────┬────────────┘
              ▼
 ┌─────────────────────────┐
 │ 3. Ledger verifier      │  deterministic checks: debits = credits, AR/AP subledger
 │    (hard constraints)   │  ties out, bank running balance reconciles, no double-applied
 │                         │  payment, aging reports still reconcile
 └────────────┬────────────┘
         pass │   fail → retry with the verifier's error as feedback (self-correction loop)
              ▼
 ┌─────────────────────────┐
 │ 4. Confidence routing   │  auto-apply high confidence, queue medium for one-click
 │                         │  review, escalate low (and show why)
 └────────────┬────────────┘
              ▼
 Clean books → 5. Cash copilot (what-if, collections risk, runway)
```

The key design principle is that **the model proposes and the ledger disposes.** Verifiers are deterministic code, which gives us trust and a number we can report: "fixes that pass invariants."

### 3.3 Task modules (each is independently scorable)

| Module | Task | Ground truth |
|---|---|---|
| **M1 Bank-feed matching** | Link each noisy bank line to the right invoice/bill/payment/journal entry (including batched deposits). | Original `source_document_id`. |
| **M2 Categorization** | Assign the right account to uncategorized spend/income. | Original account on bills, journal entries, and sales. |
| **M3 Duplicate and error detection** | Find injected duplicate invoices/bills, transposed digits, wrong-customer/vendor applications, misdated entries. | Our injection log. |
| **M4 Explanation + fix** | Produce a human-readable rationale and a proposed correction that passes the verifier. | Verifier pass rate and rubric-graded rationale (small human sample). |
| **M5 Cash copilot** | Forecast collections and cash, and answer what-if questions. See §3.5. | Held-out future days within the year. |

### 3.4 Mess-injection plan (must be disclosed in the submission)

The dataset README explicitly allows modification if we disclose it. Maintain one `MODIFICATIONS.md` with the seed, rates, and *why* for each item.

| Injection | How | Why it's realistic |
|---|---|---|
| **Bank descriptor noise** | Replace generic memos with realistic descriptors (`ACH CREDIT OKONKWO WHSE #4471`, `CHECK 10442`, `POS DEP 10/12`), truncate and add processor prefixes. Drop `source_document_id` from the model's view. | Real feeds don't have clean IDs or memos. |
| **Batched deposits** | Merge several same-day customer payments into one deposit line. | Very common in practice. |
| **Timing shifts** | Offset bank dates by 0–3 days beyond the existing settlement delay. | Clearing lag. |
| **Vendor/customer name variants** | `Sysco` → `SYSCO FOODS #221`, abbreviations, typos. | Name drift is the #1 matching problem. |
| **Missing categories** | Blank out the account on N% of bills, journal lines, and receipts. | The uncategorized queue. |
| **Wrong categories** | Move N% of items to a plausible-but-wrong account. | Human error. |
| **Duplicates** | Duplicate N% of invoices/bills with minor date or doc-number differences. | Double-entry. |
| **Amount errors** | Transposed digits, off-by-a-cent, decimal slips. | Typos. |
| **Wrong application** | Apply a payment to the wrong open invoice for the same customer. | Common AR error. |

**Difficulty tiers:** run Easy (≈2% corrupted), Medium (≈8%), Hard (≈20% plus compounding errors). Report all three. A model that only works at 2% isn't useful, and a curve that degrades gracefully is a strong story.

**Fairness rule:** mess is generated by a seeded script, and the generator never sees any model's outputs. Freeze the test set (specific companies and seeds) before we tune anything.

### 3.5 Cash copilot (secondary, but it makes the demo)

- **Collections risk per open invoice:** predicted days-to-pay and probability of write-off, built from each customer's payment history. Show *why* ("pays ~22 days late, 2 prior invoices >60 days").
- **13-week cash outlook:** project receipts (by predicted pay date) and disbursements (bills by due date, payroll cadence from `payroll_runs`, recurring owner draws/tax provisions from journal entries).
- **What-if fan-out:** "What if Customer X pays 30 days late?", "What if I hire at $1,200/week?", "What if I delay vendor Y?" Run dozens of scenarios in parallel and surface the one that breaks payroll.
- **Be honest about the math.** A gradient-boosted model will likely beat an LLM on raw days-to-pay regression. So the **numbers come from a classical model** and the **fast model does the reasoning layer**: explanations, scenario generation, prioritization, and drafting the collection message. The hybrid is stronger *and* more credible than claiming the LLM does everything.

---

## 4. The evaluation (this is where we win or lose)

> The brief says designing and running evaluations will be "a significant part of the hackathon work." Plan to spend ~35–40% of total time here.

### 4.1 Baselines (the "relevant alternatives" the judges asked for)

| Baseline | What it represents |
|---|---|
| **B0: Heuristics/rules** | Exact amount and date-window matching, keyword categorization. The cheap non-AI floor. |
| **B1: Classical ML** | Gradient boosting / logistic regression on engineered features (amount, date deltas, vendor-name TF-IDF/edit distance, historical account frequency). For forecasting: GBM on customer payment history. |
| **B2: Frontier-LLM, single pass** | A large general model, one prompt per item (or per batch), no verifier. This is the "conventional GenAI" comparator. |
| **B3: Frontier-LLM + verifier loop** | Same as B2 plus our verifier. It isolates the benefit of verification from the benefit of model speed. |
| **Ours: fast model + candidate gen + verifier + routing** | The proposed system, with the model backend swappable. |

Running B3 matters: it shows that *speed and cost* are what make the verifier loop affordable at ledger scale.

### 4.2 Metrics

**Quality**
- Match accuracy (M1), top-1 and top-3, split by easy/medium/hard and by business profile.
- Categorization accuracy and macro-F1 (M2).
- Precision, recall, and F1 per injected-error type (M3).
- **Verified-fix rate:** share of proposed fixes that pass all ledger invariants.
- **Harmful-action rate:** auto-applied fixes that are *wrong*. This is the number that earns trust, so report it prominently.
- **Calibration:** is stated confidence reliable? Show a reliability curve and the accuracy-coverage trade-off (e.g. "auto-resolves 83% of items at 99% precision").
- Forecasting (M5): MAE/WAPE on receipts timing and cash balance at 30/60/90 days on held-out days; also "did we flag the insolvency early" on the 7 distressed companies.

**Speed and cost (the unlock)**
- p50/p95 latency per item and **end-to-end time to close one company-year**.
- Throughput (items/sec at fixed concurrency).
- **$ per 1,000 items** and **$ per company-year**.
- **Quality-at-equal-budget curves:** for the same dollar or latency budget, how much accuracy does each approach reach? A frontier-LLM may match us on accuracy but only at 20–100× the cost or latency, and *that* is the unlock. Don't claim numbers until measured.
- "Interactive threshold": the fraction of what-if queries answered within, say, 1–2 seconds.

**Customer value**
- Estimated **minutes of bookkeeper time saved** per company-month (items auto-resolved × assumed seconds per manual touch). State the assumption, and show a sensitivity range.
- Number of cash-flow crises flagged N weeks early.

### 4.3 Evaluation hygiene (what judges will probe)

1. **Freeze a held-out test set first** (e.g. 20 companies spanning all 7 profiles, fixed seeds). Never tune on it.
2. **Temporal split for forecasting**: fit on days 0–270, predict 270–365. No leakage from future payments.
3. **No label leakage in prompts.** Strip `source_document_id`, `provenance_note`, `sim_*` fields, and anything that reveals the answer. Audit prompts for these fields.
4. **Stratify** results by profile, size tier, and difficulty. Show where it fails.
5. **Run each system 3+ times** (different mess seeds) and report mean ± spread.
6. **Error analysis slide:** the top failure patterns and what we'd do next. Honest limitations score better than silence.
7. **Disclose all modifications** (mess injection, descriptor generation, any synthetic extension).
8. **Human spot-check:** have teammates grade ~50 rationales on a 1–5 rubric (correct, specific, actionable), and report agreement.

### 4.4 Expected results to aim for (hypotheses, not claims)

- B0 and B1 do well on easy cases, then collapse on name variants, batched deposits, and compounding errors.
- B2 handles ambiguity but is slow and expensive, and produces some verifier-failing or hallucinated fixes.
- Ours reaches B3-level quality at much lower cost and latency, with a lower harmful-action rate than B2.
- Only report these if the measurements support them. If the fast model underperforms on some module, say so and show the routing fallback.

---

## 5. Model strategy and "System-One-compatible API"

- **Single interface:** one `LLMClient.complete(messages, schema)` wrapper with an OpenAI-compatible endpoint. Swap Jev, a SemIf or Ollaya-style model, a small open model, and a frontier model by changing a config line.
- **Structured outputs:** require JSON (decision, confidence, rationale, evidence ids). Validate it, and reject and retry on schema violations.
- **Fan-out concurrency:** async batching with a configurable concurrency limit, and record per-call latency and tokens.
- **Prompt hygiene:** short, constrained prompts with the candidate list inline, so the model *chooses* instead of *generates*. That is cheaper, faster, and less hallucination-prone.
- **Fallback ladder:** classical → fast model → (optional) larger model only for items the fast model is unsure about. Report how often escalation is needed.
- **Open questions to confirm with the organizers (do this early):**
  1. Is a Jev (or other System One) endpoint provided, and what are its rate limits and context window?
  2. Are there latency/cost figures we can cite, or must we measure ourselves?
  3. Can we use a frontier model for baselines B2/B3?
  4. Any submission format requirements (repo, deck, demo video, live demo)?

---

## 6. Build plan

Adjust the hours to the actual hackathon length. The proportions matter more than the absolute numbers.

| Phase | Share | Deliverables |
|---|---|---|
| **P0. Setup and decisions** | 5% | Confirm model access and rules. Load data into a fast store (DuckDB/SQLite or pandas parquet). Pick the test companies. |
| **P1. Mess injector + ground truth + verifier** | 20% | Seeded generator for all injections, the injection log, and the **ledger verifier** (invariants). These are the foundation, so build them first. |
| **P2. Baselines** | 15% | B0, B1, and the B2 frontier prompt. Get a first leaderboard number early. |
| **P3. Core system** | 25% | Candidate gen, fast-model reasoning, verify/retry loop, confidence routing. Iterate against the dev set. |
| **P4. Cash copilot** | 10% | GBM collections model, 13-week outlook, what-if fan-out. |
| **P5. Full eval run** | 10% | Frozen test set, 3 difficulty tiers, 3 seeds, quality/latency/cost tables and curves. |
| **P6. Demo + pitch** | 15% | UI, scripted demo, slides, `MODIFICATIONS.md`, limitations. |

**Split of roles (for 3–4 people):**
- **Data/eval lead:** injector, ground truth, metrics, held-out set.
- **Modeling lead:** prompts, candidate gen, verifier loop, routing.
- **Forecasting/copilot:** collections model, cash outlook, what-if.
- **Product/demo lead:** UI, narrative, slides, disclosure doc.

### De-risking checkpoints
- **Hour ~2 spike:** run the fast model on 200 injected items for M1 and M2. If accuracy is dismal, change the candidate-gen and prompt design, or re-scope to the module where it does work.
- **Mid-point:** have a full end-to-end run (even rough) and one results table. Everything after is improvement.
- **Cut line:** if time is short, drop M5's what-if fan-out first, then M3's rarer error types. **Never drop the evaluation.**

---

## 7. The demo (2–3 minutes)

1. **Setup (15s):** "This is a company's year of books after a messy month: 600 uncategorized bank lines, duplicates, mismatched payments."
2. **Click Close (30s):** a live counter ticks through thousands of items. Show the side-by-side timer: ours vs. the frontier-LLM baseline on the same slice, plus cost per 1,000 items.
3. **Trust (30s):** open one tricky fix: batched deposit matched to three invoices, with rationale, evidence, and a green "ledger verified ✔" badge. Then show one *rejected* fix, where the verifier caught a bad proposal and the retry corrected it.
4. **Cash copilot (45s):** the owner types "Can I hire a $1,200/week employee in January?" and gets a sub-2-second answer with a scenario fan-out chart, naming the 3 late invoices that decide it. Draft the collection email for the top one.
5. **Scoreboard (30s):** one slide with the accuracy / harmful-action-rate / latency / $ per company-year across B0–B3 and ours.

Have a **pre-recorded backup video** in case of live-demo or API failure.

---

## 8. Pitch outline

1. **Problem:** bookkeeping is reviewed late, by sampling, by hand, so errors survive into taxes and decisions.
2. **Insight:** the bottleneck isn't intelligence, it's *throughput and trust*. We need reasoning on every item and a way to prove each fix is safe.
3. **Solution:** fast-model reasoning + deterministic ledger verification + confidence routing, then a real-time cash copilot.
4. **Why System One:** per-item reasoning at ledger scale and verify-retry loops only pay off with fast, cheap inference. Show the quality-at-equal-budget curve.
5. **Evidence:** the table versus rules, classical ML, and frontier LLM, in three difficulty tiers and with harmful-action rate.
6. **Impact:** bookkeeper hours saved and crises flagged early, with assumptions stated.
7. **Honesty slide:** data limitations, what we changed, where it fails, and what's next (e.g. real QBO integration, multi-year data).

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Synthetic mess is "too easy" or too artificial | Vary injection types and rates, compound errors, and add realistic descriptors. State the limits openly. |
| The fast model underperforms on some modules | Candidate gen narrows the choice. Escalate low-confidence items. Report per-module honestly. |
| Judges say "an LLM can just do this" | Our answer is the **cost/latency-at-equal-quality** curve plus the verifier loop that only becomes affordable at speed. Have B3 ready. |
| We over-claim on forecasting | Use classical ML for the numbers, and the model for reasoning. Say so. |
| Data leakage in prompts | Field allow-list for prompts. Review before the final run. |
| Scope creep | Cut line in §6. Evaluation is protected time. |
| Live demo failure | Backup video and cached results. |
| Dataset quirks (partial months, company-scoped IDs) | Checklist in §1. Unit tests for the loaders. |

---

## 10. Deliverables checklist

- [ ] Working system and a swappable model backend
- [ ] `MODIFICATIONS.md`: every data change, seed, rate, and reason
- [ ] Frozen test set definition and the mess-injection script
- [ ] Baselines B0–B3 implemented and run on the same test set
- [ ] Results: quality, latency, cost, harmful-action rate, calibration, by tier and by profile
- [ ] Quality-vs-cost/latency curve
- [ ] Error analysis and limitations
- [ ] Demo (live and backup video)
- [ ] Slides (≤ 8) following §8
- [ ] README with reproduce steps (one command to regenerate mess and re-run evals)

---

## Appendix A: Alternative headline if the model team prefers a different angle

If model access turns out to favor *interactive* use over *batch* throughput, flip the emphasis. Make **B (Cash copilot / what-if)** the headline and keep A's repair pipeline as the "data is trustworthy because we cleaned it" foundation. The evaluation stays the same: held-out future days, a GBM baseline, a frontier-LLM baseline, and quality-at-equal-latency curves.

## Appendix B: Handy loader notes

- Path: `company-XXX/rwm-v4/world-<id>/*.yaml`. Look up `world-<id>` in `index.json` (`dataset_id`).
- Money fields are decimal strings. Use `Decimal` or integer cents, never floats.
- Bank `amount` is already signed (debit +, credit −), and `running_balance_amount` is cumulative, which is useful as a reconciliation check.
- Empty entity files (`projects`, `estimates`, `sales_receipts`, ...) are normal and depend on business shape.
- `invoices.yaml` is ~1 MB per company, so load once and cache as Parquet.
- Observation date is fixed at the last simulation day (day 365). Statuses and aging are as of that day.
