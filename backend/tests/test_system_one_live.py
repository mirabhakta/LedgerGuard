import os

import pytest

from backend.app.providers.system_one import SystemOneConfig, SystemOneProvider


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_model_discovery_requires_explicit_opt_in() -> None:
    if os.getenv("RUN_TYPESAFE_LIVE_TESTS") != "1":
        pytest.skip("set RUN_TYPESAFE_LIVE_TESTS=1 to enable external API tests")
    if not os.getenv("TYPESAFE_API_KEY"):
        pytest.skip("TYPESAFE_API_KEY is not configured")
    async with SystemOneProvider(SystemOneConfig.from_environment()) as provider:
        discovered = await provider.discover_model()
    assert isinstance(discovered, str) and discovered
