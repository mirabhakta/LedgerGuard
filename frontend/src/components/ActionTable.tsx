import type { ActionListItem } from "../api/types";
import { executionLabel, reasonCodeLabel } from "../lib/decisions";
import { formatAmount, formatAge, formatLatency } from "../lib/format";
import { DecisionBadge } from "./DecisionBadge";

export type TableMode = "ledger" | "queue";

function ExecutionCell({ item }: { item: ActionListItem }) {
  const state = executionLabel(item);
  const marker =
    state.tone === "executed" ? (
      <span className="size-1.25 shrink-0 rounded-full bg-ink-2" aria-hidden />
    ) : state.tone === "held" ? (
      <span className="size-1.25 shrink-0 rounded-full border border-ink-3" aria-hidden />
    ) : (
      <span className="size-1.25 shrink-0 border border-ink-3" aria-hidden />
    );

  return (
    <span className="flex items-center gap-1.75">
      {marker}
      <span
        className={`font-mono text-[10px] font-medium leading-3 tracking-[0.06em] ${
          state.tone === "executed" ? "text-ink-2" : "text-ink-3"
        }`}
      >
        {state.label}
      </span>
    </span>
  );
}

function reasonSummary(item: ActionListItem): string {
  if (item.reason_codes.length === 0) return item.final_action ? "—" : "Awaiting evaluation";
  const first = reasonCodeLabel(item.reason_codes[0]);
  return item.reason_codes.length > 1 ? `${first} · +${item.reason_codes.length - 1} more` : first;
}

interface ActionTableProps {
  items: ActionListItem[];
  mode: TableMode;
  onOpen: (actionId: string) => void;
  now?: number;
}

export function ActionTable({ items, mode, onOpen, now }: ActionTableProps) {
  return (
    <>
      {/* Desktop table */}
      <div className="hidden lg:block">
        <div className="flex h-9 items-center gap-6 border-y border-hairline px-12">
          <span className="w-[170px] shrink-0 font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            DECISION
          </span>
          <span className="w-[220px] shrink-0 font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            VENDOR · ACTION ID
          </span>
          <span className="w-[130px] shrink-0 text-right font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            AMOUNT
          </span>
          <span className="grow basis-[0%] font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            REASON · POLICY BASIS
          </span>
          <span className="w-[130px] shrink-0 font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            {mode === "ledger" ? "EXECUTION" : "AWAITING"}
          </span>
          <span className="w-20 shrink-0 text-right font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3">
            {mode === "ledger" ? "LATENCY" : ""}
          </span>
        </div>
        {items.map((item) => (
          <button
            key={item.action_id}
            type="button"
            onClick={() => onOpen(item.action_id)}
            className="flex h-18 w-full items-center gap-6 border-b border-hairline px-12 text-left transition-colors hover:bg-ink/3"
          >
            <span className="w-[170px] shrink-0">
              <DecisionBadge action={item.final_action} />
            </span>
            <span className="flex w-[220px] shrink-0 flex-col gap-0.75">
              <span className="truncate font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">
                {item.action_id}
              </span>
              <span className="truncate font-ui text-[14px] font-medium leading-[18px] text-ink">
                {item.action.vendor_name ?? item.action.counterparty_name ?? "Unnamed counterparty"}
              </span>
            </span>
            <span className="w-[130px] shrink-0 text-right font-mono text-[14px] font-semibold leading-[18px] text-ink">
              {formatAmount(item.action.amount, item.action.currency)}
            </span>
            <span className="grow basis-[0%] truncate font-ui text-[13px] leading-[18px] text-ink-2">
              {reasonSummary(item)}
            </span>
            <span className="w-[130px] shrink-0">
              {mode === "ledger" ? (
                <ExecutionCell item={item} />
              ) : (
                <span className="font-mono text-[11px] leading-3.5 text-ink-3">{formatAge(item.created_at, now)}</span>
              )}
            </span>
            <span className="w-20 shrink-0 text-right font-mono text-[11px] leading-3.5 text-ink-3">
              {mode === "ledger" ? formatLatency(item.latency_ms) : "→"}
            </span>
          </button>
        ))}
      </div>

      {/* Mobile cards */}
      <div className="flex flex-col lg:hidden">
        {items.map((item) => (
          <button
            key={item.action_id}
            type="button"
            onClick={() => onOpen(item.action_id)}
            className="flex flex-col gap-3 border-b border-hairline px-6 py-4 text-left transition-colors hover:bg-ink/3"
          >
            <div className="flex items-center justify-between gap-3">
              <DecisionBadge action={item.final_action} />
              <span className="font-mono text-[12px] font-semibold text-ink">
                {formatAmount(item.action.amount, item.action.currency)}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="truncate font-mono text-[9px] leading-3 tracking-[0.1em] text-ink-3">
                {item.action_id}
              </span>
              <span className="truncate font-ui text-[14px] font-medium leading-[18px] text-ink">
                {item.action.vendor_name ?? item.action.counterparty_name ?? "Unnamed counterparty"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="truncate font-ui text-[12.5px] leading-[18px] text-ink-2">{reasonSummary(item)}</span>
              <span className="shrink-0">
                {mode === "ledger" ? (
                  <ExecutionCell item={item} />
                ) : (
                  <span className="font-mono text-[11px] text-ink-3">{formatAge(item.created_at, now)}</span>
                )}
              </span>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
