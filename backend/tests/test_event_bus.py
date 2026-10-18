import asyncio

import pytest

from backend.app.providers import RulesProvider
from backend.app.services.event_bus import EventBus
from backend.tests.test_api_contract import make_service


@pytest.mark.asyncio
async def test_bounded_queue_drops_oldest_and_disconnect_cleans_up() -> None:
    bus = EventBus(queue_size=2)
    async with bus.subscribe() as queue:
        assert bus.subscriber_count == 1
        await bus.publish({"event_id": 1})
        await bus.publish({"event_id": 2})
        await bus.publish({"event_id": 3})
        assert (await queue.get())["event_id"] == 2
        assert (await queue.get())["event_id"] == 3
    assert bus.subscriber_count == 0


@pytest.mark.asyncio
async def test_provider_started_is_published_before_provider_finishes(
    tmp_path, normalized_store
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowProvider:
        async def evaluate(self, state):
            started.set()
            await release.wait()
            return await RulesProvider().evaluate(state)

    service = make_service(tmp_path, normalized_store)
    service.providers.register("slow", SlowProvider())
    async with service.event_bus.subscribe() as queue:
        task = asyncio.create_task(
            service.run_demo("safe-normal-payment-001", "slow")
        )
        await asyncio.wait_for(started.wait(), timeout=30)
        event_types = []
        while "provider_started" not in event_types:
            event_types.append((await asyncio.wait_for(queue.get(), timeout=5))["type"])
        assert not task.done()
        release.set()
        detail = await asyncio.wait_for(task, timeout=10)
    assert detail["execution_result"]["status"] == "SIMULATED"
