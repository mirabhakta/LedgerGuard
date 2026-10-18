import { ApiError } from "../api/client";
import { useStream } from "../api/stream";
import type { ProviderFailure } from "../api/types";
import { GhostButton, MonoLabel } from "./ui";

/** Thin banner shown while the SSE stream is reconnecting (never blocks the UI). */
export function StreamBanner() {
  const stream = useStream();
  if (stream.status !== "reconnecting") return null;
  return (
    <div className="flex shrink-0 items-center justify-between gap-4 border-b border-approval/25 bg-approval/6 px-6 py-2.5 md:px-12">
      <div className="flex min-w-0 items-center gap-3">
        <span className="size-1.5 shrink-0 rounded-full bg-approval" aria-hidden />
        <span className="truncate font-mono text-[10px] leading-3 tracking-[0.08em] text-approval">
          LIVE UPDATES PAUSED — PERSISTED RESULTS STAY ACCURATE; REFETCHED ON RECONNECT
        </span>
      </div>
      <button
        type="button"
        onClick={stream.reconnect}
        className="shrink-0 font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-approval underline decoration-approval/40 underline-offset-2"
      >
        RECONNECT
      </button>
    </div>
  );
}

const ERROR_COPY: Record<string, { title: string; caption: string }> = {
  NETWORK_ERROR: {
    title: "The LedgerGuard API is unreachable.",
    caption: "Start the backend (uvicorn backend.app.main:app) and retry.",
  },
  ACTION_NOT_FOUND: {
    title: "This action is not in the audit ledger.",
    caption: "It may have been produced by a different database. Refetch the list and pick again.",
  },
  STALE_REVIEW_RESPONSE: {
    title: "The risk snapshot changed since this view loaded.",
    caption: "The approval was rejected to protect against stale human decisions. Reopen the action and review the current evidence.",
  },
  INVALID_STATE_TRANSITION: {
    title: "This action already reached a terminal state.",
    caption: "It was resolved or blocked elsewhere. The ledger below shows the current truth.",
  },
  IDEMPOTENCY_KEY_CONFLICT: {
    title: "That idempotency key belongs to a different run.",
    caption: "Each run needs a fresh key; the original action is untouched.",
  },
  SCENARIO_NOT_FOUND: {
    title: "Unknown scenario id.",
    caption: "Only the six documented scenarios can run.",
  },
  PROVIDER_NOT_FOUND: {
    title: "Unknown provider.",
    caption: "Registered providers are rules, gemini, and system_one.",
  },
  VALIDATION_ERROR: {
    title: "The request was rejected by the API contract.",
    caption: "Check the fields and try again.",
  },
  WORKFLOW_ERROR: {
    title: "The workflow failed safely.",
    caption: "No execution was authorized. Inspect the audit trail for details.",
  },
};

export function errorCopy(error: unknown): { title: string; caption: string; code: string; retryable: boolean } {
  if (error instanceof ApiError) {
    const known = ERROR_COPY[error.code];
    return {
      title: known?.title ?? error.message,
      caption: known?.caption ?? "The API refused the request; the stable code above is the contract.",
      code: error.code,
      retryable: error.retryable,
    };
  }
  return {
    title: "Something went wrong.",
    caption: error instanceof Error ? error.message : "Unknown error",
    code: "UNEXPECTED_ERROR",
    retryable: true,
  };
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { title, caption, code, retryable } = errorCopy(error);
  return (
    <div className="flex flex-col items-start gap-3 border border-block/25 bg-block/4 px-5 py-5">
      <MonoLabel className="text-block!">{code}</MonoLabel>
      <p className="max-w-[560px] font-ui text-[14px] font-semibold leading-[20px] text-ink">{title}</p>
      <p className="max-w-[560px] font-ui text-[12.5px] leading-[18px] text-ink-2">{caption}</p>
      {retryable && onRetry ? <GhostButton onClick={onRetry}>Retry</GhostButton> : null}
    </div>
  );
}

export function EmptyState({
  label,
  title,
  caption,
  action,
}: {
  label: string;
  title: string;
  caption: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2.5 border border-hairline px-6 py-16 text-center">
      <MonoLabel>{label}</MonoLabel>
      <p className="font-ui text-[16px] font-semibold leading-[22px] tracking-[-0.005em] text-ink">{title}</p>
      <p className="max-w-[460px] font-ui text-[12.5px] leading-[18px] text-ink-2">{caption}</p>
      {action}
    </div>
  );
}

export function LoadingTable({ rows = 5 }: { rows?: number }) {
  return (
    <div aria-busy="true" className="flex flex-col">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex h-18 items-center gap-6 border-b border-hairline px-6 md:px-12">
          <div className="h-3 w-[120px] shrink-0 animate-pulse rounded-[2px] bg-ink/7" />
          <div className="h-3 w-[180px] shrink-0 animate-pulse rounded-[2px] bg-ink/7" />
          <div className="h-3 grow basis-[0%] animate-pulse rounded-[2px] bg-ink/7" />
          <div className="h-3 w-[64px] shrink-0 animate-pulse rounded-[2px] bg-ink/7" />
        </div>
      ))}
    </div>
  );
}

/** Sanitized provider failure: provider, code, retryability, latency, model — never raw messages. */
export function ProviderFailureNotice({ failure }: { failure: ProviderFailure }) {
  return (
    <div className="flex flex-col gap-3 border border-block/25 bg-block/4 px-4 py-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="inline-flex items-center gap-2 rounded-[3px] border border-block/30 bg-block/8 px-2.5 py-1.25">
          <span className="size-1.5 rounded-full bg-block" aria-hidden />
          <span className="font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-block">
            {failure.code}
          </span>
        </span>
        <MonoLabel>{failure.provider.toUpperCase()}</MonoLabel>
        <MonoLabel>{failure.retryable ? "RETRYABLE" : "NOT RETRYABLE"}</MonoLabel>
        <MonoLabel>{failure.latency_ms.toFixed(1)} MS</MonoLabel>
        {failure.model_name ? <MonoLabel>{failure.model_name}</MonoLabel> : null}
      </div>
      <p className="font-ui text-[12.5px] leading-[18px] text-ink-2">
        The provider did not return a usable risk assessment. The policy engine routed this action fail-safe —
        a provider failure can never become an automatic allow.
      </p>
    </div>
  );
}
