/**
 * Types for the LedgerGuard FastAPI contract (API 1.0.0, event schema 1).
 * Mirrors `backend/app/api/models.py` and the domain models exactly.
 * Source of truth: docs/API_HANDOFF.md and the FastAPI OpenAPI schema.
 */

export type FinalAction = "ALLOW" | "REQUIRE_APPROVAL" | "REQUEST_CONTEXT" | "BLOCK";

export type Resolution = "approve" | "reject" | "provide_context";

/** Decimal values may arrive as JSON strings (Pydantic v2) or numbers. */
export type DecimalValue = string | number;

export type ActionType =
  | "PAY_VENDOR_BILL"
  | "POST_TRANSACTION"
  | "MATCH_EXISTING"
  | "ADD_TRANSACTION";

export interface SyntheticDestinationMetadata {
  previous_destination: string | null;
  new_destination: string;
  changed_at: string | null;
  is_synthetic: boolean;
  modification_reason: string;
  source_record_ids: string[];
}

export interface ProposedAction {
  action_id: string;
  action_type: ActionType;
  company_id: string;
  timestamp: string;
  amount: DecimalValue;
  currency: string;
  vendor_id?: string | null;
  vendor_name?: string | null;
  counterparty_id?: string | null;
  counterparty_name?: string | null;
  account_id?: string | null;
  source_document_id?: string | null;
  proposed_category?: string | null;
  agent_goal: string;
  agent_reasoning_summary?: string | null;
  destination?: SyntheticDestinationMetadata | null;
  user_constraints?: string[];
}

export interface CandidateMatch {
  ledger_id: string;
  source_id: string;
  record_type: string;
  date: string;
  amount: DecimalValue | null;
  vendor: string | null;
  category: string | null;
  description: string | null;
  status: string | null;
  match_score: number;
  match_reasons: string[];
}

export interface HistoricalAmountStats {
  observation_count: number;
  mean: DecimalValue | null;
  median: DecimalValue | null;
  stddev: DecimalValue | null;
  minimum: DecimalValue | null;
  maximum: DecimalValue | null;
}

export interface BusinessContext {
  company_id: string;
  business_type: string | null;
  industry_naics: string | null;
  current_account_id: string | null;
  vendor_transaction_count: number;
  historical_amount_stats: HistoricalAmountStats;
  category_history: string[];
  account_history: string[];
  previous_payment_destinations: string[] | null;
  known_accounting_patterns: string[];
  user_constraints: string[];
}

export interface ContextSummary {
  candidate_matches: CandidateMatch[];
  business_context: BusinessContext;
  deterministic_features: Record<string, unknown>;
  schema_version: string;
  feature_version: string;
}

export interface RiskAssessment {
  outcome: "success";
  provider: string;
  model_name: string;
  latency_ms: number;
  schema_version: string;
  goal_alignment_probability: number;
  goal_alignment_confidence: number;
  duplicate_obligation_probability: number;
  duplicate_obligation_confidence: number;
  counterparty_change_score: number;
  counterparty_change_confidence: number;
  missing_context_probability: number;
  missing_context_confidence: number;
  action_anomaly_score: number;
  action_anomaly_confidence: number;
}

export interface ProviderFailure {
  outcome: "failure";
  provider: string;
  code: string;
  retryable: boolean;
  latency_ms: number;
  model_name: string | null;
  message?: string;
}

export type ProviderOutcome = RiskAssessment | ProviderFailure;

export interface TriggeredThreshold {
  name: string;
  comparator: string;
  threshold: DecimalValue;
  actual: DecimalValue;
}

export interface PolicyDecision {
  final_action: FinalAction;
  reason_codes: string[];
  triggered_thresholds: TriggeredThreshold[];
  provider: string;
  audit_id: string;
  action_id: string;
  config_version: string;
  config_hash: string;
  assessment_hash: string | null;
  evaluated_rules: string[];
}

export interface HumanReviewResponse {
  approved: boolean;
  action_id: string;
  assessment_hash: string | null;
  reviewer: string;
  note?: string | null;
}

export interface ContextResponse {
  action_id: string;
  updates: Record<string, unknown>;
  supplied_by: string;
  provenance: string;
}

export interface ExecutionResult {
  execution_id: string;
  action_id: string;
  audit_id: string;
  status: string;
  executed_at: string;
  idempotent_replay: boolean;
}

export interface ExecutionAuthorization {
  action_id: string;
  audit_id: string;
  authorization_type: "POLICY_ALLOW" | "HUMAN_APPROVAL";
  assessment_hash: string | null;
  actor: string | null;
  created_at: string;
  decision: PolicyDecision;
  review: HumanReviewResponse | null;
}

export interface AuditEvent {
  event_id: number;
  action_id: string;
  audit_id: string;
  type: string;
  created_at: string;
  schema_version: string;
  payload: Record<string, unknown>;
}

export interface ActionListItem {
  action_id: string;
  idempotency_key: string | null;
  audit_id: string;
  scenario_id: string | null;
  provider: string;
  created_at: string;
  updated_at: string;
  status: string;
  final_action: FinalAction | null;
  latency_ms: number | null;
  action: ProposedAction;
  reason_codes: string[];
}

export interface ActionDetail extends ActionListItem {
  context: ContextSummary | null;
  provider_outcome: ProviderOutcome | null;
  policy_decision: PolicyDecision | null;
  human_response: HumanReviewResponse | ContextResponse | null;
  execution_result: ExecutionResult | null;
  execution_authorization: ExecutionAuthorization | null;
  error_state: { code: string; message?: string } | null;
  audit_events: AuditEvent[];
}

export interface ActionListResponse {
  items: ActionListItem[];
  limit: number;
  offset: number;
  count: number;
  total: number;
}

export interface DashboardResponse {
  processed: number;
  counts: Record<string, number>;
  median_provider_latency_ms: number | null;
}

export interface BenchmarkRun {
  run_id: string | null;
  created_at: string | null;
  provider: string | null;
  model_name: string | null;
  sample_size: number | null;
  metrics: Record<string, DecimalValue | null> | null;
  measured_cost_usd: number | null;
  dataset_name?: string | null;
  artifact_path?: string | null;
  methodology_note?: string | null;
}

export interface BenchmarksResponse {
  status: "measured" | "not_run";
  runs: BenchmarkRun[];
}

export interface HealthResponse {
  status: "ok";
  providers: string[];
  scenario_count: number;
}

export interface ErrorResponse {
  code: string;
  message: string;
  retryable: boolean;
  audit_id: string | null;
}

export interface DemoRunRequest {
  scenario_id: string;
  provider: string;
  idempotency_key?: string;
}

export interface ResolveRequest {
  resolution: Resolution;
  actor: string;
  assessment_hash?: string;
  updates?: Record<string, unknown>;
  provenance?: string;
}

export interface LedgerEvent {
  event_id: number;
  action_id: string;
  audit_id: string;
  type: string;
  timestamp: string;
  schema_version: string;
  payload: Record<string, unknown>;
}

export const EVENT_TYPES = [
  "action_received",
  "precheck_complete",
  "provider_started",
  "risk_assessment_ready",
  "policy_decision",
  "execution_simulated",
  "review_required",
  "review_resolved",
  "context_requested",
  "context_supplied",
  "action_blocked",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];
