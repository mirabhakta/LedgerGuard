import type { ButtonHTMLAttributes, ReactNode } from "react";

export function MonoLabel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`font-mono text-[10px] font-medium leading-3 tracking-[0.14em] text-ink-3 ${className}`}>
      {children}
    </span>
  );
}

export function MonoValue({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`font-mono text-[10px] leading-3 tracking-[0.06em] text-ink-2 ${className}`}>{children}</span>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode };

export function PrimaryButton({ children, className = "", ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      className={`flex h-[42px] items-center justify-center gap-2.5 rounded-[3px] bg-ink px-[18px] font-ui text-[13px] font-semibold leading-4 tracking-[0.01em] text-surface transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, className = "", ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      className={`flex h-[42px] items-center justify-center rounded-[3px] border border-hairline bg-surface px-[18px] font-ui text-[13px] font-medium leading-4 text-ink transition-colors hover:border-ink-3 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {children}
    </button>
  );
}

export function LabeledRow({
  label,
  children,
  labelWidth = "w-[110px]",
}: {
  label: string;
  children: ReactNode;
  labelWidth?: string;
}) {
  return (
    <div className="flex items-baseline gap-3">
      <span className={`${labelWidth} shrink-0 font-mono text-[10px] leading-3 tracking-[0.06em] text-ink-3`}>
        {label}
      </span>
      <span className="grow basis-[0%]">{children}</span>
    </div>
  );
}
