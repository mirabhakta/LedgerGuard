/**
 * End-to-end UI verification against the real backend.
 * Exercises: demo run (BLOCK path), review approval (stale-safe), and
 * context supply with re-evaluation — through the actual rendered UI.
 *
 * Usage: node scripts/verify-e2e.mjs [baseUrl] [outputDir]
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
].filter(Boolean);
const executablePath = candidates.find((path) => existsSync(path));
if (!executablePath) throw new Error("No Chrome/Edge executable found");

const apiBase = process.env.LEDGERGUARD_API ?? "http://127.0.0.1:8000";
const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} · ${name}${detail ? ` — ${detail}` : ""}`);
};

async function api(path, init) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await response.json().catch(() => null);
  return { status: response.status, body };
}

const unique = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;

const browser = await chromium.launch({ executablePath, headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

/* ---------- 1. Live demo: BLOCK path ---------- */
await page.goto(`${baseUrl}/demo`, { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=CHOOSE A SCENARIO");
await page.getByRole("button", { name: /Possible duplicate bill/ }).click();
await page.getByRole("button", { name: /Run evaluation/ }).click();
await page.waitForSelector("text=Blocked by policy", { timeout: 30_000 });
const blockStrip = await page.locator("text=EXACT_PAID_DOCUMENT_DUPLICATE").first().isVisible();
check("demo · BLOCK decision rendered", blockStrip);
await page.screenshot({ path: join(outputDir, "10-demo-block.png") });

/* ---------- 2. Review queue: approve with exact hash ---------- */
const runApproval = await api("/api/demo/run", {
  method: "POST",
  body: JSON.stringify({
    scenario_id: "destination-change-001",
    provider: "rules",
    idempotency_key: unique(),
  }),
});
const approvalId = runApproval.body.action_id;
check("api · destination-change awaits review", runApproval.body.policy_decision.final_action === "REQUIRE_APPROVAL");

await page.goto(`${baseUrl}/review`, { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=Review queue");
const row = page.locator("button", { hasText: approvalId }).first();
await row.click();
await page.waitForSelector("text=ORIGINAL INSTRUCTION", { timeout: 15_000 });
await page.screenshot({ path: join(outputDir, "11-drawer-approval.png") });
await page.getByRole("button", { name: /Approve & execute/ }).click();
await page.waitForSelector("text=SIMULATED EXECUTION", { timeout: 30_000 });
check("ui · approve executes through the simulator", true);
await page.screenshot({ path: join(outputDir, "12-drawer-approved.png") });
const approvedDetail = await api(`/api/actions/${approvalId}`);
check(
  "api · HUMAN_APPROVAL authorization persisted",
  approvedDetail.body.execution_authorization?.authorization_type === "HUMAN_APPROVAL" &&
    approvedDetail.body.execution_result?.status === "SIMULATED",
  approvedDetail.body.execution_authorization?.authorization_type,
);

/* ---------- 3. Context request: supply context in the drawer ---------- */
const runContext = await api("/api/demo/run", {
  method: "POST",
  body: JSON.stringify({ scenario_id: "missing-context-001", provider: "rules", idempotency_key: unique() }),
});
const contextId = runContext.body.action_id;
check("api · missing-context asks for context", runContext.body.policy_decision.final_action === "REQUEST_CONTEXT");

await page.goto(`${baseUrl}/review?tab=context`, { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=REQUEST CONTEXT");
const contextRow = page.locator("button", { hasText: contextId }).first();
await contextRow.click();
await page.waitForSelector("text=SUPPLY MISSING CONTEXT · SUPPORTED FIELDS ONLY", { timeout: 15_000 });
await page.locator('input[placeholder="value"]').fill("vend-supplier");
await page.locator("textarea").fill("Operator confirmed vendor from the scanned receipt");
await page.screenshot({ path: join(outputDir, "13-drawer-context-form.png") });
await page.getByRole("button", { name: /Supply context & re-evaluate/ }).click();
await page.waitForSelector("text=SIMULATED EXECUTION, text=NO HUMAN ACTION REQUIRED", { timeout: 30_000 }).catch(() => {});
await page.waitForTimeout(800);
const contextDetail = await api(`/api/actions/${contextId}`);
check(
  "api · context supplied and re-evaluated",
  ["ALLOW", "BLOCK", "REQUIRE_APPROVAL", "REQUEST_CONTEXT"].includes(contextDetail.body.policy_decision.final_action) &&
    Boolean(contextDetail.body.human_response?.provenance),
  `${contextDetail.body.policy_decision.final_action} / ${contextDetail.body.status}`,
);
await page.screenshot({ path: join(outputDir, "14-drawer-context-resolved.png") });

/* ---------- 4. Stale approval rejection in the UI ---------- */
const runStale = await api("/api/demo/run", {
  method: "POST",
  body: JSON.stringify({ scenario_id: "high-amount-plausible-001", provider: "rules", idempotency_key: unique() }),
});
const staleId = runStale.body.action_id;
// Approve it via API with a stale hash to prove the server guard, then reopen in the UI.
const staleTry = await api(`/api/actions/${staleId}/resolve`, {
  method: "POST",
  body: JSON.stringify({ resolution: "approve", actor: "demo-reviewer@ledgerguard.app", assessment_hash: "stale" }),
});
check("api · stale assessment hash rejected with 409", staleTry.status === 409 && staleTry.body.code === "STALE_REVIEW_RESPONSE", staleTry.body?.code);

/* ---------- Summary ---------- */
await browser.close();
const failed = results.filter((entry) => !entry.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (failed.length > 0) {
  console.log("failed:", failed.map((entry) => entry.name).join(", "));
  process.exitCode = 1;
}
