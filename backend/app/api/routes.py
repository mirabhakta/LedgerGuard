"""REST and SSE routes with no embedded financial policy."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable

from fastapi import APIRouter, Header, Query, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from backend.app.services.application import LedgerGuardApplication

from .models import (
    ActionDetailResponse,
    ActionListResponse,
    BenchmarksResponse,
    DashboardResponse,
    DemoRunRequest,
    ErrorResponse,
    HealthResponse,
    ResolveRequest,
)


def build_router(service: LedgerGuardApplication) -> APIRouter:
    router = APIRouter(
        prefix="/api",
        responses={
            404: {"model": ErrorResponse, "description": "Resource not found"},
            409: {"model": ErrorResponse, "description": "State or idempotency conflict"},
            422: {"model": ErrorResponse, "description": "Request validation failed"},
            500: {"model": ErrorResponse, "description": "Safe internal failure"},
        },
    )

    @router.get("/health", response_model=HealthResponse)
    async def health() -> dict:
        return {
            "status": "ok",
            "providers": service.providers.names,
            "scenario_count": len(service.scenarios),
        }

    @router.get("/actions", response_model=ActionListResponse)
    async def actions(
        final_action: str | None = None,
        reason_code: str | None = None,
        provider: str | None = None,
        scenario: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        items = service.list_actions(
            final_action=final_action, reason_code=reason_code, provider=provider,
            scenario=scenario, limit=limit, offset=offset,
        )
        total = service.repository.count_actions(
            final_action=final_action, reason_code=reason_code, provider=provider,
            scenario=scenario,
        )
        return {
            "items": items, "limit": limit, "offset": offset,
            "count": len(items), "total": total,
        }

    @router.get("/actions/{action_id}", response_model=ActionDetailResponse)
    async def action_detail(action_id: str) -> dict:
        return service.get_action(action_id)

    @router.post("/actions/{action_id}/resolve", response_model=ActionDetailResponse)
    async def resolve(action_id: str, body: ResolveRequest) -> dict:
        return await service.resolve(action_id, **body.model_dump())

    @router.post("/demo/run", response_model=ActionDetailResponse)
    async def demo_run(body: DemoRunRequest) -> dict:
        return await service.run_demo(
            body.scenario_id, body.provider, idempotency_key=body.idempotency_key
        )

    @router.get("/benchmarks", response_model=BenchmarksResponse)
    async def benchmarks() -> dict:
        return service.benchmarks()

    @router.get("/dashboard", response_model=DashboardResponse)
    async def dashboard() -> dict:
        return service.repository.dashboard()

    @router.get("/stream", response_class=EventSourceResponse)
    async def stream(
        request: Request,
        last_event_id: int | None = Query(default=None, ge=0),
        last_event_id_header: int | None = Header(
            default=None, alias="Last-Event-ID", ge=0
        ),
        once: bool = False,
    ) -> AsyncIterable[ServerSentEvent]:
        cursor = last_event_id if last_event_id is not None else (last_event_id_header or 0)

        async def replay_persisted() -> AsyncIterable[ServerSentEvent]:
            nonlocal cursor
            while True:
                batch = service.repository.events_after(cursor, limit=100)
                for event in batch:
                    cursor = event["event_id"]
                    yield _sse(event)
                if len(batch) < 100:
                    break

        if once:
            replayed = 0
            async for event in replay_persisted():
                replayed += 1
                yield event
            if replayed == 0:
                yield ServerSentEvent(comment="heartbeat")
            return

        # Subscribe before replay so events committed during replay cannot fall into a gap.
        async with service.event_bus.subscribe() as queue:
            async for event in replay_persisted():
                yield event
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ServerSentEvent(comment="heartbeat")
                    continue
                if event["event_id"] > cursor:
                    cursor = event["event_id"]
                    yield _sse(event)

    return router


def _sse(event: dict) -> ServerSentEvent:
    return ServerSentEvent(
        id=str(event["event_id"]), event=event["type"],
        data={
            "event_id": event["event_id"], "action_id": event["action_id"],
            "audit_id": event["audit_id"], "type": event["type"],
            "timestamp": event["created_at"], "schema_version": event["schema_version"],
            "payload": event["payload"],
        },
    )
