/**
 * Typed fetch client for the LedgerGuard API (contract version 1.0.0).
 * Every endpoint here exists in backend/app/api/routes.py — nothing is invented.
 */
import type {
  ActionDetail,
  ActionListResponse,
  BenchmarksResponse,
  DashboardResponse,
  DemoRunRequest,
  ErrorResponse,
  HealthResponse,
  ResolveRequest,
} from "./types";

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly auditId: string | null;

  constructor(status: number, code: string, message: string, retryable: boolean, auditId: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.auditId = auditId;
  }
}

function toApiError(status: number, body: ErrorResponse | null): ApiError {
  if (body && typeof body.code === "string") {
    return new ApiError(status, body.code, body.message || body.code, Boolean(body.retryable), body.audit_id ?? null);
  }
  return new ApiError(status, `HTTP_${status}`, `Request failed with status ${status}`, status >= 500, null);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "The LedgerGuard API is unreachable. Start the backend and retry.",
      true,
      null,
    );
  }
  if (!response.ok) {
    let body: ErrorResponse | null = null;
    try {
      body = (await response.json()) as ErrorResponse;
    } catch {
      body = null;
    }
    throw toApiError(response.status, body);
  }
  return (await response.json()) as T;
}

function queryString(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export interface ActionListParams {
  final_action?: string;
  reason_code?: string;
  provider?: string;
  scenario?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  dashboard: () => request<DashboardResponse>("/api/dashboard"),

  listActions: (params: ActionListParams = {}) =>
    request<ActionListResponse>(
      `/api/actions${queryString({
        final_action: params.final_action,
        reason_code: params.reason_code,
        provider: params.provider,
        scenario: params.scenario,
        limit: params.limit,
        offset: params.offset,
      })}`,
    ),

  getAction: (actionId: string) => request<ActionDetail>(`/api/actions/${encodeURIComponent(actionId)}`),

  resolveAction: (actionId: string, body: ResolveRequest) =>
    request<ActionDetail>(`/api/actions/${encodeURIComponent(actionId)}/resolve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  runDemo: (body: DemoRunRequest) =>
    request<ActionDetail>("/api/demo/run", { method: "POST", body: JSON.stringify(body) }),

  benchmarks: () => request<BenchmarksResponse>("/api/benchmarks"),
};

export { API_BASE };
