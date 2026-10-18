"""
LedgerGuard iMessage bot (Photon 2.0 beta, shared iMessage line).

What it does
- Runs continuously and polls Photon for new iMessages.
- Only listens to the configured owner number (PHOTON_TEST_SENDER).
- Commands (case-insensitive):
    "pay today's bills"   -> runs the hero scenarios through LedgerGuard
    "run <scenario_id>"   -> runs one named scenario
    "scenarios"           -> lists available scenarios
    "approve" / "yes"     -> approves the payment waiting for review
    "reject" / "no"       -> rejects the payment waiting for review
    "status"              -> shows what is waiting for review
    anything else         -> shows help

Backend
- Default: real LedgerGuard backend at http://127.0.0.1:8000/api (see docs/API_HANDOFF.md).
- Set LEDGERGUARD_MOCK=1 to use built-in mock results instead (for testing without the backend).
- Set LEDGERGUARD_PROVIDER to rules | gemini | system_one (default: system_one).

Notes
- The iMessage text only chooses which pre-built scenario to run. It does not change the
  scenario's data or the owner's constraints. Decisions come from the backend pipeline.
- Do NOT use parentMessageId (shared lines reject threaded replies).
- The bot never executes payments itself. On any error it tells the owner nothing was sent.
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx
from photon_api import ApiError, Photon
from photon_api.generated.models import (
    SendMessageRequest,
    SendTextContent,
    TextContent,
    UserSnapshot,
)
from photon_api.rpc_generated import (
    ListMessagesInput,
    SendMessageHeader,
    SendMessageInput,
    SendMessagePath,
)

POLL_SECONDS = 2.0
ACTOR = "owner_via_imessage"

ALL_SCENARIOS = [
    "safe-normal-payment-001",
    "semantic-duplicate-001",
    "destination-change-001",
    "missing-context-001",
    "goal-mismatch-001",
    "high-amount-plausible-001",
]
# The three hero cases from the spec: Adobe (ALLOW), AWS (duplicate), Acme (destination change)
HERO_SCENARIOS = [
    "safe-normal-payment-001",
    "semantic-duplicate-001",
    "destination-change-001",
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def configuration():
    names = ("PHOTON_API_KEY", "PHOTON_PROJECT_ID", "PHOTON_AGENT_HANDLE", "PHOTON_TEST_SENDER")
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    return {
        "key": os.environ["PHOTON_API_KEY"],
        "project": os.environ["PHOTON_PROJECT_ID"],
        "agent": os.environ["PHOTON_AGENT_HANDLE"],
        "owner": os.environ["PHOTON_TEST_SENDER"],
        "api": os.environ.get("LEDGERGUARD_API_URL", "http://127.0.0.1:8000/api").rstrip("/"),
        "provider": os.environ.get("LEDGERGUARD_PROVIDER", "system_one"),
        "mock": os.environ.get("LEDGERGUARD_MOCK") == "1",
    }


# ---------------------------------------------------------------------------
# Result shape used by the bot (same for mock and backend)
#   {"id", "vendor", "amount", "decision", "reasons", "assessment_hash", "latency_ms"}
# ---------------------------------------------------------------------------

# Actions waiting for the owner's decision: action_id -> result dict
pending = {}


# ----- Mock (only when LEDGERGUARD_MOCK=1) ---------------------------------

def run_scenario_mock(scenario_id, run_key):
    """MOCK DATA. Not real LedgerGuard results."""
    table = {
        "safe-normal-payment-001": ("Adobe", "149", "ALLOW", ["POLICY_ALLOW"]),
        "semantic-duplicate-001": ("AWS", "4210", "BLOCK", ["DUPLICATE_OBLIGATION"]),
        "destination-change-001": ("Acme Supplies", "18400", "REQUIRE_APPROVAL", ["COUNTERPARTY_CHANGE"]),
    }
    vendor, amount, decision, reasons = table.get(
        scenario_id, ("Unknown vendor", "0", "REQUIRE_APPROVAL", ["MOCK_UNKNOWN_SCENARIO"]))
    return {"id": f"mock_{scenario_id}_{run_key}", "vendor": vendor, "amount": amount,
            "decision": decision, "reasons": reasons, "assessment_hash": None, "latency_ms": None}


# ----- Real backend ----------------------------------------------------------

def find_key(obj, key):
    """Return the first value for `key` anywhere inside a nested dict/list."""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        for v in obj.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def to_result(data):
    """Turn an ActionDetailResponse into the bot's result shape."""
    action = data.get("action") or {}
    policy = data.get("policy_decision") or {}
    decision = policy.get("final_action") or data.get("final_action") or "REQUIRE_APPROVAL"
    vendor = (action.get("vendor_name") or action.get("counterparty_name")
              or action.get("vendor_id") or action.get("counterparty_id") or "Unknown vendor")
    reasons = data.get("reason_codes") or policy.get("reason_codes") or []
    return {
        "id": data["action_id"],
        "vendor": vendor,
        "amount": action.get("amount", "0"),
        "decision": decision,
        "reasons": reasons,
        "assessment_hash": find_key(data, "assessment_hash"),
        "latency_ms": data.get("latency_ms"),
    }


def run_scenario_backend(c, http, scenario_id, run_key):
    body = {
        "scenario_id": scenario_id,
        "provider": c["provider"],
        "idempotency_key": f"imsg-{run_key}-{scenario_id}"[:128],
    }
    r = http.post(f"{c['api']}/demo/run", json=body)
    r.raise_for_status()
    return to_result(r.json())


def resolve_backend(c, http, item, approved):
    body = {"resolution": "approve" if approved else "reject", "actor": ACTOR}
    if item.get("assessment_hash"):
        body["assessment_hash"] = item["assessment_hash"]
    r = http.post(f"{c['api']}/actions/{item['id']}/resolve", json=body)
    r.raise_for_status()
    return r.json()


def backend_healthy(c, http):
    try:
        return http.get(f"{c['api']}/health").status_code == 200
    except httpx.HTTPError:
        return False


# ---------------------------------------------------------------------------
# Turning results into iMessage text
# ---------------------------------------------------------------------------

ICONS = {"ALLOW": "✅", "REQUIRE_APPROVAL": "⚠️", "REQUEST_CONTEXT": "❓", "BLOCK": "⛔"}

HELP_TEXT = (
    "Hi, I'm LedgerGuard. I check your agent's payments before money leaves.\n\n"
    "Try:\n"
    "• \"Pay today's bills\"\n"
    "• \"Approve\" or \"Reject\"\n"
    "• \"Status\"\n"
    "• \"Scenarios\" or \"Run goal-mismatch-001\""
)


def money(amount):
    try:
        return f"${Decimal(str(amount)):,.2f}".replace(".00", "")
    except (InvalidOperation, ValueError):
        return f"${amount}"


def reason_text(codes):
    codes = [c for c in codes if c != "POLICY_ALLOW"]
    if not codes:
        return ""
    return ", ".join(c.replace("_", " ").lower() for c in codes[:2])


def format_line(r):
    icon = ICONS.get(r["decision"], "•")
    why = reason_text(r["reasons"])
    why = f" ({why})" if why else ""
    label = {
        "ALLOW": "approved by policy",
        "BLOCK": "blocked",
        "REQUIRE_APPROVAL": "on hold for you",
        "REQUEST_CONTEXT": "needs more info",
    }.get(r["decision"], r["decision"].lower())
    return f"{icon} {r['vendor']} {money(r['amount'])} {label}{why}"


def format_results(results):
    lines = ["LedgerGuard checked today's bills:", ""]
    lines += [format_line(r) for r in results]
    if any(r["decision"] == "REQUIRE_APPROVAL" for r in results):
        lines += ["", "Please confirm with the vendor using a number you trust, then reply APPROVE or REJECT."]
    if any(r["decision"] == "REQUEST_CONTEXT" for r in results):
        lines += ["", "Some bills need more details. Please add them in the LedgerGuard dashboard."]
    lines += ["", "No real money moves in this demo."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deciding what to reply
# ---------------------------------------------------------------------------

def run_scenarios(c, http, scenario_ids, run_key):
    results = []
    for sid in scenario_ids:
        r = run_scenario_mock(sid, run_key) if c["mock"] else run_scenario_backend(c, http, sid, run_key)
        results.append(r)
        if r["decision"] == "REQUIRE_APPROVAL":
            pending[r["id"]] = r
    return results


def handle(c, http, text, run_key):
    t = text.strip().lower().replace("’", "'")

    if "pay" in t and "bill" in t:
        pending.clear()
        return format_results(run_scenarios(c, http, HERO_SCENARIOS, run_key))

    if t.startswith("run "):
        sid = t[4:].strip()
        if sid not in ALL_SCENARIOS:
            return "I don't know that scenario. Text \"Scenarios\" to see the list."
        return format_results(run_scenarios(c, http, [sid], run_key))

    if t == "scenarios":
        return "Available scenarios:\n" + "\n".join(f"• {s}" for s in ALL_SCENARIOS)

    if t in ("approve", "approved", "yes", "y"):
        return decide(c, http, approved=True)

    if t in ("reject", "rejected", "no", "n"):
        return decide(c, http, approved=False)

    if t == "status":
        if not pending:
            return "Nothing is waiting for your review."
        items = "\n".join(f"⚠️ {r['vendor']} {money(r['amount'])}" for r in pending.values())
        return f"Waiting for your review:\n{items}"

    return HELP_TEXT


def decide(c, http, approved):
    if not pending:
        return "There's nothing waiting for your approval right now."
    # Hackathon simplification: one pending action at a time, oldest first.
    action_id, item = next(iter(pending.items()))
    if not c["mock"]:
        resolve_backend(c, http, item, approved)
    del pending[action_id]
    desc = f"{item['vendor']} {money(item['amount'])}"
    if approved:
        return f"Got it. You approved {desc}. The decision is logged in the audit trail."
    return f"Got it. {desc} is cancelled. The decision is logged in the audit trail."


# ---------------------------------------------------------------------------
# Photon plumbing
# ---------------------------------------------------------------------------

def incoming_text(item, c, started_at):
    """Return (message, text) if it is a new direct iMessage from the owner."""
    m = item.root.root
    if m.platform != "imessage" or m.status != "received":
        return None
    if datetime.fromisoformat(m.createdAt) < started_at:
        return None
    if not isinstance(m.receivedBy, UserSnapshot):
        return None
    sender, agent, space = m.sentBy.root, m.receivedBy.root, m.space.root
    # Security: only the registered owner can give commands.
    if sender.kind != "human" or sender.handle != c["owner"]:
        return None
    if agent.kind != "agent" or agent.handle != c["agent"]:
        return None
    if space.kind != "direct":
        return None
    if not isinstance(m.content, TextContent) or m.content.format != "plain":
        return None
    return m, m.content.text


def send(photon, c, m, text):
    photon.projects.send_message(
        SendMessageInput(
            path=SendMessagePath(id=c["project"]),
            headers=SendMessageHeader.model_validate({"idempotency-key": f"lg-reply:{m.id}"}),
            body=SendMessageRequest(
                spaceId=m.space.root.id,
                senderId=m.receivedBy.root.id,
                # No parentMessageId: shared lines reject threaded replies.
                content=SendTextContent(type="text", format="plain", text=text),
            ),
        )
    )


def run(c):
    started_at = datetime.now(timezone.utc)
    created_since = (started_at - timedelta(seconds=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    seen = set()

    with Photon(headers={"Authorization": f"Bearer {c['key']}"}) as photon, httpx.Client(timeout=60.0) as http:
        if c["mock"]:
            print("Mode: MOCK data (LEDGERGUARD_MOCK=1)")
        else:
            ok = backend_healthy(c, http)
            print(f"Mode: backend {c['api']} | provider={c['provider']} | health={'OK' if ok else 'NOT REACHABLE'}")
            if not ok:
                print("   Start the backend first, or set LEDGERGUARD_MOCK=1 to test without it.")
        print("LedgerGuard bot running. Text the agent number. Press Ctrl+C to stop.")

        while True:
            query = {"createdSince": created_since, "direction": "received", "order": "asc",
                     "pageSize": 100, "platform": "imessage"}
            while True:
                page = photon.projects.list_messages(
                    ListMessagesInput.model_validate({"path": {"id": c["project"]}, "query": query})
                )
                for item in page.items:
                    found = incoming_text(item, c, started_at)
                    if not found:
                        continue
                    m, text = found
                    if m.id in seen:
                        continue
                    seen.add(m.id)
                    print(f"<- {text!r}")
                    try:
                        reply = handle(c, http, text, run_key=m.id)
                    except httpx.HTTPStatusError as error:
                        print(f"   backend {error.response.status_code}: {error.response.text[:300]}", file=sys.stderr)
                        reply = "LedgerGuard couldn't finish that check, so nothing was paid. Please try again or use the dashboard."
                    except Exception as error:  # fail safe: never auto-pay on errors
                        print(f"   handler error: {error!r}", file=sys.stderr)
                        reply = "LedgerGuard couldn't finish that check, so nothing was paid. Please try again or use the dashboard."
                    send(photon, c, m, reply)
                    print(f"-> {reply.splitlines()[0]}")
                token = page.nextPageToken
                if not isinstance(token, str):
                    break
                query["pageToken"] = token
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        run(configuration())
    except KeyboardInterrupt:
        print("\nStopped.")
    except ApiError as error:
        print(f"Photon API error {error.status} (request {error.request_id or 'unknown'}).", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
