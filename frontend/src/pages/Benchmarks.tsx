import { useMemo, useState } from "react";

import { useBenchmarks } from "../api/queries";
import type { BenchmarkRun, DecimalValue } from "../api/types";
import { PageFooter, PageHeader } from "../components/PageChrome";
import { EmptyState, ErrorState } from "../components/StatePanels";
import { MonoLabel } from "../components/ui";
import { formatMetricValue, formatUtcDateTime, humanizeKey, shortId } from "../lib/format";

const HERO_KEY = "dangerous_action_prevention_rate";

const GRID_KEYS = [
  "accuracy",
  "precision",
  "recall",
  "f1",
  "human_review_rate",
  "provider_failure_rate",
  "unsafe_action_escape_rate",
  "safe_autonomous_execution_coverage",
];

const LATENCY_KEYS = ["latency_p50_ms", "latency_p95_ms"];

const META_KEYS = new Set(["sample_size", "safe_case_count", "unsafe_case_count"]);

function metric(run: BenchmarkRun, key: string): DecimalValue | null | undefined {
  return run.metrics ? run.metrics[key] : undefined;
}

function numericMetric(value: DecimalValue | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function RunBlock({ run }: { run: BenchmarkRun }) {
  const hero = metric(run, HERO_KEY);
  const unsafeEscapeRate = numericMetric(metric(run, "unsafe_action_escape_rate"));
  const accuracy = numericMetric(metric(run, "accuracy"));
  const providerFailureRate = numericMetric(metric(run, "provider_failure_rate"));
  const gridCells = useMemo(() => {
    const cells: Array<{ key: string; label: string; value: DecimalValue | null | undefined }> = GRID_KEYS.map(
      (key) => ({ key, label: humanizeKey(key), value: metric(run, key) }),
    );
    if (run.metrics) {
      for (const key of Object.keys(run.metrics)) {
        if (key === HERO_KEY || META_KEYS.has(key) || GRID_KEYS.includes(key) || LATENCY_KEYS.includes(key)) continue;
        cells.push({ key, label: humanizeKey(key), value: run.metrics[key] });
      }
    }
    return cells.filter((cell) => cell.value !== undefined && cell.value !== null);
  }, [run]);

  const safeCount = metric(run, "safe_case_count");
  const unsafeCount = metric(run, "unsafe_case_count");
  const sampleCaption =
    run.sample_size === null || run.sample_size === undefined
      ? "sample not recorded"
      : `${run.sample_size} scenarios${safeCount !== undefined && safeCount !== null ? ` · ${safeCount} safe / ${unsafeCount} unsafe` : ""}`;

  return (
    <div className="flex flex-col">
      {/* Run metadata band */}
      <div className="flex shrink-0 flex-wrap items-stretch gap-9 border-b border-hairline px-6 pb-5 pt-2 md:flex-nowrap md:px-12">
        <div className="flex flex-col gap-1.75">
          <MonoLabel>RUN ID</MonoLabel>
          <span className="font-mono text-[12px] font-medium leading-4 text-ink">{shortId(run.run_id, 16)}</span>
        </div>
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <div className="flex flex-col gap-1.75">
          <MonoLabel>PROVIDER · MODEL</MonoLabel>
          <span className="font-mono text-[12px] font-medium leading-4 text-ink">
            {run.provider ?? "—"} · {run.model_name ?? "—"}
          </span>
        </div>
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <div className="flex flex-col gap-1.75">
          <MonoLabel>SAMPLE</MonoLabel>
          <span className="font-mono text-[12px] font-medium leading-4 text-ink">{sampleCaption}</span>
        </div>
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <div className="flex flex-col gap-1.75">
          <MonoLabel>RUN AT</MonoLabel>
          <span className="font-mono text-[12px] font-medium leading-4 text-ink">{formatUtcDateTime(run.created_at)}</span>
        </div>
        <span className="hidden w-px shrink-0 self-stretch bg-hairline md:block" aria-hidden />
        <div className="flex flex-col gap-1.75">
          <MonoLabel>ARTIFACT</MonoLabel>
          <span className="font-mono text-[12px] font-medium leading-4 text-ink">evaluation/results/*.json</span>
        </div>
      </div>

      {/* Hero metric */}
      <div className="flex shrink-0 flex-col gap-6 px-6 pb-6 pt-7 md:flex-row md:items-start md:justify-between md:px-12">
        <div className="flex flex-col gap-2">
          <MonoLabel>DANGEROUS ACTION PREVENTION RATE</MonoLabel>
          <span className="font-mono text-[60px] font-semibold leading-16 tracking-[-0.03em] text-allow">
            {hero !== undefined && hero !== null ? formatMetricValue(hero, HERO_KEY) : "—"}
          </span>
          <span className="font-mono text-[10px] leading-3.5 tracking-[0.08em] text-ink-3">
            {unsafeEscapeRate === 0
              ? "NO UNSAFE ACTION REACHED SIMULATED EXECUTION IN THIS RUN"
              : unsafeEscapeRate === null
                ? "UNSAFE-ACTION ESCAPE RATE NOT RECORDED FOR THIS RUN"
                : "SEE UNSAFE-ACTION ESCAPE RATE IN THE RECORDED METRICS"}
          </span>
        </div>
        <div className="flex flex-col gap-2.5 md:pt-6">
          <span className="flex items-center gap-2.25">
            <span className="size-1.5 shrink-0 rounded-full bg-allow" aria-hidden />
            <span className="font-ui text-[13px] leading-[18px] text-ink-2">
              {accuracy === 1 ? "Decisions match expected labels" : "See recorded accuracy for decision-label agreement"}
            </span>
          </span>
          <span className="flex items-center gap-2.25">
            <span className="size-1.5 shrink-0 rounded-full bg-allow" aria-hidden />
            <span className="font-ui text-[13px] leading-[18px] text-ink-2">
              {providerFailureRate === 0
                ? "Zero provider failures in this run"
                : "See recorded provider-failure rate"}
            </span>
          </span>
          <span className="flex items-center gap-2.25">
            <span className="size-1.5 shrink-0 rounded-full bg-allow" aria-hidden />
            <span className="font-ui text-[13px] leading-[18px] text-ink-2">Simulated execution only — no real rail</span>
          </span>
        </div>
      </div>

      {/* Metric grid */}
      {gridCells.length > 0 ? (
        <div className="mx-6 grid shrink-0 grid-cols-2 border border-hairline md:mx-12 md:grid-cols-4">
          {gridCells.map((cell) => (
            <div key={cell.key} className="flex flex-col gap-2 border-b border-r border-hairline p-4 last:border-r-0">
              <MonoLabel>{cell.label.toUpperCase()}</MonoLabel>
              <span className="font-mono text-[26px] font-semibold leading-7.5 tracking-[-0.02em] text-ink">
                {formatMetricValue(cell.value, cell.key)}
              </span>
            </div>
          ))}
        </div>
      ) : null}

      {/* Latency */}
      <div className="mt-6 flex shrink-0 flex-col gap-4 px-6 pb-2 md:flex-row md:items-stretch md:gap-9 md:px-12">
        {LATENCY_KEYS.map((key, index) => (
          <div key={key} className="flex items-stretch gap-9">
            {index > 0 ? <span className="hidden w-px shrink-0 bg-hairline md:block" aria-hidden /> : null}
            <div className="flex flex-col gap-1.75">
              <MonoLabel>{key.replace("latency_", "").replace("_ms", "").toUpperCase()} PROVIDER LATENCY</MonoLabel>
              <span className="font-mono text-[20px] font-semibold leading-6 tracking-[-0.02em] text-ink">
                {formatMetricValue(metric(run, key), key)}
              </span>
            </div>
          </div>
        ))}
        <span className="hidden w-px shrink-0 bg-hairline md:block" aria-hidden />
        <span className="max-w-[480px] self-center font-mono text-[10px] leading-3.5 tracking-[0.08em] text-ink-3">
          {run.provider ?? "PROVIDER"} COMPUTE TIME — NOT END-TO-END. EXTERNAL PROVIDERS ARE CREDENTIAL-GATED AND FAIL
          SAFE.
        </span>
      </div>
    </div>
  );
}

/** Providers the backend can evaluate. Unmeasured ones stay in the menu with no numbers. */
const MODEL_ORDER = ["rules", "gemini", "openjev", "system_one"] as const;

const MODEL_LABELS: Record<string, string> = {
  rules: "Rules",
  gemini: "Gemini",
  openjev: "OpenJev",
  system_one: "System One",
};

function modelLabel(provider: string | null | undefined): string {
  if (!provider) return "Unknown model";
  return MODEL_LABELS[provider] ?? provider;
}

function runLabel(run: BenchmarkRun): string {
  const sample = run.sample_size === null || run.sample_size === undefined ? "sample n/a" : `${run.sample_size} scenarios`;
  return `${modelLabel(run.provider)} · ${run.model_name ?? "model n/a"} · ${sample}`;
}

export function BenchmarksPage() {
  const benchmarks = useBenchmarks();
  const runs = benchmarks.data?.runs ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const options = useMemo(() => {
    const measured = [...runs].sort((a, b) => {
      const rank = (provider: string | null) => {
        const index = MODEL_ORDER.indexOf((provider ?? "") as (typeof MODEL_ORDER)[number]);
        return index === -1 ? MODEL_ORDER.length : index;
      };
      const byProvider = rank(a.provider) - rank(b.provider);
      if (byProvider !== 0) return byProvider;
      return (b.sample_size ?? 0) - (a.sample_size ?? 0);
    });
    const covered = new Set(measured.map((run) => run.provider));
    const missing = MODEL_ORDER.filter((provider) => !covered.has(provider));
    return { measured, missing };
  }, [runs]);

  const selected =
    options.measured.find((run) => run.run_id === selectedId) ?? options.measured[0] ?? null;
  const showingMissing = selectedId !== null && selectedId.startsWith("missing:");
  const missingProvider = showingMissing ? selectedId.slice("missing:".length) : null;

  return (
    <div className="flex min-h-0 grow flex-col">
      <PageHeader
        title="Benchmarks"
        caption="MEASURED ARTIFACTS ONLY — EVERY NUMBER CARRIES ITS RUN METADATA"
        right={
          <MonoLabel className="hidden tracking-[0.1em]! lg:block">
            {benchmarks.isSuccess ? (benchmarks.data.status === "measured" ? "MEASURED · NOT ESTIMATED" : "NOT RUN") : "…"}
          </MonoLabel>
        }
      />

      <div className="flex min-h-0 grow flex-col pt-4">
        {benchmarks.isError ? (
          <div className="px-6 md:px-12">
            <ErrorState error={benchmarks.error} onRetry={() => benchmarks.refetch()} />
          </div>
        ) : benchmarks.isLoading ? (
          <div className="flex flex-col gap-5 px-6 md:px-12">
            <div className="h-3.5 w-40 animate-pulse rounded-[2px] bg-ink/7" />
            <div className="h-16 w-full max-w-[560px] animate-pulse rounded-[2px] bg-ink/7" />
            <div className="h-40 w-full animate-pulse rounded-[2px] bg-ink/7" />
          </div>
        ) : benchmarks.data?.status === "not_run" ? (
          <div className="px-6 md:px-12">
            <EmptyState
              label="NO MEASURED RUNS"
              title="This benchmark suite has not run yet."
              caption="The API reports status not_run and the UI renders nothing measured — never a placeholder metric. Produce a run with: .venv/bin/python -m evaluation.run_eval"
            />
          </div>
        ) : (
          <div className="flex flex-col">
            <div className="flex flex-col gap-2 px-6 pb-5 md:px-12">
              <label className="flex flex-col gap-1.75" htmlFor="benchmark-model">
                <MonoLabel>MODEL</MonoLabel>
                <select
                  id="benchmark-model"
                  value={showingMissing ? selectedId ?? "" : (selected?.run_id ?? "")}
                  onChange={(event) => setSelectedId(event.target.value)}
                  className="h-10 w-full max-w-[520px] rounded-[3px] border border-hairline bg-surface px-3 font-mono text-[12px] text-ink"
                >
                  {options.measured.map((run) => (
                    <option key={run.run_id ?? runLabel(run)} value={run.run_id ?? ""}>
                      {runLabel(run)}
                    </option>
                  ))}
                  {options.missing.map((provider) => (
                    <option key={provider} value={`missing:${provider}`}>
                      {MODEL_LABELS[provider]} — not measured
                    </option>
                  ))}
                </select>
              </label>
              <MonoLabel className="tracking-[0.08em]!">
                SWITCH MODELS TO COMPARE THE SAME METRICS · UNMEASURED MODELS SHOW NO NUMBERS
              </MonoLabel>
            </div>

            {options.measured.length > 1 ? (
              <div className="mx-6 mb-6 overflow-x-auto border border-hairline md:mx-12">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-hairline">
                      {["MODEL", "SAMPLE", "PREVENTION", "ACCURACY", "ESCAPE"].map((heading) => (
                        <th
                          key={heading}
                          className="whitespace-nowrap px-4 py-2.5 font-mono text-[10px] font-medium tracking-[0.12em] text-ink-3"
                        >
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {options.measured.map((run) => {
                      const active = run.run_id === selected?.run_id && !showingMissing;
                      return (
                        <tr
                          key={run.run_id ?? runLabel(run)}
                          className={active ? "bg-ink/3" : "hover:bg-ink/3"}
                        >
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              onClick={() => setSelectedId(run.run_id)}
                              className="whitespace-nowrap text-left font-mono text-[12px] font-medium text-ink"
                            >
                              {modelLabel(run.provider)} · {run.model_name ?? "—"}
                            </button>
                          </td>
                          <td className="px-4 py-3 font-mono text-[12px] text-ink-2">{run.sample_size ?? "—"}</td>
                          <td className="px-4 py-3 font-mono text-[12px] text-ink">
                            {formatMetricValue(metric(run, HERO_KEY), HERO_KEY)}
                          </td>
                          <td className="px-4 py-3 font-mono text-[12px] text-ink">
                            {formatMetricValue(metric(run, "accuracy"), "accuracy")}
                          </td>
                          <td className="px-4 py-3 font-mono text-[12px] text-ink">
                            {formatMetricValue(metric(run, "unsafe_action_escape_rate"), "unsafe_action_escape_rate")}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}

            {showingMissing ? (
              <div className="px-6 md:px-12">
                <EmptyState
                  label="NOT MEASURED"
                  title={`${missingProvider ? modelLabel(missingProvider) : "This model"} has no measured run.`}
                  caption="The menu lists every model the benchmark can run. This one has no artifact yet, so nothing is shown — never a placeholder metric."
                />
              </div>
            ) : selected ? (
              <RunBlock key={selected.run_id ?? "run"} run={selected} />
            ) : null}
          </div>
        )}
      </div>

      <div className="h-8" aria-hidden />
      <PageFooter
        left="REPRODUCE · .venv/bin/python -m evaluation.run_eval · CASE SET + POLICY CONFIG HASHES LIVE IN THE ARTIFACT"
        right="STATUS not_run RENDERS AN EMPTY STATE — NEVER A PLACEHOLDER METRIC"
      />
    </div>
  );
}
