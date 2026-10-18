import { Link } from "react-router-dom";

/**
 * Landing — Precision Marketing Page.
 * Faithful implementation of the Paper artboard of the same name.
 */

function LaunchDemoButton({ label, href, compact = false }: { label: string; href: string; compact?: boolean }) {
  return (
    <Link
      to={href}
      className={`flex items-center justify-center gap-2.5 rounded-[3px] bg-ink transition-opacity hover:opacity-90 ${
        compact ? "h-10 px-5.5" : "h-11.5 px-6"
      }`}
    >
      <span
        className={`font-mono font-semibold tracking-[0.12em] text-surface ${
          compact ? "text-[10.5px] leading-3.5" : "text-[11px] leading-3.5"
        }`}
      >
        {label}
      </span>
      <svg width="12" height="10" viewBox="0 0 12 10" aria-hidden>
        <path
          d="M1 5 H10 M6.5 1.5 L10 5 L6.5 8.5"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </Link>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="font-mono text-[10px] font-medium leading-3 tracking-[0.16em] text-ink-3">{children}</div>
  );
}

function LandingNav() {
  return (
    <div className="flex h-18 shrink-0 items-center justify-between border-b border-hairline px-6 md:px-12">
      <div className="flex items-center gap-3.5">
        <span className="flex items-center gap-2.5">
          <span className="size-3.5 shrink-0 bg-ink" aria-hidden />
          <span className="font-ui text-[17px] font-bold leading-5.5 tracking-[-0.01em] text-ink">LedgerGuard</span>
        </span>
        <span className="hidden h-4 w-px shrink-0 bg-hairline sm:block" aria-hidden />
        <span className="hidden font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3 sm:block">
          FINANCIAL SAFETY LAYER
        </span>
      </div>
      <div className="flex items-center gap-6 md:gap-8">
        <a
          href="#how-it-works"
          className="hidden font-mono text-[10px] font-medium leading-3 tracking-[0.12em] text-ink-2 hover:text-ink sm:block"
        >
          HOW IT WORKS
        </a>
        <a
          href="#features"
          className="hidden font-mono text-[10px] font-medium leading-3 tracking-[0.12em] text-ink-2 hover:text-ink sm:block"
        >
          FEATURES
        </a>
        <LaunchDemoButton label="LAUNCH DEMO" href="/demo" compact />
      </div>
    </div>
  );
}

function Hero() {
  return (
    <div className="flex flex-col border-b border-hairline px-6 pb-15 pt-16 md:px-12">
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] font-medium leading-3 tracking-[0.16em] text-ink-3">
          PRE-EXECUTION SAFETY FOR AUTONOMOUS ACCOUNTING AGENTS
        </div>
        <svg width="14" height="14" viewBox="0 0 14 14" className="inline-block shrink-0 opacity-45" aria-hidden>
          <path d="M7 0 V14 M0 7 H14" fill="none" stroke="var(--color-ink-3)" />
          <circle cx="7" cy="7" r="3.2" fill="none" stroke="var(--color-ink-3)" />
        </svg>
      </div>
      <div className="mt-9 flex flex-col gap-1.5">
        <div className="font-ui text-[40px] font-bold leading-[50px] tracking-[-0.025em] text-ink md:text-[66px] md:leading-18.5">
          Your agent can act.
        </div>
        <div className="flex flex-wrap items-center">
          <span className="font-ui text-[40px] font-bold leading-[50px] tracking-[-0.025em] text-ink md:text-[66px] md:leading-18.5">
            LedgerGuard&nbsp;
          </span>
          <span className="font-ui text-[40px] font-bold leading-[50px] tracking-[-0.025em] text-approval md:text-[66px] md:leading-18.5">
            decides
          </span>
        </div>
        <div className="font-ui text-[40px] font-bold leading-[50px] tracking-[-0.025em] text-ink md:text-[66px] md:leading-18.5">
          if it should.
        </div>
      </div>
    </div>
  );
}

function HeroSupport() {
  return (
    <div className="flex flex-col gap-10 px-6 pb-16 pt-11 md:px-12 lg:flex-row lg:gap-16">
      <div className="flex max-w-140 grow basis-[0%] flex-col">
        <p className="max-w-130 font-ui text-[15.5px] leading-6.25 text-ink-2">
          LedgerGuard sits between your autonomous accounting agent and its payment rail. Before an agent pays a vendor
          bill, every proposed action is checked against trusted accounting records, the original user's instructions,
          and semantic risk judgments.
        </p>
        <p className="mt-3.5 max-w-130 font-ui text-[15.5px] leading-6.25 text-ink-2">
          A deterministic policy engine returns one of four decisions — an action is allowed, held for approval, asked
          for context, or blocked outright. Nothing moves money by accident.
        </p>
        <div className="mt-9 flex flex-wrap items-center gap-6">
          <LaunchDemoButton label="LAUNCH INTERACTIVE DEMO" href="/demo" />
          <a
            href="#how-it-works"
            className="border-b border-ink-3 pb-1.25 font-mono text-[10.5px] font-medium leading-3.5 tracking-[0.12em] text-ink"
          >
            EXPLORE HOW IT WORKS
          </a>
        </div>
      </div>
      <div className="flex w-full shrink-0 flex-col gap-4 self-start rounded-[4px] border border-hairline bg-surface px-6.5 py-6 lg:w-100">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            EVALUATION PREVIEW · ILLUSTRATIVE SCENARIO
          </div>
          <span className="size-1.75 shrink-0 rounded-full bg-allow" aria-hidden />
        </div>
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <div className="font-mono text-[9.5px] leading-3 tracking-[0.1em] text-ink-3">ACT-0417-02</div>
            <div className="font-ui text-[20px] font-bold leading-6 tracking-[-0.01em] text-ink">Acme Supplies</div>
          </div>
          <div className="font-mono text-[20px] font-semibold leading-6 text-ink">$18,400.00</div>
        </div>
        <div className="h-px shrink-0 bg-hairline" />
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 rounded-[3px] border border-approval/30 bg-approval/8 px-2.5 py-1.25">
            <span className="size-1.5 shrink-0 rounded-full bg-approval" aria-hidden />
            <span className="font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-approval">
              REQUIRE APPROVAL
            </span>
          </span>
          <span className="font-mono text-[10px] font-medium leading-3 tracking-[0.08em] text-ink-2">
            HELD · NOT EXECUTED
          </span>
        </div>
        <div className="font-mono text-[9.5px] leading-3 tracking-[0.08em] text-ink-3">
          PAYMENT DESTINATION UNVERIFIED — POLICY HOLDS THE ACTION. DETAILS SHOWN ARE FIXTURES.
        </div>
      </div>
    </div>
  );
}

function TickerLine() {
  return (
    <div className="flex h-11 shrink-0 items-center gap-4.5 border-b border-hairline px-6 md:px-12">
      <span className="size-1.5 shrink-0 bg-ink" aria-hidden />
      <div className="font-mono text-[9.5px] leading-3 tracking-[0.14em] text-ink-3">
        EVALUATE BEFORE EXECUTION · ALLOW / REQUIRE_APPROVAL / REQUEST_CONTEXT / BLOCK · JEV SEMANTIC LAYER · PHOTON 2.0
        ALERTS · PAYMENTS RUN IN A SIMULATOR ONLY
      </div>
    </div>
  );
}

function PipelineSection() {
  return (
    <div className="flex flex-col px-6 pb-18 pt-16 md:px-12">
      <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
        <div className="flex flex-col gap-3.5">
          <SectionLabel>01 — THE GUARD, IN MOTION</SectionLabel>
          <h2 className="font-ui text-[34px] font-bold leading-10.5 tracking-[-0.02em] text-ink">
            Watch one payment get held.
          </h2>
        </div>
        <div className="pb-1.5 font-mono text-[9.5px] leading-3 tracking-[0.12em] text-ink-3">
          ILLUSTRATIVE FIXTURE — NOT A MEASURED EVALUATION
        </div>
      </div>
    </div>
  );
}

function StationArrow() {
  return (
    <div className="flex w-11 shrink-0 items-center justify-center max-lg:hidden">
      <svg width="44" height="10" viewBox="0 0 44 10" aria-hidden>
        <path d="M0 5 H36" fill="none" stroke="var(--color-ink-3)" />
        <path d="M36 1.8 L43 5 L36 8.2 Z" fill="var(--color-ink-3)" />
      </svg>
    </div>
  );
}

function PipelineRow() {
  return (
    <div className="flex flex-col gap-6 px-6 md:px-12 lg:flex-row lg:gap-0">
      {/* Station 1 */}
      <div className="flex grow basis-[0%] flex-col gap-3 rounded-[4px] border border-hairline bg-surface px-5 pb-4.5 pt-5">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            STATION 01 · INPUT
          </div>
          <div className="font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">14:02:11</div>
        </div>
        <div className="font-ui text-[18px] font-bold leading-5.5 tracking-[-0.01em] text-ink">Agent proposes</div>
        <div className="bg-ink/3 px-3.5 py-3">
          <div className="font-mono text-[11px] leading-4.25 text-ink">
            "Pay Acme Supplies $18,400 for the Apr 21 restock, today."
          </div>
        </div>
        <div className="mt-auto flex items-center gap-2">
          <span className="size-1.5 shrink-0 rounded-full border border-ink-2" aria-hidden />
          <div className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.1em] text-ink-2">
            AUTONOMOUS AGENT · NO HUMAN SEES YET
          </div>
        </div>
      </div>
      <StationArrow />
      {/* Station 2 */}
      <div className="flex grow basis-[0%] flex-col gap-3 rounded-[4px] border border-hairline bg-surface px-5 pb-4.5 pt-5">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            STATION 02 · DETERMINISTIC
          </div>
          <div className="font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">18 MS</div>
        </div>
        <div className="font-ui text-[18px] font-bold leading-5.5 tracking-[-0.01em] text-ink">Accounting checks</div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2 border-b border-hairline/62 py-1.75">
            <span className="size-1.25 shrink-0 rounded-full bg-allow" aria-hidden />
            <div className="grow basis-[0%] font-ui text-[12px] leading-4 text-ink-2">Ledger match on invoice</div>
            <div className="font-mono text-[10px] font-medium leading-3 text-ink-2">0.98</div>
          </div>
          <div className="flex items-center gap-2 border-b border-hairline/62 py-1.75">
            <span className="size-1.25 shrink-0 rounded-full bg-allow" aria-hidden />
            <div className="grow basis-[0%] font-ui text-[12px] leading-4 text-ink-2">Vendor known, terms on file</div>
            <div className="font-mono text-[10px] font-medium leading-3 text-ink-2">0.94</div>
          </div>
          <div className="flex items-center gap-2 py-1.75">
            <span className="size-1.25 shrink-0 bg-block" aria-hidden />
            <div className="grow basis-[0%] font-ui text-[12px] font-medium leading-4 text-ink">
              Destination unverified
            </div>
            <div className="font-mono text-[10px] font-medium leading-3 text-block">FLAG</div>
          </div>
        </div>
        <div className="mt-auto flex items-center gap-2">
          <div className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.1em] text-ink-3">
            TRUSTED FEEDS ONLY — NO ASSUMPTIONS
          </div>
        </div>
      </div>
      <StationArrow />
      {/* Station 3 */}
      <div className="flex grow basis-[0%] flex-col gap-3 rounded-[4px] border border-approval/24 bg-approval/5 px-5 pb-4.5 pt-5">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-approval">
            STATION 03 · SEMANTIC
          </div>
          <div className="font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">214 MS</div>
        </div>
        <div className="font-ui text-[18px] font-bold leading-5.5 tracking-[-0.01em] text-ink">Narrow judgment</div>
        <div className="font-ui text-[12px] leading-4.25 text-ink-2">
          Jev answers one bounded question — does this destination resemble prior verified beneficiaries?
        </div>
        <div className="flex flex-col gap-2.25">
          <div className="h-0.75 w-full shrink-0 overflow-hidden rounded-[2px] bg-ink/10">
            <div className="h-0.75 w-[86%] bg-approval" />
          </div>
          <div className="flex items-center justify-between">
            <div className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.1em] text-ink-2">
              UNLIKE ANY PRIOR DESTINATION
            </div>
            <div className="font-mono text-[11px] font-semibold leading-3.5 text-ink">0.86</div>
          </div>
        </div>
        <div className="mt-auto flex items-center gap-2">
          <div className="rounded-[2px] border border-approval/32 px-1.75 py-0.75">
            <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.12em] text-approval">
              JEV · SYSTEM ONE
            </div>
          </div>
        </div>
      </div>
      <StationArrow />
      {/* Station 4 */}
      <div className="flex grow basis-[0%] flex-col gap-3 rounded-[4px] border border-ink bg-surface px-5 pb-4.5 pt-5">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            STATION 04 · DETERMINISTIC
          </div>
          <div className="font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">44 MS</div>
        </div>
        <div className="font-ui text-[18px] font-bold leading-5.5 tracking-[-0.01em] text-ink">Policy holds it</div>
        <div className="flex w-fit items-center gap-2 rounded-[3px] border border-approval/30 bg-approval/8 px-2.5 py-1.25">
          <span className="size-1.5 shrink-0 rounded-full bg-approval" aria-hidden />
          <span className="font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-approval">
            REQUIRE_APPROVAL
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="w-16 shrink-0 font-mono text-[9.5px] leading-3 tracking-[0.08em] text-ink-3">RULE</div>
            <div className="grow basis-[0%] font-ui text-[12px] font-medium leading-4 text-ink">
              R-04 · unverified destination
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-16 shrink-0 font-mono text-[9.5px] leading-3 tracking-[0.08em] text-ink-3">OUTCOME</div>
            <div className="grow basis-[0%] font-ui text-[12px] font-medium leading-4 text-ink">
              HELD — money did not move
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-16 shrink-0 font-mono text-[9.5px] leading-3 tracking-[0.08em] text-ink-3">NEXT</div>
            <div className="grow basis-[0%] font-ui text-[12px] leading-4 text-ink-2">
              Photon alerts the user · agent cannot proceed
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const HOW_IT_WORKS_STEPS = [
  {
    index: "01",
    title: "Agent proposes",
    description:
      "An autonomous agent intends to pay a vendor bill — an amount, a vendor, a moment. The proposal arrives with its full instruction, not a bare API call.",
    right: (
      <div className="ml-auto flex items-center gap-2">
        <span className="size-1.5 shrink-0 rounded-full border border-ink-3" aria-hidden />
        <span className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.12em] text-ink-3">
          INTENT · PRE-AUTHORIZATION
        </span>
      </div>
    ),
  },
  {
    index: "02",
    title: "LedgerGuard evaluates",
    description:
      "Trusted accounting facts are assembled first. Only where facts run out does Jev answer narrow, bounded questions — never open-ended speculation about the business.",
    right: (
      <div className="ml-auto flex items-center gap-2.5">
        <span className="rounded-[2px] border border-hairline bg-surface px-2 py-0.75 font-mono text-[9px] font-medium leading-3 tracking-[0.1em] text-ink-2">
          FACTS · DETERMINISTIC
        </span>
        <span className="rounded-[2px] border border-approval/30 bg-approval/6 px-2 py-0.75 font-mono text-[9px] font-medium leading-3 tracking-[0.1em] text-approval">
          JUDGMENT · JEV
        </span>
      </div>
    ),
  },
  {
    index: "03",
    title: "Policy decides",
    description:
      "A deterministic policy engine weighs facts and signals into one of four outcomes. Same inputs, same verdict, every time — the reasoning is written down.",
    right: (
      <div className="ml-auto flex items-center gap-1.5">
        <span className="font-mono text-[9px] font-semibold leading-3 tracking-[0.08em] text-allow">ALLOW</span>
        <span className="font-sans text-[10px] leading-3 text-ink-3">/</span>
        <span className="font-mono text-[9px] font-semibold leading-3 tracking-[0.08em] text-approval">
          REQUIRE_APPROVAL
        </span>
        <span className="font-sans text-[10px] leading-3 text-ink-3">/</span>
        <span className="font-mono text-[9px] font-semibold leading-3 tracking-[0.08em] text-context">
          REQUEST_CONTEXT
        </span>
      </div>
    ),
  },
];

function HowItWorks() {
  return (
    <div id="how-it-works" className="flex scroll-mt-8 flex-col px-6 pb-10 pt-18 md:px-12">
      <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
        <div className="flex flex-col gap-3.5">
          <SectionLabel>02 — HOW LEDGERGUARD WORKS</SectionLabel>
          <h2 className="font-ui text-[34px] font-bold leading-10.5 tracking-[-0.02em] text-ink">
            Four stages between intent and money.
          </h2>
          <div className="flex justify-end self-end text-right">
            <div className="max-w-75 font-mono text-[9.5px] leading-3 tracking-[0.12em] text-ink-3">
              FINANCIAL SAFEGUARDS ARE DETERMINISTIC · SEMANTIC JUDGMENTS STAY NARROW
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 flex w-full flex-col">
        {HOW_IT_WORKS_STEPS.map((step) => (
          <div
            key={step.index}
            className="flex w-full flex-col gap-4 border-t border-hairline py-7 md:flex-row md:items-center md:gap-10"
          >
            <div className="w-16 shrink-0 font-mono text-[12px] font-semibold leading-4 tracking-[0.06em] text-ink-3">
              {step.index}
            </div>
            <div className="w-full shrink-0 font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-ink md:w-59">
              {step.title}
            </div>
            <div className="grow basis-[0%] font-ui text-[14px] leading-5.25 text-ink-2">{step.description}</div>
            {step.right}
            <svg width="12" height="10" viewBox="0 0 12 10" className="inline-block shrink-0 opacity-55 max-md:hidden" aria-hidden>
              <path
                d="M1 5 H10 M6.5 1.5 L10 5 L6.5 8.5"
                fill="none"
                stroke="var(--color-ink-3)"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        ))}
        {/* Step 04 — inverted */}
        <div className="flex w-full flex-col gap-4 border-y border-ink bg-ink py-7.5 md:flex-row md:items-center md:gap-10">
          <div className="w-16 shrink-0 font-mono text-[12px] font-semibold leading-4 tracking-[0.06em] text-paper/85">
            04
          </div>
          <div className="w-full shrink-0 font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-paper md:w-59">
            Action enforced
          </div>
          <div className="grow basis-[0%] font-ui text-[14px] leading-5.25 text-paper/78">
            Approved actions execute through a guarded payment simulator. Everything else stops — and every decision,
            signal, and outcome is written to an audit ledger you can read.
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="size-1.5 shrink-0 bg-allow" aria-hidden />
            <span className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.12em] text-paper">
              SIMULATOR + PHOTON 2.0 ALERTS
            </span>
          </div>
          <div className="w-3 shrink-0 max-md:hidden" aria-hidden />
        </div>
      </div>
    </div>
  );
}

function Capabilities() {
  return (
    <div id="features" className="flex scroll-mt-8 flex-col px-6 pt-18 md:px-12">
      <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
        <div className="flex flex-col gap-3.5">
          <SectionLabel>03 — CORE CAPABILITIES</SectionLabel>
          <h2 className="font-ui text-[34px] font-bold leading-10.5 tracking-[-0.02em] text-ink">
            Built for the moment before money moves.
          </h2>
        </div>
        <div className="self-end pb-1.5 text-right font-mono text-[9.5px] leading-3 tracking-[0.12em] text-ink-3">
          EXAMPLES ARE FIXTURES · REAL OUTPUTS ARRIVE WITH THE BACKEND
        </div>
      </div>

      <div className="mt-10 flex flex-col lg:flex-row">
        <div className="flex w-full shrink-0 flex-col border-hairline lg:w-193 lg:border-r">
          <div className="flex flex-col gap-3.5 border-b border-hairline pb-10 pr-0 pt-11 lg:pr-14">
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-[11px] font-semibold leading-3.5 tracking-[0.08em] text-ink-3">1</span>
              <h3 className="font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-ink">
                Pre-execution financial protection.
              </h3>
            </div>
            <p className="max-w-160 font-ui text-[14.5px] leading-5.75 text-ink-2">
              Orders of protection run before any money moves. The agent never fires payment logic into the dark — its
              intent is evaluated in flight, so irreversible mistakes become reviewable ones instead of Sunday-night
              reconciliations.
            </p>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-[9px] font-medium leading-3 tracking-[0.12em] text-ink-3">DECISIONS</span>
              <span className="h-3.5 w-px shrink-0 bg-hairline" aria-hidden />
              <span className="font-mono text-[9.5px] font-semibold leading-3 tracking-[0.06em] text-allow">ALLOW</span>
              <span className="font-sans text-[11px] leading-3.5 text-ink-3">/</span>
              <span className="font-mono text-[9.5px] font-semibold leading-3 tracking-[0.06em] text-approval">
                REQUIRE_APPROVAL
              </span>
              <span className="font-sans text-[11px] leading-3.5 text-ink-3">/</span>
              <span className="font-mono text-[9.5px] font-semibold leading-3 tracking-[0.06em] text-context">
                REQUEST_CONTEXT
              </span>
              <span className="font-sans text-[11px] leading-3.5 text-ink-3">/</span>
              <span className="font-mono text-[9.5px] font-semibold leading-3 tracking-[0.06em] text-block">BLOCK</span>
            </div>
            <div className="w-fit font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
              NO ACTION EXECUTES OUTSIDE THESE FOUR GATES
            </div>
          </div>
          <div className="flex flex-col gap-3.5 pb-11 pt-10 lg:pr-14">
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-[11px] font-semibold leading-3.5 tracking-[0.08em] text-ink-3">2</span>
              <h3 className="font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-ink">
                Explainable, evidence-backed decisions.
              </h3>
            </div>
            <p className="max-w-160 font-ui text-[14.5px] leading-5.75 text-ink-2">
              Every verdict ships with its own paper trail: the facts it trusted, the signals it weighed, the rule that
              fired. No black-box verdicts — open any action and read exactly why it held.
            </p>
            <div className="flex w-fit flex-wrap items-center gap-4.5 rounded-[2px] bg-ink/3 px-3.5 py-2.5">
              <span className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.08em] text-ink-2">FACTS ×3</span>
              <span className="h-3 w-px shrink-0 bg-hairline" aria-hidden />
              <span className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.08em] text-ink-2">
                SIGNALS ×1
              </span>
              <span className="h-3 w-px shrink-0 bg-hairline" aria-hidden />
              <span className="font-mono text-[9.5px] font-medium leading-3 tracking-[0.08em] text-ink-2">RULE R-04</span>
              <span className="h-3 w-px shrink-0 bg-hairline" aria-hidden />
              <span className="font-mono text-[9.5px] font-semibold leading-3 tracking-[0.08em] text-approval">
                OUTCOME: HELD
              </span>
            </div>
          </div>
        </div>

        <div className="flex grow basis-[0%] flex-col">
          <div className="flex flex-col gap-3.5 border-b border-hairline pb-10 pt-11 lg:pl-12">
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-[11px] font-semibold leading-3.5 tracking-[0.08em] text-ink-3">3</span>
              <h3 className="font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-ink">
                Review from wherever you are.
              </h3>
            </div>
            <p className="font-ui text-[14px] leading-5.5 text-ink-2">
              When an action needs a human, a messaging alert is planned to deliver the action and its evidence one tap
              away — shown here as an illustrative concept, not an operational channel.
            </p>
            <div className="mt-2 flex max-w-107.5 flex-col gap-2.5 rounded-[4px] bg-ink px-4.5 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="size-2 shrink-0 bg-approval" aria-hidden />
                  <span className="font-mono text-[9px] font-semibold leading-3 tracking-[0.14em] text-paper">
                    PHOTON 2.0 · ACTION ALERT — CONCEPT
                  </span>
                </div>
                <span className="font-mono text-[9px] leading-3 tracking-[0.08em] text-paper/55">14:02:45 UTC</span>
              </div>
              <div className="font-ui text-[13.5px] font-semibold leading-4.75 text-paper">
                Acme Supplies — $18,400.00 needs your approval
              </div>
              <div className="rounded-[3px] bg-paper/8 px-3 py-2.25">
                <div className="font-mono text-[10px] leading-3.75 text-paper/72">
                  "Agent proposes paying Acme Supplies $18,400 for the Apr 21 restock. Destination unverified — HELD."
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="border-b border-paper/40 pb-0.75 font-mono text-[9.5px] font-semibold leading-3 tracking-[0.1em] text-paper">
                  OPEN ACTION →
                </span>
                <span className="font-mono text-[9px] leading-3 tracking-[0.08em] text-paper/55">
                  REPLY "APPROVE" · "REJECT"
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-3.5 pb-11 pt-10 lg:pl-12">
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-[11px] font-semibold leading-3.5 tracking-[0.08em] text-ink-3">4</span>
              <h3 className="font-ui text-[21px] font-bold leading-6.5 tracking-[-0.015em] text-ink">
                Auditable end to end.
              </h3>
            </div>
            <p className="font-ui text-[14px] leading-5.5 text-ink-2">
              The decision, its evidence, and the execution outcome settle into one ledger — before and after, on the
              record.
            </p>
            <div className="flex max-w-107.5 flex-col">
              {["DECISION WRITTEN WITH POLICY TRACE", "EXECUTION OUTCOME LOGGED", "SIMULATOR TRAIL — NO REAL PAYMENT RAIL"].map(
                (item, index) => (
                  <div
                    key={item}
                    className={`flex items-center gap-2.5 py-2 ${index < 2 ? "border-b border-hairline/62" : ""}`}
                  >
                    <span className="size-1.25 shrink-0 rounded-full bg-allow" aria-hidden />
                    <span className="grow basis-[0%] font-mono text-[10px] leading-3 tracking-[0.08em] text-ink-2">
                      {item}
                    </span>
                  </div>
                ),
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewSheet() {
  const rows = [
    {
      badge: { tone: "allow", label: "ALLOW" },
      id: "ACT-0417-01",
      vendor: "Adobe",
      amount: "$149.00",
      reason: "Vendor verified · invoice matches ledger",
      execution: "EXECUTED",
      latency: "31 ms",
      tinted: false,
    },
    {
      badge: { tone: "approval", label: "REQUIRE APPROVAL" },
      id: "ACT-0417-02",
      vendor: "Acme Supplies",
      amount: "$18,400.00",
      reason: "Unverified payment destination — beneficiary account is not on file",
      execution: "HELD",
      latency: "38 ms",
      tinted: true,
    },
    {
      badge: { tone: "block", label: "BLOCK" },
      id: "ACT-0417-05",
      vendor: "Helios Freight",
      amount: "$2,850.00",
      reason: "Bill already marked paid — duplicate prevented",
      execution: "NOT EXECUTED",
      latency: "22 ms",
      tinted: false,
    },
  ];
  const toneClass: Record<string, string> = {
    allow: "border-allow/28 bg-allow/8 text-allow",
    approval: "border-approval/30 bg-approval/8 text-approval",
    block: "border-block/32 bg-block/9 text-block",
  };
  const dotClass: Record<string, string> = {
    allow: "bg-allow",
    approval: "bg-approval",
    block: "bg-block",
  };

  return (
    <div className="flex flex-col pb-6 pt-18 md:px-12">
      <div className="mb-6 flex flex-col items-start justify-between gap-6 px-6 md:mb-0 md:flex-row md:items-end md:px-0">
        <div className="flex flex-col gap-3.5">
          <SectionLabel>04 — THE POLICY LEDGER, UP CLOSE</SectionLabel>
          <h2 className="font-ui text-[34px] font-bold leading-10.5 tracking-[-0.02em] text-ink">
            This is the operator's ledger.
          </h2>
        </div>
        <div className="self-end pb-1.5 text-right font-mono text-[9.5px] leading-3 tracking-[0.12em] text-ink-3">
          DIRECT PREVIEW OF THE LIVE DASHBOARD · FIXTURE DATA
        </div>
      </div>

      <div className="flex items-center pt-2">
        <div className="hidden w-8.5 shrink-0 justify-center md:flex">
          <svg width="14" height="14" viewBox="0 0 14 14" className="inline-block shrink-0 opacity-50" aria-hidden>
            <path d="M7 0 V14 M0 7 H14" fill="none" stroke="var(--color-ink-3)" />
          </svg>
        </div>
        <div className="flex grow flex-col overflow-hidden rounded-[2px] border border-ink bg-surface">
          <div className="flex h-13 shrink-0 items-center justify-between border-b border-hairline bg-paper px-4 md:px-9">
            <div className="flex items-center gap-3">
              <span className="size-2.75 shrink-0 bg-ink" aria-hidden />
              <span className="font-ui text-[14px] font-bold leading-4.5 tracking-[-0.01em] text-ink">LedgerGuard</span>
              <span className="h-3.25 w-px shrink-0 bg-hairline" aria-hidden />
              <span className="font-mono text-[8px] font-medium leading-2.5 tracking-[0.14em] text-ink-3">
                POLICY LEDGER · OCT 17
              </span>
            </div>
            <div className="flex items-center gap-2.25">
              <span className="size-1.5 shrink-0 rounded-full bg-allow" aria-hidden />
              <span className="font-mono text-[8.5px] font-medium leading-3 tracking-[0.1em] text-ink-2">
                EVALUATOR LIVE
              </span>
            </div>
          </div>
          <div className="flex w-fit gap-8.5 px-4 pb-4.5 pt-5.5 md:px-9">
            {[
              { label: "EVALUATED ACTIONS", value: "05", tone: "" },
              { label: "EXECUTED", value: "01", tone: "" },
              { label: "HELD FOR REVIEW", value: "03", tone: "" },
              { label: "BLOCKED", value: "01", tone: "text-block" },
            ].map((stat, index) => (
              <div key={stat.label} className="flex items-stretch gap-8.5">
                {index > 0 ? <span className="w-px shrink-0 bg-hairline" aria-hidden /> : null}
                <div className="flex flex-col gap-1.75">
                  <span className="font-mono text-[8px] font-medium leading-2.5 tracking-[0.14em] text-ink-3">
                    {stat.label}
                  </span>
                  <span
                    className={`font-mono text-[30px] font-semibold leading-7.5 tracking-[-0.02em] ${
                      stat.tone || "text-ink"
                    }`}
                  >
                    {stat.value}
                  </span>
                </div>
              </div>
            ))}
            <div className="grow basis-[0%]" aria-hidden />
            <div className="flex flex-col items-end gap-1.75">
              <span className="font-mono text-[8px] font-medium leading-2.5 tracking-[0.14em] text-ink-3">
                P50 PROVIDER LATENCY
              </span>
              <span className="flex items-baseline gap-1.25">
                <span className="font-mono text-[30px] font-semibold leading-7.5 tracking-[-0.02em] text-ink">38</span>
                <span className="font-mono text-[9px] leading-3 text-ink-3">ms</span>
              </span>
            </div>
          </div>
          <div className="flex w-full flex-col overflow-x-auto">
            <div className="flex h-7.5 min-w-[720px] shrink-0 items-center gap-5 border-y border-hairline bg-paper px-4 md:px-9">
              {["DECISION", "VENDOR · ACTION ID", "AMOUNT", "REASON · POLICY BASIS", "EXECUTION", "LATENCY"].map(
                (heading, index) => (
                  <div
                    key={heading}
                    className={`font-mono text-[7.5px] font-medium leading-2.5 tracking-[0.14em] text-ink-3 ${
                      index === 0
                        ? "w-37.5 shrink-0"
                        : index === 1
                          ? "w-47.5 shrink-0"
                          : index === 2
                            ? "w-27.5 shrink-0 text-right"
                            : index === 3
                              ? "grow basis-[0%]"
                              : index === 4
                                ? "w-27.5 shrink-0"
                                : "w-17.5 shrink-0 text-right"
                    }`}
                  >
                    {heading}
                  </div>
                ),
              )}
            </div>
            {rows.map((row) => (
              <div
                key={row.id}
                className={`flex h-13.5 min-w-[720px] shrink-0 items-center gap-5 border-b border-hairline px-4 md:px-9 ${
                  row.tinted ? "bg-ink/3" : ""
                }`}
              >
                <div className="w-37.5 shrink-0">
                  <span
                    className={`inline-flex items-center gap-1.75 rounded-[2px] border px-2 py-1 ${toneClass[row.badge.tone]}`}
                  >
                    <span className={`size-1.25 shrink-0 rounded-full ${dotClass[row.badge.tone]}`} aria-hidden />
                    <span className="font-mono text-[8.5px] font-semibold leading-3 tracking-[0.06em]">
                      {row.badge.label}
                    </span>
                  </span>
                </div>
                <div className="flex w-47.5 shrink-0 flex-col gap-0.5">
                  <span className="font-mono text-[7px] leading-2.5 tracking-[0.1em] text-ink-3">{row.id}</span>
                  <span className="font-ui text-[12.5px] font-medium leading-4 text-ink">{row.vendor}</span>
                </div>
                <div className="w-27.5 shrink-0 text-right font-mono text-[12.5px] font-semibold leading-4 text-ink">
                  {row.amount}
                </div>
                <div className="grow basis-[0%] font-ui text-[11.5px] leading-3.5 text-ink-2">{row.reason}</div>
                <div
                  className={`w-27.5 shrink-0 font-mono text-[9px] font-medium leading-3 tracking-[0.06em] ${
                    row.execution === "EXECUTED" ? "text-ink-2" : "text-ink-3"
                  }`}
                >
                  {row.execution}
                </div>
                <div className="w-17.5 shrink-0 text-right font-mono text-[10px] leading-3 text-ink-3">
                  {row.latency}
                </div>
              </div>
            ))}
            <div className="flex h-9.5 shrink-0 items-center justify-between px-4 md:px-9">
              <span className="font-mono text-[7.5px] leading-2.5 tracking-[0.12em] text-ink-3">
                SOURCE FACTS · QUICKBOOKS SPONSOR DATASET + DISCLOSED OVERLAYS
              </span>
              <Link to="/dashboard" className="font-mono text-[7.5px] font-medium leading-2.5 tracking-[0.12em] text-ink-2">
                OPEN IN DEMO →
              </Link>
            </div>
          </div>
        </div>
        <div className="hidden w-8.5 shrink-0 justify-center md:flex">
          <svg width="14" height="14" viewBox="0 0 14 14" className="inline-block shrink-0 opacity-50" aria-hidden>
            <path d="M7 0 V14 M0 7 H14" fill="none" stroke="var(--color-ink-3)" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function FinalCta() {
  return (
    <div className="flex flex-col items-start justify-between gap-12 border-y border-ink px-6 py-16 md:px-12 md:py-24 lg:flex-row lg:items-center">
      <div className="flex max-w-190 flex-col gap-5.5">
        <SectionLabel>05 — YOUR TURN</SectionLabel>
        <h2 className="font-ui text-[40px] font-bold leading-[48px] tracking-[-0.025em] text-ink md:text-[52px] md:leading-15">
          See the guard hold its first payment.
        </h2>
        <p className="max-w-140 font-ui text-[15px] leading-6 text-ink-2">
          The demo runs the full evaluation loop on illustrative fixtures — proposals, facts, judgments, decisions.
          Simulated execution only; no real payments.
        </p>
      </div>
      <div className="flex flex-col items-start gap-4 lg:items-end">
        <Link
          to="/demo"
          className="flex h-14 shrink-0 items-center gap-3 rounded-[3px] bg-ink px-7.5 transition-opacity hover:opacity-90"
        >
          <span className="font-mono text-[12px] font-semibold leading-4 tracking-[0.12em] text-surface">
            LAUNCH INTERACTIVE DEMO
          </span>
          <svg width="13" height="11" viewBox="0 0 12 10" className="inline-block shrink-0" aria-hidden>
            <path
              d="M1 5 H10 M6.5 1.5 L10 5 L6.5 8.5"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Link>
        <span className="font-mono text-[9px] leading-3 tracking-[0.12em] text-ink-3">
          THE DEMO RUNS ON THE LIVE BACKEND ONCE IT IS STARTED
        </span>
      </div>
    </div>
  );
}

function LandingFooter() {
  return (
    <div className="flex flex-col">
      <div className="flex flex-col gap-12 px-6 pb-12 pt-14 lg:flex-row lg:gap-16 lg:px-12">
        <div className="flex w-full shrink-0 flex-col gap-4 lg:w-100">
          <div className="flex items-center gap-2.5">
            <span className="size-3.5 shrink-0 bg-ink" aria-hidden />
            <span className="font-ui text-[17px] font-bold leading-5.5 tracking-[-0.01em] text-ink">LedgerGuard</span>
          </div>
          <p className="max-w-90 font-ui text-[13.5px] leading-5.25 text-ink-2">
            A pre-execution financial safety layer for autonomous AI accounting agents. Proposals are evaluated against
            trusted records, the user's own instructions, and narrow semantic judgments — then a deterministic policy
            decides what money may do.
          </p>
          <div className="font-mono text-[9px] leading-3 tracking-[0.14em] text-ink-3">
            EVALUATE FIRST · EXECUTE IN A SIMULATOR · LOG EVERYTHING
          </div>
        </div>
        <div className="grow basis-[0%]" aria-hidden />
        <div className="flex flex-col gap-10 sm:flex-row lg:gap-18">
          <div className="flex flex-col gap-3.5">
            <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">PAGE</div>
            <a href="#how-it-works" className="font-ui text-[13px] font-medium leading-4 text-ink-2 hover:text-ink">
              How it works
            </a>
            <a href="#features" className="font-ui text-[13px] font-medium leading-4 text-ink-2 hover:text-ink">
              Features
            </a>
            <Link to="/demo" className="font-ui text-[13px] font-bold leading-4 text-ink">
              Launch demo
            </Link>
          </div>
          <div className="flex flex-col gap-3.5">
            <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">SYSTEM</div>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">Policy engine v1</span>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">Jev semantic layer</span>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">Guarded payment simulator</span>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">Photon alerts — separate workstream</span>
          </div>
          <div className="flex flex-col gap-3.5">
            <div className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">PROJECT</div>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">LA Hacks 2026</span>
            <span className="font-mono text-[10.5px] leading-3.5 text-ink-2">Built as a hack — no claims implied</span>
          </div>
        </div>
      </div>
      <div className="flex shrink-0 flex-col gap-2 border-t border-hairline px-6 py-3 md:h-13 md:flex-row md:items-center md:justify-between md:px-12 md:py-0">
        <span className="font-mono text-[9px] leading-3 tracking-[0.12em] text-ink-3">
          © 2026 LEDGERGUARD · A LA HACKS PROJECT · ILLUSTRATIVE FIXTURES THROUGHOUT
        </span>
        <span className="font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">
          DECISIONS · ALLOW / REQUIRE_APPROVAL / REQUEST_CONTEXT / BLOCK
        </span>
      </div>
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <LandingNav />
      <Hero />
      <HeroSupport />
      <TickerLine />
      <PipelineSection />
      <PipelineRow />
      <HowItWorks />
      <Capabilities />
      <PreviewSheet />
      <FinalCta />
      <LandingFooter />
    </div>
  );
}
