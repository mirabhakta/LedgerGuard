import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useActions, useDashboard } from "../api/queries";
import type { ActionListItem, FinalAction } from "../api/types";
import { ActionDrawer } from "../components/ActionDrawer";
import { ActionTable } from "../components/ActionTable";
import { PageFooter, PageHeader } from "../components/PageChrome";
import { EmptyState, ErrorState, LoadingTable } from "../components/StatePanels";
import { MonoLabel, PrimaryButton } from "../components/ui";
import { formatCount, formatLatency } from "../lib/format";

const SEVERITY_RANK: Record<FinalAction, number> = {
  BLOCK: 0,
  REQUIRE_APPROVAL: 1,
  REQUEST_CONTEXT: 2,
  ALLOW: 3,
};

function sortBySeverity(items: ActionListItem[]): ActionListItem[] {
  return [...items].sort((a, b) => {
    const rankA = a.final_action ? SEVERITY_RANK[a.final_action] : 4;
    const rankB = b.final_action ? SEVERITY_RANK[b.final_action] : 4;
    if (rankA !== rankB) return rankA - rankB;
    return b.created_at.localeCompare(a.created_at);
  });
}

function Stat({
  label,
  value,
  caption,
  tone,
  alignEnd,
}: {
  label: string;
  value: string;
  caption: string;
  tone?: "block";
  alignEnd?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-2.5 ${alignEnd ? "items-end" : ""}`}>
      <MonoLabel>{label}</MonoLabel>
      <div className="flex items-baseline gap-2">
        <span
          className={`font-mono text-[44px] font-semibold leading-11 tracking-[-0.02em] ${
            tone === "block" ? "text-block" : "text-ink"
          }`}
        >
          {value}
        </span>
        <span className="font-mono text-[10px] leading-3 text-ink-3">{caption}</span>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { actionId } = useParams<{ actionId?: string }>();
  const navigate = useNavigate();

  const dashboard = useDashboard();
  const actions = useActions({ limit: 50 });

  const items = useMemo(() => (actions.data ? sortBySeverity(actions.data.items) : []), [actions.data]);

  const counts = dashboard.data?.counts ?? {};
  const held = (counts.REQUIRE_APPROVAL ?? 0) + (counts.REQUEST_CONTEXT ?? 0);

  return (
    <div className="flex min-h-0 grow flex-col">
      <PageHeader
        title="Dashboard"
        caption="EVERY DECISION IS PERSISTED — COUNTS AND LATENCY COME STRAIGHT FROM THE AUDIT LEDGER"
        right={
          <MonoLabel className="hidden tracking-[0.1em]! lg:block">
            ORDERED BY DECISION SEVERITY · CLICK A ROW FOR EVIDENCE
          </MonoLabel>
        }
      />

      {/* Stats band */}
      <div className="mt-6 flex shrink-0 flex-wrap items-stretch gap-9 border-b border-hairline px-6 pb-7 pt-8 md:flex-nowrap md:px-12">
        <Stat
          label="EVALUATED ACTIONS"
          value={dashboard.isSuccess ? formatCount(dashboard.data.processed) : "——"}
          caption="recorded total"
        />
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <Stat
          label="EXECUTED"
          value={dashboard.isSuccess ? formatCount(counts.ALLOW ?? 0) : "——"}
          caption="policy: allow"
        />
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <Stat
          label="HELD FOR REVIEW"
          value={dashboard.isSuccess ? formatCount(held) : "——"}
          caption="approval + context"
        />
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <Stat
          label="BLOCKED"
          value={dashboard.isSuccess ? formatCount(counts.BLOCK ?? 0) : "——"}
          caption="policy: block"
          tone="block"
        />
        <span className="grow basis-[0%]" aria-hidden />
        <Stat
          label="P50 PROVIDER LATENCY"
          value={dashboard.isSuccess ? formatLatency(dashboard.data.median_provider_latency_ms).replace(" ms", "") : "——"}
          caption={dashboard.isSuccess && dashboard.data.median_provider_latency_ms !== null ? "ms · measured" : "not measured"}
          alignEnd
        />
      </div>

      {/* Section header */}
      <div className="flex shrink-0 items-center justify-between gap-4 px-6 pb-4 pt-6 md:px-12">
        <div className="flex items-baseline gap-3">
          <h2 className="font-ui text-[18px] font-semibold leading-[22px] text-ink">Proposed payments</h2>
          <span className="font-mono text-[11px] leading-3.5 text-ink-3">
            {actions.isSuccess ? `${formatCount(actions.data.total)} actions in ledger` : "…"}
          </span>
        </div>
      </div>

      {actions.isError ? (
        <div className="px-6 md:px-12">
          <ErrorState error={actions.error} onRetry={() => actions.refetch()} />
        </div>
      ) : actions.isLoading ? (
        <LoadingTable rows={5} />
      ) : items.length === 0 ? (
        <div className="px-6 md:px-12">
          <EmptyState
            label="EMPTY LEDGER"
            title="No actions in the ledger yet."
            caption="Run a scenario from the live demo — decisions are written here the moment they are made."
            action={<PrimaryButton onClick={() => navigate("/demo")}>Open the live demo</PrimaryButton>}
          />
        </div>
      ) : (
        <ActionTable items={items} mode="ledger" onOpen={(id) => navigate(`/dashboard/actions/${id}`)} />
      )}

      <PageFooter
        left="SOURCE FACTS · QUICKBOOKS SPONSOR DATASET + DISCLOSED SYNTHETIC OVERLAYS"
        right="SIMULATED EXECUTION ONLY — NO REAL PAYMENT RAIL"
      />

      {actionId ? <ActionDrawer actionId={actionId} onClose={() => navigate("/dashboard")} /> : null}
    </div>
  );
}
