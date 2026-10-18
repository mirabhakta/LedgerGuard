import type { FinalAction, RiskAssessment } from "../api/types";
import { formatAmount } from "./format";

export interface DecisionMeta {
  label: string;
  /** Tailwind color token name from the Paper design system. */
  token: "allow" | "approval" | "context" | "block";
  blurb: string;
}

export const DECISION_META: Record<FinalAction, DecisionMeta> = {
  ALLOW: {
    label: "ALLOW",
    token: "allow",
    blurb: "Policy authorized this action. Execution is simulated only.",
  },
  REQUIRE_APPROVAL: {
    label: "REQUIRE APPROVAL",
    token: "approval",
    blurb: "A human must review the exact evidence before anything executes.",
  },
  REQUEST_CONTEXT: {
    label: "REQUEST CONTEXT",
    token: "context",
    blurb: "A required fact is missing. Supply it and the action is re-evaluated.",
  },
  BLOCK: {
    label: "BLOCK",
    token: "block",
    blurb: "Terminal. This action can never execute.",
  },
};

const REFUSED_STATUSES = new Set(["blocked", "review_rejected", "error"]);

/** Execution column semantics derived from the persisted state — never invented. */
export function executionLabel(item: {
  final_action: FinalAction | null;
  status: string;
  execution_result?: unknown;
}): {
  label: string;
  tone: "executed" | "held" | "not_executed" | "pending";
} {
  if (item.execution_result) return { label: "EXECUTED", tone: "executed" };
  if (item.final_action === "BLOCK" || REFUSED_STATUSES.has(item.status)) {
    return { label: "NOT EXECUTED", tone: "not_executed" };
  }
  if (item.final_action === "REQUIRE_APPROVAL" || item.final_action === "REQUEST_CONTEXT") {
    return { label: "HELD", tone: "held" };
  }
  if (item.final_action === "ALLOW") return { label: "ALLOWED", tone: "executed" };
  return { label: "PENDING", tone: "pending" };
}

/** Reason codes are machine-readable; this is a display dictionary with a safe fallback. */
const REASON_LABELS: Record<string, string> = {
  HARD_LIMIT_EXCEEDED: "Amount exceeds the hard policy limit",
  UNSUPPORTED_CURRENCY: "Currency outside the supported set",
  UNSUPPORTED_ACTION_TYPE: "Action type is not supported",
  CROSS_COMPANY_CONTEXT: "Reference crosses company boundaries",
  UNKNOWN_ACCOUNT: "Account is not in the company chart",
  EXACT_PAID_DOCUMENT_DUPLICATE: "Document is already marked paid in the ledger",
  MISSING_REQUIRED_REFERENCE: "A required reference is missing",
  DUPLICATE_RISK: "Semantic duplicate obligation risk",
  GOAL_MISMATCH: "Action conflicts with the agent goal",
  COUNTERPARTY_CHANGE_RISK: "Payment destination change risk",
  MISSING_CONTEXT: "Required context is missing",
  ACTION_ANOMALY: "Action is unusual for this vendor",
  LOW_CONFIDENCE: "Signal confidence below the review threshold",
  POLICY_ALLOW: "All policy checks passed",
  PROVIDER_TIMEOUT: "Provider timed out — routed fail-safe",
  PROVIDER_UNAVAILABLE: "Provider unavailable — routed fail-safe",
  PROVIDER_INVALID_RESPONSE: "Provider returned an invalid response — routed fail-safe",
};

export function reasonCodeLabel(code: string): string {
  return REASON_LABELS[code] ?? code.replace(/_/g, " ").toLowerCase();
}

/** Fields the backend accepts for provide_context (workflow CONTEXT_UPDATE_FIELDS). */
export const CONTEXT_UPDATE_FIELDS = [
  "vendor_id",
  "vendor_name",
  "counterparty_id",
  "counterparty_name",
  "source_document_id",
  "proposed_category",
  "user_constraints",
  "agent_reasoning_summary",
] as const;

export type ContextUpdateField = (typeof CONTEXT_UPDATE_FIELDS)[number];

/** The five risk signals exposed by every DecisionProvider. */
export const SIGNAL_LABELS: Array<{
  probability: keyof RiskAssessment;
  confidence: keyof RiskAssessment;
  label: string;
  question: string;
}> = [
  {
    probability: "duplicate_obligation_probability",
    confidence: "duplicate_obligation_confidence",
    label: "Duplicate obligation",
    question: "Does this obligation already exist under another document?",
  },
  {
    probability: "goal_alignment_probability",
    confidence: "goal_alignment_confidence",
    label: "Goal alignment",
    question: "Does the action serve the stated agent goal?",
  },
  {
    probability: "counterparty_change_score",
    confidence: "counterparty_change_confidence",
    label: "Counterparty change",
    question: "Does the destination resemble prior verified beneficiaries?",
  },
  {
    probability: "missing_context_probability",
    confidence: "missing_context_confidence",
    label: "Missing context",
    question: "Is a required fact absent from the snapshot?",
  },
  {
    probability: "action_anomaly_score",
    confidence: "action_anomaly_confidence",
    label: "Action anomaly",
    question: "Is this action unusual against the vendor's history?",
  },
];

export function actionSummary(item: {
  action: { vendor_name?: string | null; counterparty_name?: string | null; amount: string | number; currency: string; action_type: string };
}): { title: string; amount: string; actionType: string } {
  const { vendor_name, counterparty_name, amount, currency, action_type } = item.action;
  return {
    title: vendor_name ?? counterparty_name ?? "Unnamed counterparty",
    amount: formatAmount(amount, currency),
    actionType: action_type,
  };
}

export const PROVIDER_LABELS: Record<string, string> = {
  rules: "Rules baseline",
  gemini: "Gemini baseline",
  system_one: "System One (Jev)",
  "timeout-test": "Timeout test provider",
};
