import type { ReactNode } from "react";

export function PageHeader({ title, caption, right }: { title: string; caption: string; right?: ReactNode }) {
  return (
    <div className="flex shrink-0 flex-col gap-4 px-6 pt-6 md:flex-row md:items-end md:justify-between md:px-12">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-ui text-[22px] font-bold leading-7 tracking-[-0.01em] text-ink">{title}</h1>
        <p className="font-mono text-[10px] leading-3.5 tracking-[0.06em] text-ink-3">{caption}</p>
      </div>
      {right ? <div className="flex items-center gap-4">{right}</div> : null}
    </div>
  );
}

export function PageFooter({ left, right }: { left: string; right: string }) {
  return (
    <div className="mt-auto flex shrink-0 flex-col gap-2 border-t border-hairline px-6 py-3 md:flex-row md:items-center md:justify-between md:px-12">
      <span className="font-mono text-[9px] font-medium leading-3.5 tracking-[0.1em] text-ink-3">{left}</span>
      <span className="font-mono text-[9px] font-medium leading-3.5 tracking-[0.1em] text-ink-3">{right}</span>
    </div>
  );
}
