import os

import pytest

from backend.app.models import RiskAssessment
from backend.app.providers.gemini import GeminiBaselineConfig, GeminiBaselineProvider
from backend.tests.test_rules_provider import _state


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_gemini_structured_output_requires_explicit_opt_in() -> None:
    if os.getenv("RUN_GEMINI_LIVE_TESTS") != "1":
        pytest.skip("set RUN_GEMINI_LIVE_TESTS=1 to enable the external Gemini API test")
    config = GeminiBaselineConfig.from_environment()
    if not config.api_key or not config.model:
        pytest.skip("GEMINI/GOOGLE API key and GEMINI_MODEL are not configured")

    async with GeminiBaselineProvider(config) as provider:
        result = await provider.evaluate(_state())

    assert isinstance(result, RiskAssessment), result
    assert result.provider == "gemini"
