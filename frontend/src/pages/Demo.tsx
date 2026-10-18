import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAction, useDemoRun, useHealth } from "../api/queries";
import { useStream } from "../api/stream";
import type { ActionDetail, LedgerEvent } from "../api/types";
import { ActionDrawer } from "../components/ActionDrawer";
import { DecisionBadge } from "../components/DecisionBadge";
import { PageFooter, PageHeader } from "../components/PageChrome";
import { ErrorState } from "../components/StatePanels";
import { GhostButton, MonoLabel, MonoValue, PrimaryButton } from "../components/ui";
import { DEMO_PROVIDERS, SCENARIOS } from "../config/scenarios";
import { DECISION_META, PROVIDER_LABELS, reasonCodeLabel } from "../lib/decisions";
import { formatAmount, formatLatency, formatUtcTime, shortId } from "../lib/format";

type StageStatus = "pending" | "active" | "done";

interface StageView {
  key: string;
  index: string;
  title: string;
  sub: string;
  right: { text: string; tone: "ink" | "allow" | "approval" | "context" | "block" | "muted" };
  status: StageStatus;
}

const EVENT_TONE: Record<string, string> = {
  policy_decision: "text-ink font-semibold",
  execution_simulated: "text-allow font-semibold",
  action_blocked: "text-block font-semibold",
  review_required: "text-approval",
  context_requested: "text-context",
};

function mutatingLabel(detail: ActionDetail | null): string {
  return detail ? "LIVE" : "PENDING";
}

function buildStages(
  detail: ActionDetail | null,
  events: LedgerEvent[],
  runInFlight: boolean,
  liveActionId: string | null,
): StageView[] {
  // Only trust events that belong to the action we are actually tracking.
  const forAction = liveActionId ? events.filter((event) => event.action_id === liveActionId) : [];
  const has = (type: string) => forAction.some((event) => event.type === type);

  const decision = detail?.policy_decision ?? null;
  const outcome = detail?.provider_outcome ?? null;
  const receivedDone = Boolean(detail) || has("action_received");
  const precheckDone = has("precheck_complete") || Boolean(decision);
  const providerDone = has("provider_started") || Boolean(outcome);
  const riskDone = Boolean(outcome) || has("risk_assessment_ready");
  const policyDone = Boolean(decision);
  const outcomeDone = Boolean(
    detail &&
      (detail.execution_result ||
        detail.final_action === "BLOCK" ||
        (detail.human_response && decision?.final_action !== "REQUIRE_APPROVAL") ||
        decision?.final_action === "REQUIRE_APPROVAL" ||
        decision?.final_action === "REQUEST_CONTEXT"),
  );

  const outcomeText = !detail
    ? "PENDING"
    : detail.execution_result
      ? "SIMULATED"
      : decision?.final_action === "BLOCK"
        ? "BLOCKED — TERMINAL"
        : decision?.final_action === "REQUIRE_APPROVAL"
          ? "HELD FOR REVIEW"
          : decision?.final_action === "REQUEST_CONTEXT"
            ? "AWAITING CONTEXT"
            : "PENDING";

  const outcomeTone =
    detail?.execution_result || decision?.final_action === "ALLOW"
      ? "allow"
      : decision?.final_action === "BLOCK"
        ? "block"
        : decision?.final_action === "REQUIRE_APPROVAL"
          ? "approval"
          : decision?.final_action === "REQUEST_CONTEXT"
            ? "context"
            : "muted";

  const status = (done: boolean): StageStatus => {
    if (done) return "done";
    if (!runInFlight) return "pending";
    return "active";
  };

  const firstPending = [receivedDone, precheckDone, providerDone, riskDone, policyDone, outcomeDone].findIndex(
    (done) => !done,
  );

  const stages: StageView[] = [
    {
      key: "received",
      index: "01",
      title: "Action received",
      sub: detail
        ? `${detail.action.action_type.replaceAll("_", " ")} · PROPOSED ACTION PERSISTED TO THE AUDIT LEDGER`
        : "THE AGENT PROPOSAL IS WRITTEN DOWN BEFORE ANY EVALUATION",
      right: { text: detail ? `${formatUtcTime(detail.created_at)} UTC` : "—", tone: "muted" },
      status: status(receivedDone),
    },
    {
      key: "precheck",
      index: "02",
      title: "Prechecks complete",
      sub: "DETERMINISTIC HARD RULES — AMOUNT · CURRENCY · ACCOUNTS · DUPLICATES",
      right: {
        text: precheckDone ? "HARD RULES PASS" : "—",
        tone: "muted",
      },
      status: status(precheckDone),
    },
    {
      key: "provider",
      index: "03",
      title: "Provider started",
      sub: "ONE SHARED ACCOUNTING SNAPSHOT IS SENT TO THE SELECTED PROVIDER",
      right: {
        text: outcome
          ? `${outcome.provider.toUpperCase()} · ${(outcome.model_name ?? "—").toUpperCase()}`
          : "—",
        tone: "muted",
      },
      status: status(providerDone),
    },
    {
      key: "risk",
      index: "04",
      title: "Risk assessment ready",
      sub: "FIVE SEMANTIC SIGNALS — OR A TYPED FAILURE; NEVER FABRICATED OUTPUT",
      right: {
        text: outcome
          ? outcome.outcome === "success"
            ? `${formatLatency(outcome.latency_ms).toUpperCase()}`
            : outcome.code
          : "—",
        tone: outcome && outcome.outcome === "failure" ? "block" : "muted",
      },
      status: status(riskDone),
    },
    {
      key: "policy",
      index: "05",
      title: "Policy decision",
      sub: "DETERMINISTIC ENGINE — THE SOLE AUTHORITY THAT CAN AUTHORIZE EXECUTION",
      right: {
        text: decision ? `${decision.final_action} · ${decision.reason_codes[0] ?? ""}` : "—",
        tone: "ink",
      },
      status: status(policyDone),
    },
    {
      key: "outcome",
      index: "06",
      title: "Outcome",
      sub: "SIMULATOR · REVIEW · CONTEXT REQUEST · OR BLOCK — NOTHING ELSE",
      right: { text: outcomeText, tone: outcomeTone as StageView["right"]["tone"] },
      status: status(outcomeDone || (runInFlight && firstPending === 5)),
    },
  ];

  return stages;
}

function StatusDot({ status, tone }: { status: StageStatus; tone: string }) {
  if (status === "pending") {
    return <span className="size-1.75 shrink-0 rounded-full border border-ink-3" aria-hidden />;
  }
  if (status === "active") {
    return <span className="size-1.75 shrink-0 animate-pulse rounded-full bg-approval" aria-hidden />;
  }
  return <span className={`size-1.75 shrink-0 rounded-full ${tone}`} aria-hidden />;
}

const TONE_CLASS: Record<string, string> = {
  ink: "bg-ink",
  allow: "bg-allow",
  approval: "bg-approval",
  context: "bg-context",
  block: "bg-block",
  muted: "bg-ink-2",
};

export function DemoPage() {
  const { actionId } = useParams<{ actionId?: string }>();
  const navigate = useNavigate();
  const health = useHealth();
  const stream = useStream();

  const [scenarioId, setScenarioId] = useState(SCENARIOS[0].id);
  const [provider, setProvider] = useState("rules");
  const [liveActionId, setLiveActionId] = useState<string | null>(null);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);

  const run = useDemoRun();
  const detailQuery = useAction(liveActionId);
  const detail = detailQuery.data ?? (run.data && run.data.action_id === liveActionId ? run.data : null);

  // While the POST is in flight, pick up the freshly created action from SSE.
  useEffect(() => {
    if (!runStartedAt) return;
    const candidate = [...stream.events]
      .reverse()
      .find(
        (event) =>
          event.type === "action_received" &&
          event.payload?.scenario_id === scenarioId &&
          new Date(event.timestamp).getTime() >= runStartedAt - 1000,
      );
    if (candidate && candidate.action_id !== liveActionId) setLiveActionId(candidate.action_id);
  }, [stream.events, runStartedAt, scenarioId, liveActionId]);

  const runInFlight = run.isPending;
  const activeEvents = useMemo(
    () => (liveActionId ? stream.events.filter((event) => event.action_id === liveActionId) : stream.events),
    [stream.events, liveActionId],
  );

  const stages = buildStages(detail, activeEvents, runInFlight, liveActionId);

  const startRun = () => {
    setLiveActionId(null);
    setRunStartedAt(Date.now());
    run.mutate(
      {
        scenario_id: scenarioId,
        provider,
        idempotency_key: `ui-demo-${scenarioId}-${crypto.randomUUID()}`,
      },
      {
        onSuccess: (value) => setLiveActionId(value.action_id),
      },
    );
  };

  const demoProviders = health.data?.providers ?? [...DEMO_PROVIDERS];
  const availableProviders = health.data?.providers ?? [];
  const decision = detail?.policy_decision ?? null;

  useEffect(() => {
    if (health.data?.providers.length && !health.data.providers.includes(provider)) {
      setProvider(health.data.providers[0]);
    }
  }, [health.data?.providers, provider]);

  return (
    <div className="flex min-h-0 grow flex-col">
      <PageHeader
        title="Live demo"
        caption="ONE PROPOSED ACTION, EVALUATED END-TO-END BY THE REAL PIPELINE · SIMULATED EXECUTION ONLY"
        right={
          <span
            className={`flex items-center gap-2 rounded-[3px] border px-2.5 py-1.25 ${
              stream.status === "connected"
                ? "border-allow/28 bg-allow/8"
                : "border-approval/30 bg-approval/8"
            }`}
          >
            <span
              className={`size-1.5 shrink-0 rounded-full ${
                stream.status === "connected" ? "bg-allow" : "bg-approval"
              }`}
              aria-hidden
            />
            <span
              className={`font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] ${
                stream.status === "connected" ? "text-allow" : "text-approval"
              }`}
            >
              {stream.status === "connected" ? `SSE CONNECTED · EVENT #${stream.lastEventId}` : "SSE RETRYING"}
            </span>
          </span>
        }
      />

      <div className="mt-4 flex grow flex-col gap-8 px-6 pb-6 md:flex-row md:items-start md:px-12">
        {/* Scenario picker */}
        <div className="flex w-full shrink-0 flex-col gap-3 md:w-[360px]">
          <MonoLabel>01 — CHOOSE A SCENARIO</MonoLabel>
          <div className="flex flex-col border border-b-0 border-hairline bg-surface">
            {SCENARIOS.map((scenario) => {
              const selected = scenario.id === scenarioId;
              return (
                <button
                  key={scenario.id}
                  type="button"
                  onClick={() => setScenarioId(scenario.id)}
                  className={`flex h-[58px] items-center justify-between gap-3 border-b border-hairline px-4 text-left transition-colors ${
                    selected
                      ? "border-l-2 border-l-ink bg-ink/3 pl-3.5"
                      : "border-l-2 border-l-transparent hover:bg-ink/3"
                  }`}
                >
                  <span className="flex min-w-0 flex-col gap-0.75">
                    <span className="truncate font-mono text-[10px] leading-3 tracking-[0.1em] text-ink-3">
                      {scenario.id}
                    </span>
                    <span
                      className={`truncate font-ui text-[13px] leading-[18px] ${
                        selected ? "font-semibold" : "font-medium"
                      } text-ink`}
                    >
                      {scenario.title}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
          <p className="font-mono text-[10px] leading-3.5 tracking-[0.08em] text-ink-3">
            {SCENARIOS.find((scenario) => scenario.id === scenarioId)?.description.toUpperCase()}
          </p>

          <MonoLabel className="mt-2">PROVIDER</MonoLabel>
          <div className="flex overflow-hidden rounded-[3px] border border-hairline">
            {demoProviders.map((name) => {
              const enabled = health.isLoading || availableProviders.includes(name);
              const selected = provider === name;
              return (
                <button
                  key={name}
                  type="button"
                  disabled={!enabled}
                  onClick={() => setProvider(name)}
                  title={enabled ? (PROVIDER_LABELS[name] ?? name) : "Provider is not registered on this server"}
                  className={`h-8 flex-1 basis-0 border-r border-hairline font-mono text-[10px] leading-3 tracking-[0.08em] last:border-r-0 ${
                    selected
                      ? "bg-ink font-semibold text-surface"
                      : enabled
                        ? "font-medium text-ink-3 hover:text-ink-2"
                        : "cursor-not-allowed font-medium text-ink-3/50"
                  }`}
                >
                  {name.replace("_", " ").toUpperCase()}
                </button>
              );
            })}
          </div>

          <PrimaryButton onClick={startRun} disabled={run.isPending} className="mt-1 h-11! w-full">
            {run.isPending ? "Evaluating…" : "Run evaluation"}
            {!run.isPending ? <span className="font-mono text-[13px]">→</span> : null}
          </PrimaryButton>
          <MonoLabel className="tracking-[0.08em]!">
            EACH RUN STORES A NEW AUDITED ACTION — POST /api/demo/run
          </MonoLabel>

          {run.isError ? <ErrorState error={run.error} onRetry={startRun} /> : null}
        </div>

        {/* Pipeline */}
        <div className="flex min-w-0 grow flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <MonoLabel>02 — EVALUATION</MonoLabel>
            <MonoLabel className="hidden tracking-[0.08em]! lg:block">
              SSE NOTIFICATIONS · ACTION DETAIL REFETCHED PER EVENT
            </MonoLabel>
          </div>
          <div className="flex flex-col border border-hairline">
            {stages.map((stage) => (
              <div
                key={stage.key}
                className={`flex min-h-16 items-center gap-3.5 border-b border-hairline px-4 py-2.5 last:border-b-0 ${
                  stage.status === "done" && (stage.key === "policy" || stage.key === "outcome") ? "bg-surface" : ""
                }`}
              >
                <span className="w-5 shrink-0 font-mono text-[10px] tracking-[0.1em] text-ink-3">{stage.index}</span>
                <StatusDot status={stage.status} tone={TONE_CLASS[stage.right.tone]} />
                <span className="flex min-w-0 grow flex-col gap-0.75">
                  <span className="truncate font-ui text-[13px] font-medium leading-[18px] text-ink">
                    {stage.title}
                  </span>
                  <span className="font-mono text-[10px] leading-3.5 tracking-[0.08em] text-ink-3">
                    {stage.sub}
                  </span>
                </span>
                <span
                  className={`max-w-[42%] shrink-0 [overflow-wrap:anywhere] text-right font-mono text-[10px] leading-3.5 tracking-[0.06em] ${
                    stage.right.tone === "muted"
                      ? "text-ink-3"
                      : stage.right.tone === "ink"
                        ? "font-semibold text-ink"
                        : stage.right.tone === "allow"
                          ? "font-semibold text-allow"
                          : stage.right.tone === "approval"
                            ? "font-semibold text-approval"
                            : stage.right.tone === "context"
                              ? "font-semibold text-context"
                              : "font-semibold text-block"
                  }`}
                >
                  {stage.right.text}
                </span>
              </div>
            ))}
          </div>

          {/* Result strip */}
          {detail?.policy_decision ? (
            <div className="flex flex-col gap-2.5 rounded-[3px] border border-hairline bg-surface p-[18px]">
              <div className="flex items-center justify-between gap-3">
                <DecisionBadge action={detail.policy_decision.final_action} />
                <MonoLabel className="tracking-[0.08em]!">
                  {detail.policy_decision.reason_codes.join(" · ")} · CONFIG V{detail.policy_decision.config_version}
                </MonoLabel>
              </div>
              <p className="font-ui text-[15px] font-semibold leading-5 tracking-[-0.005em] text-ink">
                {detail.execution_result
                  ? "Simulated execution recorded — no real payment rail."
                  : detail.policy_decision.final_action === "BLOCK"
                    ? "Blocked by policy — this action is terminal."
                    : detail.policy_decision.final_action === "REQUIRE_APPROVAL"
                      ? "Held for a human decision — open the audit to review the evidence."
                      : "Context required — supply the missing fact to re-evaluate."}
              </p>
              <MonoValue className="tracking-[0.08em]!">
                {detail.policy_decision.reason_codes.map(reasonCodeLabel).join(" · ")}
              </MonoValue>
              <MonoValue className="tracking-[0.08em]!">
                ACTION {shortId(detail.action_id)} · AUDIT {shortId(detail.audit_id)} · ASSESSMENT{" "}
                {shortId(detail.policy_decision.assessment_hash, 12)}
              </MonoValue>
              <div className="mt-1 flex flex-wrap items-center gap-2.5">
                <PrimaryButton onClick={() => navigate(`/demo/actions/${detail.action_id}`)} className="h-10!">
                  Open audit <span className="font-mono text-[12px]">→</span>
                </PrimaryButton>
                <GhostButton onClick={() => navigate(`/dashboard/actions/${detail.action_id}`)} className="h-10!">
                  View in ledger
                </GhostButton>
                {detail.policy_decision.final_action === "REQUIRE_APPROVAL" ||
                detail.policy_decision.final_action === "REQUEST_CONTEXT" ? (
                  <GhostButton onClick={() => navigate("/review")} className="h-10!">
                    Open review queue
                  </GhostButton>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2 rounded-[3px] border border-dashed border-hairline px-[18px] py-4">
              <MonoValue className="tracking-[0.08em]!">
                {runInFlight
                  ? mutatingLabel(detail) + " — THE PIPELINE IS RUNNING; STAGES ANIMATE AS EVENTS ARRIVE"
                  : "PICK A SCENARIO AND RUN IT — THE SIX STAGES LIGHT UP FROM REAL EVENTS"}
              </MonoValue>
              <MonoLabel className="tracking-[0.08em]!">
                DECISION STATES · ALLOW / REQUIRE_APPROVAL / REQUEST_CONTEXT / BLOCK
              </MonoLabel>
            </div>
          )}
        </div>

        {/* Event log */}
        <div className="flex w-full shrink-0 flex-col gap-3 md:w-[300px]">
          <MonoLabel>03 — LIVE EVENTS · SSE</MonoLabel>
          <div className="flex flex-col border border-hairline">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
              <span className="flex items-center gap-2.25">
                <span
                  className={`size-1.5 shrink-0 rounded-full ${
                    stream.status === "connected" ? "bg-allow" : "bg-approval"
                  }`}
                  aria-hidden
                />
                <MonoLabel className="tracking-[0.06em]! text-ink-2!">
                  {stream.status === "connected" ? "CONNECTED" : "RETRYING"}
                </MonoLabel>
              </span>
              <MonoLabel className="tracking-[0.08em]!">/api/stream</MonoLabel>
            </div>
            <div className="flex flex-col gap-2.25 px-4 py-3.5">
              {activeEvents.length === 0 ? (
                <MonoLabel className="tracking-[0.08em]!">NO EVENTS YET — RUN A SCENARIO</MonoLabel>
              ) : (
                activeEvents
                  .slice(-12)
                  .map((event) => (
                    <span key={event.event_id} className="flex items-baseline gap-2.5">
                      <span className="w-9 shrink-0 font-mono text-[10px] leading-3.5 text-ink-3">
                        #{event.event_id}
                      </span>
                      <span
                        className={`grow basis-[0%] truncate font-mono text-[10px] leading-3.5 ${
                          EVENT_TONE[event.type] ?? "text-ink-3"
                        }`}
                      >
                        {event.type}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] leading-3.5 text-ink-3">
                        {formatUtcTime(event.timestamp)}
                      </span>
                    </span>
                  ))
              )}
            </div>
            <div className="border-t border-hairline px-4 py-2.5">
              <MonoLabel className="tracking-[0.08em]!">
                REPLAY FROM last_event_id ON RECONNECT · HEARTBEAT 15 S
              </MonoLabel>
            </div>
          </div>
          <MonoLabel className="tracking-[0.08em]!">
            SSE IS A NOTIFICATION ONLY — ACTION DETAIL IS REFETCHED AFTER EVERY EVENT.
          </MonoLabel>
          {detail ? (
            <div className="flex flex-col gap-2 border border-hairline px-4 py-3.5">
              <MonoLabel>RUN RESULT</MonoLabel>
              <span className="flex items-center gap-2">
                <DecisionBadge action={detail.final_action} />
                <span className="font-mono text-[11px] font-semibold text-ink">
                  {formatAmount(detail.action.amount, detail.action.currency)}
                </span>
              </span>
              <MonoLabel className="tracking-[0.08em]!">
                {detail.action.vendor_name ?? detail.action.counterparty_name ?? "UNNAMED COUNTERPARTY"}
              </MonoLabel>
              <MonoLabel className="tracking-[0.08em]!">
                {decision ? DECISION_META[decision.final_action].blurb.toUpperCase() : ""}
              </MonoLabel>
            </div>
          ) : null}
        </div>
      </div>

      <PageFooter
        left="PIPELINE · POST /api/demo/run → LANGGRAPH → POLICY ENGINE → GUARDED SIMULATOR"
        right="SIMULATED EXECUTION ONLY — NO REAL PAYMENT RAIL"
      />

      {actionId ? <ActionDrawer actionId={actionId} onClose={() => navigate("/demo")} /> : null}
    </div>
  );
}
