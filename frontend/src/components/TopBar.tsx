import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { useHealth } from "../api/queries";
import { useStream } from "../api/stream";

const NAV_ITEMS = [
  { to: "/dashboard", label: "LEDGER" },
  { to: "/review", label: "REVIEW" },
  { to: "/demo", label: "DEMO" },
  { to: "/benchmarks", label: "BENCHMARKS" },
];

function formatClock(date: Date): string {
  const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${months[date.getUTCMonth()]} ${date.getUTCDate()} · ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

export function TopBar() {
  const health = useHealth();
  const stream = useStream();
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const streamHealthy = stream.status === "connected";
  const online = health.isSuccess && streamHealthy;

  const dotClass = online ? "bg-allow" : streamHealthy || health.isSuccess ? "bg-approval" : "bg-block";
  const statusText = health.isError
    ? "EVALUATOR OFFLINE"
    : online
      ? "EVALUATOR LIVE"
      : stream.status === "reconnecting"
        ? "STREAM RETRYING"
        : "CONNECTING";

  return (
    <>
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-hairline bg-paper px-6 md:px-12">
        <Link to="/dashboard" className="flex items-center gap-3.5">
          <span className="flex items-center gap-2.5">
            <span className="size-3.5 shrink-0 bg-ink" aria-hidden />
            <span className="font-ui text-[17px] font-bold leading-[22px] tracking-[-0.01em] text-ink">
              LedgerGuard
            </span>
          </span>
          <span className="hidden h-4 w-px shrink-0 bg-hairline sm:block" aria-hidden />
          <span className="hidden font-mono text-[9px] font-medium leading-3 tracking-[0.14em] text-ink-3 sm:block">
            FINANCIAL SAFETY LAYER
          </span>
        </Link>

        <nav className="hidden h-16 items-center gap-7 md:flex" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex h-16 items-center font-mono text-[10px] leading-3 tracking-[0.08em] ${
                  isActive
                    ? "border-b-2 border-ink font-semibold text-ink"
                    : "font-medium text-ink-3 transition-colors hover:text-ink-2"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-5">
          <span className="hidden font-mono text-[10px] leading-3 tracking-[0.08em] text-ink-3 lg:block">
            POLICY CONFIG V1
          </span>
          <button
            type="button"
            onClick={stream.reconnect}
            title="Reconnect the live event stream"
            className="flex items-center gap-1.75"
          >
            <span className={`size-[7px] shrink-0 rounded-full ${dotClass}`} aria-hidden />
            <span className="font-mono text-[10px] font-medium leading-3 tracking-[0.08em] text-ink-2">
              {statusText}
            </span>
          </button>
          <span className="hidden h-4 w-px shrink-0 bg-hairline lg:block" aria-hidden />
          <span className="hidden font-mono text-[10px] leading-3 tracking-[0.08em] text-ink-3 lg:block">
            {formatClock(now)}
          </span>
        </div>
      </header>
      <nav
        className="flex shrink-0 items-center gap-6 overflow-x-auto border-b border-hairline bg-paper px-6 py-2.5 md:hidden"
        aria-label="Primary mobile"
      >
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `whitespace-nowrap font-mono text-[10px] leading-3 tracking-[0.08em] ${
                isActive ? "font-semibold text-ink" : "font-medium text-ink-3"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
