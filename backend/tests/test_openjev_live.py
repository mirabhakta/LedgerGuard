import os

import pytest

from backend.app.models.risk import ProviderFailure
from backend.app.providers.openjev import OpenJevConfig, OpenJevProvider
from backend.tests.test_openjev_provider import _state


@pytest.mark.live
@pytest.mark.asyncio
async def test_local_openjev_end_to_end_requires_explicit_opt_in() -> None:
    if os.getenv("RUN_OPENJEV_LIVE_TESTS") != "1":
        pytest.skip("set RUN_OPENJEV_LIVE_TESTS=1 to enable the local model test")

    async with OpenJevProvider(OpenJevConfig.from_environment()) as provider:
        result = await provider.evaluate(_state())

    assert not isinstance(result, ProviderFailure), result
    assert result.provider == "openjev"
    assert result.model_name.startswith("openjev/")
