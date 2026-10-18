/**
 * UI screenshot harness for design review against the Paper artboards.
 * Uses the locally installed Chrome via playwright-core (no browser download).
 *
 * Usage:
 *   node scripts/screenshots.mjs [baseUrl] [outputDir]
 * Optional env:
 *   CHROME_PATH  – explicit Chrome/Edge executable
 *   ACTION_ID    – action to open in the drawer (defaults to first REQUIRE_APPROVAL)
 *   BLOCKED_ID   – action to open in the blocked-drawer shot
 */
import { chromium } from "playwright-core";
import { mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";

const baseUrl = process.argv[2] ?? "http://localhost:5173";
const outputDir = process.argv[3] ?? "shots";
mkdirSync(outputDir, { recursive: true });

const candidates = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);

const executablePath = candidates.find((path) => existsSync(path));
if (!executablePath) throw new Error("No Chrome/Edge executable found");

const apiBase = process.env.LEDGERGUARD_API ?? "http://127.0.0.1:8000";

async function fetchJson(path) {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(`${path} -> ${response.status}`);
  return response.json();
}

const pending = await fetchJson("/api/actions?final_action=REQUIRE_APPROVAL&limit=10");
const approval = pending.items.find((item) => !["blocked", "executed", "review_rejected"].includes(item.status));
const blocked = (await fetchJson("/api/actions?final_action=BLOCK&limit=1")).items[0];

const actionId = process.env.ACTION_ID ?? approval?.action_id ?? blocked?.action_id;
const blockedId = process.env.BLOCKED_ID ?? blocked?.action_id;

const targets = [
  { name: "01-landing", url: `${baseUrl}/`, fullPage: true, wait: 2000 },
  { name: "02-dashboard", url: `${baseUrl}/dashboard`, wait: 2500, ready: "text=Proposed payments" },
  { name: "03-drawer-approval", url: `${baseUrl}/dashboard/actions/${actionId}`, wait: 2500, ready: "text=ORIGINAL INSTRUCTION" },
  { name: "04-review", url: `${baseUrl}/review`, wait: 2500, ready: "text=Review queue" },
  { name: "05-demo", url: `${baseUrl}/demo`, wait: 2500, ready: "text=CHOOSE A SCENARIO" },
  { name: "06-benchmarks", url: `${baseUrl}/benchmarks`, wait: 2500, ready: "text=Benchmarks" },
  { name: "07-drawer-blocked", url: `${baseUrl}/dashboard/actions/${blockedId}`, wait: 2500, ready: "text=TERMINAL" },
  { name: "08-dashboard-mobile", url: `${baseUrl}/dashboard`, viewport: { width: 420, height: 900 }, wait: 2500, ready: "text=Proposed payments" },
  { name: "09-demo-mobile", url: `${baseUrl}/demo`, viewport: { width: 420, height: 900 }, wait: 2500, ready: "text=CHOOSE A SCENARIO" },
];

const browser = await chromium.launch({ executablePath, headless: true });

for (const target of targets) {
  const viewport = target.viewport ?? { width: 1440, height: 900 };
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(target.url, { waitUntil: "domcontentloaded" });
  if (target.ready) {
    try {
      await page.waitForSelector(target.ready, { timeout: 10_000 });
    } catch {
      console.warn(`warn: ${target.name} ready-selector not found (${target.ready})`);
    }
  }
  await page.waitForTimeout(target.wait ?? 2000);
  const file = join(outputDir, `${target.name}.png`);
  await page.screenshot({ path: file, fullPage: Boolean(target.fullPage) });
  console.log(`saved ${file}`);
  await context.close();
}

await browser.close();
console.log("done");
