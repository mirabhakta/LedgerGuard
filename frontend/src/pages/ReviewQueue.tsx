import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useActions } from "../api/queries";
import type { ActionListItem } from "../api/types";
import { ActionDrawer } from "../components/ActionDrawer";
import { ActionTable } from "../components/ActionTable";
import { PageFooter, PageHeader } from "../components/PageChrome";
import { EmptyState, ErrorState, LoadingTable } from "../components/StatePanels";
import { MonoLabel } from "../components/ui";
import { formatCount } from "../lib/format";

const PROTOCOL_ROWS = [
  {
    action: "APPROVE",
    description:
      "Re-validates the exact assessment hash, then the guarded simulator executes and the outcome is written to the audit ledger.",
    code: "resolution=approve",
  },
  {
    action: "REJECT",
    description: "Terminal. The action is recorded as not executed — nothing downstream can resume it.",
    code: "resolution=reject",
  },
  {
    action: "ADD CONTEXT",
    description:
      "Offered only on REQUEST_CONTEXT items — supplied fields carry provenance and the action is re-evaluated.",
    code: "resolution=provide_context",
  },
];

function oldestFirst(items: ActionListItem[]): ActionListItem[] {
  return [...items].sort((a, b) => a.created_at.localeCompare(b.created_at));
}

/**
 * `final_action` is the immutable policy decision, so resolved actions (approved and
 * executed, rejected, ...) still match the server filter. Only `status === "decided"`
 * is still waiting on a human; everything else has left the queue.
 */
function pendingOnly(items: ActionListItem[] | undefined): ActionListItem[] {
  return oldestFirst((items ?? []).filter((item) => item.status === "decided"));
}

export function ReviewQueuePage() {
  const { actionId } = useParams<{ actionId?: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "context" ? "context" : "approval";

  const approvals = useActions({ final_action: "REQUIRE_APPROVAL", limit: 100 });
  const contexts = useActions({ final_action: "REQUEST_CONTEXT", limit: 100 });

  const active = tab === "approval" ? approvals : contexts;
  const pendingApprovals = useMemo(() => pendingOnly(approvals.data?.items), [approvals.data]);
  const pendingContexts = useMemo(() => pendingOnly(contexts.data?.items), [contexts.data]);
  const items = tab === "approval" ? pendingApprovals : pendingContexts;

  return (
    <div className="flex min-h-0 grow flex-col">
      <PageHeader
        title="Review queue"
        caption="ACTIONS THE POLICY ENGINE HELD FOR A HUMAN — NOTHING HERE CAN EXECUTE ON ITS OWN"
        right={<MonoLabel className="hidden tracking-[0.1em]! lg:block">ORDERED BY AGE · OLDEST FIRST</MonoLabel>}
      />

      {/* Tabs */}
      <div className="flex shrink-0 items-end gap-7 px-6 pt-5 md:px-12" role="tablist" aria-label="Queue filters">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "approval"}
          onClick={() => setSearchParams({})}
          className={`flex h-10 items-center gap-2.5 border-b-2 pb-px ${
            tab === "approval" ? "border-ink" : "border-transparent"
          }`}
        >
          <span
            className={`font-mono text-[10px] leading-3 tracking-[0.08em] ${
              tab === "approval" ? "font-semibold text-ink" : "font-medium text-ink-3"
            }`}
          >
            REQUIRE APPROVAL
          </span>
          <span className="font-mono text-[10px] font-medium leading-3 tracking-[0.08em] text-ink-3">
            {approvals.isSuccess ? formatCount(pendingApprovals.length) : "——"}
          </span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "context"}
          onClick={() => setSearchParams({ tab: "context" })}
          className={`flex h-10 items-center gap-2.5 border-b-2 pb-px ${
            tab === "context" ? "border-ink" : "border-transparent"
          }`}
        >
          <span
            className={`font-mono text-[10px] leading-3 tracking-[0.08em] ${
              tab === "context" ? "font-semibold text-ink" : "font-medium text-ink-3"
            }`}
          >
            REQUEST CONTEXT
          </span>
          <span className="font-mono text-[10px] font-medium leading-3 tracking-[0.08em] text-ink-3">
            {contexts.isSuccess ? formatCount(pendingContexts.length) : "——"}
          </span>
        </button>
      </div>

      <div className="mt-6">
        {active.isError ? (
          <div className="px-6 md:px-12">
            <ErrorState error={active.error} onRetry={() => active.refetch()} />
          </div>
        ) : active.isLoading ? (
          <LoadingTable rows={3} />
        ) : items.length === 0 ? (
          <div className="px-6 md:px-12">
            <EmptyState
              label="QUEUE CLEAR"
              title="No actions awaiting a human decision."
              caption={
                tab === "approval"
                  ? "Holds appear here the moment the policy engine requires approval."
                  : "Context requests appear here when a required fact is missing from the snapshot."
              }
            />
          </div>
        ) : (
          <ActionTable
            items={items}
            mode="queue"
            // Keep ?tab= so the list behind the drawer stays on the tab the reviewer chose.
            onOpen={(id) => navigate({ pathname: `/review/actions/${id}`, search: searchParams.toString() })}
          />
        )}
      </div>

      {/* Resolution protocol */}
      <div className="mt-8 flex shrink-0 flex-col gap-3 px-6 md:px-12">
        <MonoLabel>RESOLUTION PROTOCOL · WHAT EACH HUMAN ACTION DOES</MonoLabel>
        <div className="flex flex-col border border-hairline">
          {PROTOCOL_ROWS.map((row) => (
            <div
              key={row.action}
              className="flex flex-col gap-1.5 border-b border-hairline px-4 py-4 last:border-b-0 md:h-16 md:flex-row md:items-center md:gap-5 md:py-0"
            >
              <span className="w-[150px] shrink-0 font-mono text-[10px] font-semibold leading-3 tracking-[0.08em] text-ink">
                {row.action}
              </span>
              <span className="grow basis-[0%] font-ui text-[13px] leading-[18px] text-ink-2">{row.description}</span>
              <span className="shrink-0 font-mono text-[10px] leading-3 tracking-[0.08em] text-ink-3">{row.code}</span>
            </div>
          ))}
        </div>
      </div>

      <PageFooter
        left="APPROVALS CARRY THE EXACT ASSESSMENT HASH — STALE SUBMITS RETURN 409 · SIMULATED EXECUTION ONLY"
        right="/api/actions · final_action=REQUIRE_APPROVAL | REQUEST_CONTEXT"
      />

      {actionId ? <ActionDrawer actionId={actionId} onClose={() => navigate({ pathname: "/review", search: searchParams.toString() })} /> : null}
    </div>
  );
}
