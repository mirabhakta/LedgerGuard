"""Black-box smoke test for a running LedgerGuard FastAPI server."""

from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

import httpx


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    timeout = httpx.Timeout(45)

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        health = await client.get("/api/health")
        health.raise_for_status()
        assert health.json()["status"] == "ok"

        schema = (await client.get("/openapi.json")).json()
        assert schema["paths"]["/api/demo/run"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]["$ref"].endswith("/ActionDetailResponse")

        preflight = await client.options(
            "/api/demo/run",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"

        idempotency_key = f"smoke-{uuid4().hex}"
        safe = await _run(client, "safe-normal-payment-001", idempotency_key)
        assert safe["policy_decision"]["final_action"] == "ALLOW"
        assert safe["execution_result"]["status"] == "SIMULATED"
        assert safe["execution_authorization"]["authorization_type"] == "POLICY_ALLOW"
        replay = await _run(client, "safe-normal-payment-001", idempotency_key)
        assert replay["action_id"] == safe["action_id"]

        review = await _run(client, "destination-change-001")
        assert review["policy_decision"]["final_action"] == "REQUIRE_APPROVAL"
        assert review["execution_result"] is None
        stale = await client.post(
            f"/api/actions/{review['action_id']}/resolve",
            json={
                "resolution": "approve",
                "actor": "smoke@example.com",
                "assessment_hash": "stale",
            },
        )
        assert stale.status_code == 409 and stale.json()["code"] == "STALE_REVIEW_RESPONSE"
        approved = (
            await client.post(
                f"/api/actions/{review['action_id']}/resolve",
                json={
                    "resolution": "approve",
                    "actor": "smoke@example.com",
                    "assessment_hash": review["policy_decision"]["assessment_hash"],
                },
            )
        ).json()
        assert approved["execution_result"]["status"] == "SIMULATED"
        assert approved["execution_authorization"]["authorization_type"] == "HUMAN_APPROVAL"

        blocked = await _run(client, "semantic-duplicate-001")
        assert blocked["policy_decision"]["final_action"] == "BLOCK"
        assert blocked["execution_result"] is None
        assert blocked["execution_authorization"] is None

        context = await _run(client, "missing-context-001")
        assert context["policy_decision"]["final_action"] == "REQUEST_CONTEXT"
        supplied = (
            await client.post(
                f"/api/actions/{context['action_id']}/resolve",
                json={
                    "resolution": "provide_context",
                    "actor": "smoke@example.com",
                    "updates": {"vendor_id": "vend-supplier"},
                    "provenance": "smoke test fixture",
                },
            )
        ).json()
        assert supplied["execution_result"]["status"] == "SIMULATED"

        last_seen = blocked["audit_events"][0]["event_id"]
        stream = await client.get(
            "/api/stream",
            params={"once": "true"},
            headers={"Last-Event-ID": str(last_seen)},
        )
        assert stream.status_code == 200
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert f"id: {last_seen}\n" not in stream.text

        listing = (await client.get("/api/actions", params={"limit": 2})).json()
        assert listing["count"] <= 2 and listing["total"] >= 4
        dashboard = (await client.get("/api/dashboard")).json()
        assert dashboard["processed"] >= 4

    print(
        "PASS: health, OpenAPI, CORS, ALLOW/idempotency, review/stale guard, "
        "BLOCK, context resume, SSE replay, pagination, and dashboard"
    )


async def _run(
    client: httpx.AsyncClient, scenario_id: str, idempotency_key: str | None = None
) -> dict:
    payload = {"scenario_id": scenario_id, "provider": "rules"}
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    response = await client.post("/api/demo/run", json=payload)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    asyncio.run(main())
