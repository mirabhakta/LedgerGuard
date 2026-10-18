import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { useStream } from "../api/stream";
import type {
  ActionDetail,
  AuditEvent,
  ContextResponse,
  HumanReviewResponse,
  ProviderFailure,
  RiskAssessment,
} from "../api/types";
import { CONTEXT_UPDATE_FIELDS, SIGNAL_LABELS, reasonCodeLabel } from "../lib/decisions";
import { formatAmount, formatLatency, formatUtcTime, shortId } from "../lib/format";
import { DecisionBadge } from "./DecisionBadge";
import { ErrorState, ProviderFailureNotice } from "./StatePanels";
import { GhostButton, LabeledRow, MonoLabel, MonoValue, PrimaryButton } from "./ui";

export const DEMO_ACTOR = "demo-reviewer@ledgerguard.app";

function SectionHeader({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <MonoLabel>{children}</MonoLabel>
      {right}
    </div>
  );
}

function isReviewResponse(value: ActionDetail["human_response"]): value is HumanReviewResponse {
  return value !== null && "approved" in value;
}

function isContextResponse(value: ActionDetail["human_response"]): value is ContextResponse {
  return value !== null && "updates" in value;
}

function decisionEvent(detail: ActionDetail): AuditEvent | undefined {
  return detail.audit_events.find((event) => event.type === "policy_decision");
}

function executionEvent(detail: ActionDetail): AuditEvent | undefined {
  return detail.audit_events.find((event) => event.type === "execution_simulated");
}

function summarizeEventPayload(event: AuditEvent): string {
  const payload = event.payload ?? {};
  switch (event.type) {
    case "policy_decision":
      return `${String(payload.final_action ?? "")} · ${(payload.reason_codes as string[] | undefined)?.join(", ") ?? ""}`;
    case "risk_assessment_ready":
      return `outcome ${String(payload.outcome ?? "unknown")}`;
    case "execution_simulated":
      return "simulated execution recorded";
    case "review_required":
      return "awaiting human review";
    case "context_requested":
      return "awaiting operator context";
    case "review_resolved":
      return `resolution ${String(payload.resolution ?? "")} by ${String(payload.actor ?? "")}`;
    case "context_supplied":
      return `context supplied by ${String(payload.actor ?? "")}`;
    case "action_blocked":
      return payload.code ? `code ${String(payload.code)}` : "terminal";
    case "action_received":
      return payload.scenario_id ? `scenario ${String(payload.scenario_id)}` : "";
    default:
      return "";
  }
}

const EVENT_TONE: Record<string, string> = {
  policy_decision: "text-ink",
  execution_simulated: "text-allow",
  action_blocked: "text-block",
  review_required: "text-approval",
  context_requested: "text-context",
};

function SignalRow({
  label,
  question,
  probability,
  confidence,
  highlight,
}: {
  label: string;
  question: string;
  probability: number;
  confidence: number;
  highlight: boolean;
}) {
  const width = Math.max(0, Math.min(100, Math.round(probability * 100)));
  return (
    <div
      className={`flex flex-col gap-2.5 rounded-[3px] border px-4 py-3.5 ${
        highlight ? "border-approval/18 bg-approval/5" : "border-hairline bg-transparent"
      }`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-ui text-[13px] font-semibold leading-4 text-ink">{label}</span>
        <span className="font-mono text-[12px] font-semibold leading-4 text-ink">{probability.toFixed(2)}</span>
      </div>
      <div className="h-0.75 w-full shrink-0 overflow-hidden rounded-[2px] bg-ink/10">
        <div className={`h-full ${highlight ? "bg-approval" : "bg-ink-2"}`} style={{ width: `${width}%` }} />
      </div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-ui text-[11.5px] leading-4 text-ink-2">{question}</span>
        <span className="font-mono text-[9px] leading-3 tracking-[0.08em] text-ink-3">
          CONF {confidence.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

function ContextForm({
  detail,
  onSubmit,
  isPending,
}: {
  detail: ActionDetail;
  onSubmit: (updates: Record<string, unknown>, provenance: string) => void;
  isPending: boolean;
}) {
  const [field, setField] = useState<(typeof CONTEXT_UPDATE_FIELDS)[number]>("vendor_id");
  const [value, setValue] = useState("");
  const [extra, setExtra] = useState<Array<{ field: string; value: string }>>([]);
  const [provenance, setProvenance] = useState("");

  const addField = () => {
    if (!value.trim()) return;
    setExtra((prev) => [...prev, { field, value: value.trim() }]);
    setValue("");
  };

  const submit = () => {
    const updates: Record<string, unknown> = {};
    for (const entry of extra) updates[entry.field] = entry.value;
    if (value.trim()) updates[field] = value.trim();
    onSubmit(updates, provenance.trim() || "Operator supplied context from the review queue");
  };

  return (
    <div className="flex flex-col gap-3">
      <MonoLabel>SUPPLY MISSING CONTEXT · SUPPORTED FIELDS ONLY</MonoLabel>
      <div className="flex flex-col gap-2">
        {extra.map((entry) => (
          <div key={entry.field} className="flex items-center justify-between gap-3 border border-hairline px-3 py-2">
            <span className="font-mono text-[10px] tracking-[0.06em] text-ink-3">{entry.field}</span>
            <span className="truncate font-ui text-[12.5px] text-ink">{entry.value}</span>
          </div>
        ))}
        <div className="flex gap-2">
          <select
            value={field}
            onChange={(event) => setField(event.target.value as (typeof CONTEXT_UPDATE_FIELDS)[number])}
            className="h-10 shrink-0 rounded-[3px] border border-hairline bg-surface px-2 font-mono text-[10px] tracking-[0.06em] text-ink"
          >
            {CONTEXT_UPDATE_FIELDS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="value"
            className="h-10 min-w-0 grow rounded-[3px] border border-hairline bg-surface px-3 font-ui text-[13px] text-ink placeholder:text-ink-3"
          />
          <GhostButton onClick={addField} className="h-10! px-3!">
            Add
          </GhostButton>
        </div>
        <textarea
          value={provenance}
          onChange={(event) => setProvenance(event.target.value)}
          placeholder="Provenance — where did this fact come from? (stored with the resolution)"
          rows={2}
          className="rounded-[3px] border border-hairline bg-surface px-3 py-2 font-ui text-[13px] text-ink placeholder:text-ink-3"
        />
      </div>
      <PrimaryButton onClick={submit} disabled={isPending || (extra.length === 0 && !value.trim())}>
        {isPending ? "Supplying…" : "Supply context & re-evaluate"}
      </PrimaryButton>
      <MonoLabel className="tracking-[0.08em]!">
        THE ACTION IS REBUILT AND RE-EVALUATED FROM {String(detail.context?.schema_version ?? "1")} SCHEMA CONTEXT
      </MonoLabel>
    </div>
  );
}

export function ActionDrawer({ actionId, onClose }: { actionId: string; onClose: () => void }) {
  const { lastEvent } = useStream();
  const [detail, setDetail] = useState<ActionDetail | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [resolveState, setResolveState] = useState<{ pending: boolean; error: unknown | null }>({
    pending: false,
    error: null,
  });
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setLoadError(null);
    api
      .getAction(actionId)
      .then((value) => {
        if (!cancelled) setDetail(value);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error);
      });
    return () => {
      cancelled = true;
    };
  }, [actionId, reloadToken]);

  // The drawer owns local detail state, so refetch it explicitly after an SSE update.
  useEffect(() => {
    if (lastEvent?.action_id === actionId) setReloadToken((value) => value + 1);
  }, [actionId, lastEvent?.event_id]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const decision = detail?.policy_decision ?? null;
  const humanIsReview = detail ? isReviewResponse(detail.human_response) : false;
  const humanIsContext = detail ? isContextResponse(detail.human_response) : false;

  const awaitingReview = Boolean(
    decision?.final_action === "REQUIRE_APPROVAL" && !humanIsReview && !detail?.execution_result,
  );
  const awaitingContext = Boolean(
    decision?.final_action === "REQUEST_CONTEXT" && !humanIsContext && !detail?.execution_result,
  );

  const decidedAt = detail ? decisionEvent(detail)?.created_at : undefined;
  const executedAt = detail ? executionEvent(detail)?.created_at : undefined;

  const risk = useMemo(() => {
    const outcome = detail?.provider_outcome ?? null;
    return outcome && outcome.outcome === "success" ? (outcome as RiskAssessment) : null;
  }, [detail]);

  const failure = useMemo(() => {
    const outcome = detail?.provider_outcome ?? null;
    return outcome && outcome.outcome === "failure" ? (outcome as ProviderFailure) : null;
  }, [detail]);

  const resolve = async (resolution: "approve" | "reject") => {
    if (!detail || !decision) return;
    setResolveState({ pending: true, error: null });
    try {
      const updated = await api.resolveAction(actionId, {
        resolution,
        actor: DEMO_ACTOR,
        assessment_hash: decision.assessment_hash ?? undefined,
      });
      setDetail(updated);
      setResolveState({ pending: false, error: null });
    } catch (error) {
      setResolveState({ pending: false, error });
    }
  };

  const provideContext = async (updates: Record<string, unknown>, provenance: string) => {
    setResolveState({ pending: true, error: null });
    try {
      const updated = await api.resolveAction(actionId, {
        resolution: "provide_context",
        actor: DEMO_ACTOR,
        updates,
        provenance,
      });
      setDetail(updated);
      setResolveState({ pending: false, error: null });
    } catch (error) {
      setResolveState({ pending: false, error });
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label="Action detail">
      <button
        type="button"
        aria-label="Close action detail"
        onClick={onClose}
        className="absolute inset-0 bg-ink/30 backdrop-blur-[1px]"
      />
      <section className="relative flex h-full w-full max-w-[480px] flex-col overflow-y-auto border-l border-hairline bg-paper shadow-[0_0_60px_rgba(25,25,23,0.18)]">
        {loadError ? (
          <div className="p-6">
            <ErrorState error={loadError} onRetry={() => setReloadToken((n) => n + 1)} />
          </div>
        ) : !detail ? (
          <div className="flex flex-col gap-4 p-6">
            <div className="h-3 w-44 animate-pulse rounded-[2px] bg-ink/7" />
            <div className="h-6 w-64 animate-pulse rounded-[2px] bg-ink/7" />
            <div className="h-24 w-full animate-pulse rounded-[2px] bg-ink/7" />
            <div className="h-40 w-full animate-pulse rounded-[2px] bg-ink/7" />
          </div>
        ) : (
          <>
            <div className="flex h-15 shrink-0 items-center justify-between border-b border-hairline px-8">
              <MonoLabel className="tracking-[0.12em]!">EVALUATED ACTION · {detail.action_id}</MonoLabel>
              <button type="button" onClick={onClose} aria-label="Close" className="p-1 text-ink-2 hover:text-ink">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                  <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.4" />
                </svg>
              </button>
            </div>

            {/* Title block */}
            <div className="flex flex-col gap-3 border-b border-hairline px-8 pb-4.5 pt-5">
              <h2 className="font-ui text-[21px] font-bold leading-[26px] tracking-[-0.01em] text-ink">
                {detail.action.vendor_name ?? detail.action.counterparty_name ?? "Unnamed counterparty"}
              </h2>
              <div className="flex items-center justify-between gap-4">
                <span className="font-mono text-[17px] font-semibold leading-[22px] text-ink">
                  {formatAmount(detail.action.amount, detail.action.currency)}
                </span>
                <DecisionBadge action={detail.final_action} />
              </div>
              <MonoLabel className="tracking-[0.12em]!">
                {awaitingReview
                  ? `AWAITING HUMAN REVIEW · DECIDED ${formatUtcTime(decidedAt)} UTC`
                  : awaitingContext
                    ? `AWAITING CONTEXT · DECIDED ${formatUtcTime(decidedAt)} UTC`
                    : detail.execution_result
                      ? `SIMULATED EXECUTION RECORDED · ${formatUtcTime(executedAt)} UTC`
                      : detail.final_action === "BLOCK"
                        ? "TERMINAL — THIS ACTION CAN NEVER EXECUTE"
                        : `STATE ${detail.status.toUpperCase()}`}
              </MonoLabel>
            </div>

            {/* Original instruction */}
            <div className="flex flex-col gap-2.5 border-b border-hairline px-8 pb-4.5 pt-4">
              <SectionHeader>ORIGINAL INSTRUCTION</SectionHeader>
              <div className="border-l-2 border-ink bg-ink/3 py-3.5 pl-4 pr-4">
                <p className="font-mono text-[12.5px] leading-[19px] text-ink">“{detail.action.agent_goal}”</p>
              </div>
              <MonoLabel className="tracking-[0.08em]!">
                AGENT PROPOSAL · {detail.action.action_type.replaceAll("_", " ")} · PROPOSED{" "}
                {formatUtcTime(detail.action.timestamp)} UTC
              </MonoLabel>
              {detail.action.agent_reasoning_summary ? (
                <div className="flex flex-col gap-1.5 border border-hairline px-3.5 py-3">
                  <MonoLabel className="text-approval!">AGENT REASONING — UNTRUSTED INPUT, NEVER A FACT</MonoLabel>
                  <p className="font-ui text-[12.5px] leading-[18px] text-ink-2">
                    {detail.action.agent_reasoning_summary}
                  </p>
                </div>
              ) : null}
              {detail.action.destination ? (
                <div className="flex flex-col gap-1.5 border border-approval/18 bg-approval/5 px-3.5 py-3">
                  <MonoLabel className="text-approval!">SYNTHETIC DESTINATION OVERLAY — DISCLOSED MODIFICATION</MonoLabel>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[10px] leading-4 text-ink-2">
                      NEW · {detail.action.destination.new_destination}
                    </span>
                    {detail.action.destination.previous_destination ? (
                      <span className="font-mono text-[10px] leading-4 text-ink-3">
                        PRIOR · {detail.action.destination.previous_destination}
                      </span>
                    ) : null}
                    <span className="font-ui text-[11.5px] leading-4 text-ink-2">
                      {detail.action.destination.modification_reason}
                    </span>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Accounting evidence */}
            <div className="flex flex-col gap-2.5 border-b border-hairline px-8 pb-4.5 pt-4">
              <SectionHeader>ACCOUNTING EVIDENCE · TRUSTED FACTS</SectionHeader>
              {detail.context ? (
                <div className="flex flex-col">
                  {detail.context.candidate_matches.map((match) => (
                    <div
                      key={`${match.ledger_id}-${match.source_id}`}
                      className="flex items-baseline justify-between gap-4 border-b border-hairline/70 py-2.5 last:border-b-0"
                    >
                      <div className="flex min-w-0 flex-col gap-1">
                        <span className="font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
                          {match.record_type.toUpperCase()} · {match.source_id.toUpperCase()}
                        </span>
                        <span className="truncate font-ui text-[12.5px] leading-4 text-ink">
                          {formatAmount(match.amount, detail.action.currency)} · {match.date}
                          {match.status ? ` · ${match.status.replaceAll("_", " ")}` : ""}
                          {match.vendor ? ` · ${match.vendor}` : ""}
                        </span>
                        {match.match_reasons.length > 0 ? (
                          <span className="font-mono text-[9px] leading-3 text-ink-3">
                            {match.match_reasons.join(" · ").toUpperCase()}
                          </span>
                        ) : null}
                      </div>
                      <span className="shrink-0 font-mono text-[11px] font-semibold text-ink">
                        {match.match_score.toFixed(2)}
                      </span>
                    </div>
                  ))}
                  {detail.context.candidate_matches.length === 0 ? (
                    <MonoLabel className="tracking-[0.08em]!">NO CANDIDATE MATCHES IN THE LEDGER WINDOW</MonoLabel>
                  ) : null}
                  <div className="mt-2 flex flex-col gap-2 border-t border-hairline pt-3">
                    <LabeledRow label="VENDOR HISTORY" labelWidth="w-[130px]">
                      <MonoValue>
                        {detail.context.business_context.vendor_transaction_count} PRIOR TRANSACTIONS · TYPICAL{" "}
                        {formatAmount(detail.context.business_context.historical_amount_stats.median, detail.action.currency)}
                      </MonoValue>
                    </LabeledRow>
                    <LabeledRow label="PRECHECKS" labelWidth="w-[130px]">
                      <MonoValue>
                        {(detail.context.deterministic_features["missing_required_reference"] as boolean)
                          ? "REQUIRED REFERENCE MISSING"
                          : "NO HARD PRECHECK VIOLATIONS"}
                      </MonoValue>
                    </LabeledRow>
                  </div>
                </div>
              ) : (
                <MonoLabel className="tracking-[0.08em]!">CONTEXT SNAPSHOT NOT RECORDED FOR THIS ACTION</MonoLabel>
              )}
            </div>

            {/* Semantic signals */}
            <div className="flex flex-col gap-2.5 border-b border-hairline px-8 pb-4.5 pt-4">
              <SectionHeader
                right={
                  risk ? (
                    <span className="shrink-0 whitespace-nowrap font-mono text-[9.5px] leading-3 tracking-[0.08em] text-ink-3">
                      {risk.provider.toUpperCase()} · {formatLatency(risk.latency_ms).toUpperCase()}
                    </span>
                  ) : null
                }
              >
                SEMANTIC SIGNALS · PROVIDER JUDGMENT
              </SectionHeader>
              {failure ? <ProviderFailureNotice failure={failure} /> : null}
              {risk ? (
                <div className="flex flex-col gap-2">
                  {SIGNAL_LABELS.map((signal) => {
                    const probability = risk[signal.probability] as number;
                    const confidence = risk[signal.confidence] as number;
                    const isTop = probability === Math.max(...SIGNAL_LABELS.map((s) => risk[s.probability] as number));
                    return (
                      <SignalRow
                        key={signal.label}
                        label={signal.label}
                        question={signal.question}
                        probability={probability}
                        confidence={confidence}
                        highlight={isTop && probability >= 0.5}
                      />
                    );
                  })}
                </div>
              ) : null}
              {!risk && !failure ? (
                <MonoLabel className="tracking-[0.08em]!">PROVIDER DID NOT RETURN A RISK ASSESSMENT</MonoLabel>
              ) : null}
            </div>

            {/* Policy decision */}
            <div className="flex flex-col gap-2.5 border-b border-hairline px-8 pb-4.5 pt-4">
              <SectionHeader
                right={<MonoLabel className="tracking-[0.08em]!">CONFIG V{decision?.config_version ?? "—"}</MonoLabel>}
              >
                POLICY DECISION · DETERMINISTIC
              </SectionHeader>
              {decision ? (
                <div className="flex flex-col gap-2.25">
                  <LabeledRow label="RULE HIT" labelWidth="w-[110px]">
                    <span className="font-ui text-[12.5px] font-medium leading-4 text-ink">
                      {decision.reason_codes.map(reasonCodeLabel).join(" · ") || "—"}
                    </span>
                  </LabeledRow>
                  {decision.triggered_thresholds.map((threshold) => (
                    <LabeledRow key={threshold.name} label="THRESHOLD" labelWidth="w-[110px]">
                      <MonoValue>
                        {threshold.name.toUpperCase()} {threshold.comparator} {String(threshold.threshold)} · ACTUAL{" "}
                        {String(threshold.actual)}
                      </MonoValue>
                    </LabeledRow>
                  ))}
                  <LabeledRow label="EVALUATED" labelWidth="w-[110px]">
                    <MonoValue>
                      {decision.evaluated_rules.length} RULES · {detail.context?.candidate_matches.length ?? 0} CANDIDATE
                      FACTS · {risk ? "1 SEMANTIC ASSESSMENT" : failure ? "PROVIDER FAILURE" : "NO PROVIDER INPUT"}
                    </MonoValue>
                  </LabeledRow>
                  <LabeledRow label="SNAPSHOT" labelWidth="w-[110px]">
                    <MonoValue>ASSESSMENT {shortId(decision.assessment_hash, 14)}</MonoValue>
                  </LabeledRow>
                  <div className="flex items-baseline gap-3 border-t border-hairline/62 pt-2.5">
                    <span className="w-[110px] shrink-0 font-mono text-[10px] leading-3 tracking-[0.06em] text-ink-3">
                      EXECUTION
                    </span>
                    <span className="flex items-center gap-1.75">
                      <span
                        className={`size-1.25 shrink-0 ${
                          detail.execution_result ? "rounded-full bg-allow" : "rounded-full border border-ink-3"
                        }`}
                        aria-hidden
                      />
                      <span className="font-mono text-[10px] font-medium leading-3 tracking-[0.06em] text-ink-2">
                        {detail.execution_result
                          ? `SIMULATED EXECUTION ${detail.execution_result.execution_id.toUpperCase()}`
                          : "HELD — NOT EXECUTED"}
                      </span>
                    </span>
                  </div>
                </div>
              ) : (
                <MonoLabel className="tracking-[0.08em]!">NO POLICY DECISION RECORDED YET</MonoLabel>
              )}
            </div>

            {/* Audit trail */}
            <div className="flex flex-col gap-2.5 border-b border-hairline px-8 pb-4.5 pt-4">
              <SectionHeader right={<MonoLabel className="tracking-[0.08em]!">{detail.audit_events.length} EVENTS</MonoLabel>}>
                AUDIT TRAIL · APPEND-ONLY
              </SectionHeader>
              <div className="flex flex-col">
                {detail.audit_events.map((event) => (
                  <div
                    key={event.event_id}
                    className="flex items-baseline gap-3 border-b border-hairline/70 py-2 last:border-b-0"
                  >
                    <span className="w-9 shrink-0 font-mono text-[9px] leading-3 text-ink-3">#{event.event_id}</span>
                    <span className="shrink-0 font-mono text-[10px] leading-3 text-ink-3">
                      {formatUtcTime(event.created_at)}
                    </span>
                    <span
                      className={`font-mono text-[10px] font-medium leading-3 tracking-[0.02em] ${
                        EVENT_TONE[event.type] ?? "text-ink-2"
                      }`}
                    >
                      {event.type}
                    </span>
                    <span className="grow basis-[0%] truncate text-right font-mono text-[9px] leading-3 text-ink-3">
                      {summarizeEventPayload(event)}
                    </span>
                  </div>
                ))}
              </div>
              {isContextResponse(detail.human_response) ? (
                <MonoLabel className="tracking-[0.08em]!">
                  CONTEXT SUPPLIED BY {detail.human_response.supplied_by.toUpperCase()} ·{" "}
                  {detail.human_response.provenance.slice(0, 80)}
                </MonoLabel>
              ) : null}
              {isReviewResponse(detail.human_response) ? (
                <MonoLabel className="tracking-[0.08em]!">
                  {detail.human_response.approved ? "APPROVED" : "REJECTED"} BY{" "}
                  {detail.human_response.reviewer.toUpperCase()}
                </MonoLabel>
              ) : null}
              {detail.execution_authorization ? (
                <MonoLabel className="tracking-[0.08em]!">
                  AUTHORIZATION · {detail.execution_authorization.authorization_type.replaceAll("_", " ")} ·{" "}
                  {detail.execution_authorization.actor ? detail.execution_authorization.actor.toUpperCase() : "AUTOMATIC"}
                </MonoLabel>
              ) : null}
            </div>

            {/* Resolve actions */}
            <div className="mt-auto flex flex-col gap-3 border-t border-hairline px-8 pb-5 pt-4">
              {resolveState.error ? (
                <ErrorState error={resolveState.error} onRetry={() => setResolveState({ pending: false, error: null })} />
              ) : null}
              {awaitingReview ? (
                <>
                  <div className="flex items-center gap-3">
                    <PrimaryButton onClick={() => resolve("approve")} disabled={resolveState.pending} className="grow!">
                      {resolveState.pending ? "Submitting…" : "Approve & execute"}
                    </PrimaryButton>
                    <GhostButton onClick={() => resolve("reject")} disabled={resolveState.pending} className="grow!">
                      Reject
                    </GhostButton>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <MonoLabel>ADD CONTEXT — REQUEST_CONTEXT ACTIONS ONLY</MonoLabel>
                    <MonoLabel className="tracking-[0.08em]!">SIGNED AS {DEMO_ACTOR.toUpperCase()}</MonoLabel>
                  </div>
                </>
              ) : awaitingContext ? (
                <ContextForm detail={detail} onSubmit={provideContext} isPending={resolveState.pending} />
              ) : (
                <div className="flex items-center justify-between gap-3">
                  <MonoLabel className="tracking-[0.08em]!">
                    {detail.execution_result
                      ? "SIMULATED EXECUTION COMPLETE — NO REAL PAYMENT RAIL"
                      : detail.final_action === "BLOCK"
                        ? "TERMINAL DECISION — NO CONTROLS"
                        : "NO HUMAN ACTION REQUIRED"}
                  </MonoLabel>
                  <span className="flex items-center gap-1.75">
                    <span
                      className={`size-1.25 shrink-0 ${
                        detail.execution_result ? "rounded-full bg-allow" : "rounded-full border border-ink-3"
                      }`}
                      aria-hidden
                    />
                    <MonoLabel className="tracking-[0.08em]!">
                      {detail.execution_result ? "EXECUTED" : "NOT EXECUTED"}
                    </MonoLabel>
                  </span>
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
