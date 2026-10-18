import type { FinalAction } from "../api/types";
import { DECISION_META } from "../lib/decisions";

const TONE_CLASSES: Record<string, string> = {
  allow: "bg-allow/8 border-allow/30 text-allow",
  approval: "bg-approval/8 border-approval/30 text-approval",
  context: "bg-context/8 border-context/30 text-context",
  block: "bg-block/8 border-block/30 text-block",
};

const DOT_CLASSES: Record<string, string> = {
  allow: "bg-allow",
  approval: "bg-approval",
  context: "bg-context",
  block: "bg-block",
};

interface DecisionBadgeProps {
  action: FinalAction | null;
  /** Optional override label for non-final states. */
  label?: string;
  tone?: "allow" | "approval" | "context" | "block";
  className?: string;
}

export function DecisionBadge({ action, label, tone, className = "" }: DecisionBadgeProps) {
  if (!action && !label) {
    return (
      <span
        className={`inline-flex w-fit items-center gap-2 rounded-[3px] border border-hairline bg-ink/3 px-2.5 py-1.25 ${className}`}
      >
        <span className="size-1.5 shrink-0 rounded-full border border-ink-3" aria-hidden />
        <span className="font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-ink-3">
          PENDING
        </span>
      </span>
    );
  }

  const meta = action ? DECISION_META[action] : null;
  const resolvedTone = tone ?? meta?.token ?? "allow";
  const text = label ?? meta?.label ?? "PENDING";

  return (
    <span
      className={`inline-flex w-fit items-center gap-2 rounded-[3px] border px-2.5 py-1.25 ${TONE_CLASSES[resolvedTone]} ${className}`}
    >
      <span className={`size-1.5 shrink-0 rounded-full ${DOT_CLASSES[resolvedTone]}`} aria-hidden />
      <span className="font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] whitespace-nowrap">
        {text}
      </span>
    </span>
  );
}
