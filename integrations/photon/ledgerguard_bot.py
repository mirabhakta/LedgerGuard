"""
LedgerGuard iMessage bot (Photon 2.0 beta, shared iMessage line).

What it does
- Runs continuously and polls Photon for new iMessages.
- Only listens to the configured owner number (PHOTON_TEST_SENDER).
- Understands a few commands:
    "pay today's bills"   -> runs the LedgerGuard check on today's bills
    "approve" / "yes"     -> approves the payment waiting for review
    "reject" / "no"       -> rejects the payment waiting for review
    "status"              -> shows what is waiting for review
    anything else         -> shows help

Backend
- By default it uses MOCK results (the 3 hero cases) so we can test
  the iMessage flow before the backend is ready.
- When the backend is ready, set LEDGERGUARD_API_URL and fill in
  run_bills_backend() and resolve_backend() below.

Lessons from the ping test
- Do NOT use parentMessageId (shared lines reject threaded replies).
- iPhone capitalizes the first letter, so all matching is lowercase.
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

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
        "backend": os.environ.get("LEDGERGUARD_API_URL"),  # optional
    }


# ---------------------------------------------------------------------------
# LedgerGuard side (mock for now)
# ---------------------------------------------------------------------------

# Actions waiting for the owner's decision: action_id -> description
pending = {}


def run_bills_mock():
    """MOCK DATA. Mirrors the 3 hero cases from the spec. Not real results."""
    results = [
        {"id": "act_adobe", "vendor": "Adobe", "amount": 149, "decision": "ALLOW",
         "reason": "routine payment"},
        {"id": "act_aws", "vendor": "AWS", "amount": 4210, "decision": "BLOCK",
         "reason": "looks like the $4,206 bill recorded 2 days ago"},
        {"id": "act_acme", "vendor": "Acme Supplies", "amount": 18400, "decision": "REQUIRE_APPROVAL",
         "reason": "bank account changed yesterday"},
    ]
    return results


def resolve_mock(action_id, approved):
    """MOCK. Pretends the backend recorded the decision."""
    return {"action_id": action_id, "status": "executed" if approved else "rejected"}


def run_bills_backend(base_url):
    """TODO: call the real backend. Ask Yizhe for the exact request/response schema.
    Expected to return a list like run_bills_mock()."""
    raise NotImplementedError("Backend not connected yet")


def resolve_backend(base_url, action_id, approved):
    """TODO: POST /api/actions/{action_id}/resolve on the real backend."""
    raise NotImplementedError("Backend not connected yet")


def run_bills(c):
    return run_bills_backend(c["backend"]) if c["backend"] else run_bills_mock()


def resolve(c, action_id, approved):
    return resolve_backend(c["backend"], action_id, approved) if c["backend"] else resolve_mock(action_id, approved)


# ---------------------------------------------------------------------------
# Turning LedgerGuard results into iMessage text
# ---------------------------------------------------------------------------

ICONS = {"ALLOW": "✅", "REQUIRE_APPROVAL": "⚠️", "REQUEST_CONTEXT": "❓", "BLOCK": "⛔"}

HELP_TEXT = (
    "Hi, I'm LedgerGuard. I check your agent's payments before money leaves.\n\n"
    "Try:\n"
    "• \"Pay today's bills\"\n"
    "• \"Approve\" or \"Reject\"\n"
    "• \"Status\""
)


def format_results(results):
    lines = ["Here's what happened with today's bills:", ""]
    for r in results:
        icon = ICONS.get(r["decision"], "•")
        if r["decision"] == "ALLOW":
            lines.append(f"{icon} {r['vendor']} ${r['amount']:,} paid ({r['reason']})")
        elif r["decision"] == "BLOCK":
            lines.append(f"{icon} {r['vendor']} ${r['amount']:,} blocked. It {r['reason']}.")
        elif r["decision"] == "REQUIRE_APPROVAL":
            lines.append(f"{icon} {r['vendor']} ${r['amount']:,} is on hold. The {r['reason']}.")
        else:
            lines.append(f"{icon} {r['vendor']} ${r['amount']:,} needs more info. {r['reason']}.")
    if pending:
        lines += ["", "Please confirm with the vendor using a number you trust, then reply APPROVE or REJECT."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deciding what to reply
# ---------------------------------------------------------------------------

def handle(c, text):
    t = text.strip().lower()

    if "pay" in t and "bill" in t:
        results = run_bills(c)
        pending.clear()
        for r in results:
            if r["decision"] in ("REQUIRE_APPROVAL", "REQUEST_CONTEXT"):
                pending[r["id"]] = f"{r['vendor']} ${r['amount']:,}"
        return format_results(results)

    if t in ("approve", "approved", "yes", "y"):
        return decide(c, approved=True)

    if t in ("reject", "rejected", "no", "n"):
        return decide(c, approved=False)

    if t == "status":
        if not pending:
            return "Nothing is waiting for your review."
        items = "\n".join(f"⚠️ {desc}" for desc in pending.values())
        return f"Waiting for your review:\n{items}"

    return HELP_TEXT


def decide(c, approved):
    if not pending:
        return "There's nothing waiting for your approval right now."
    # Hackathon simplification: one pending action at a time.
    action_id, desc = next(iter(pending.items()))
    resolve(c, action_id, approved)
    del pending[action_id]
    if approved:
        return f"Got it. {desc} approved and sent. This decision is logged."
    return f"Got it. {desc} cancelled. This decision is logged."


# ---------------------------------------------------------------------------
# Photon plumbing
# ---------------------------------------------------------------------------

def incoming_text(item, c, started_at):
    """Return the message (and its text) if it is a new direct iMessage from the owner."""
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
    mode = "backend" if c["backend"] else "MOCK data"

    with Photon(headers={"Authorization": f"Bearer {c['key']}"}) as photon:
        print(f"LedgerGuard bot running ({mode}). Text the agent number. Press Ctrl+C to stop.")
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
                        reply = handle(c, text)
                    except Exception as error:  # fail safe: never auto-pay on errors
                        print(f"   handler error: {error}", file=sys.stderr)
                        reply = "Something went wrong, so I paused all payments. Nothing was sent."
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
