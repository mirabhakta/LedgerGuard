import os

import httpx
import pytest

from backend.app.main import build_default_service, create_app
from backend.app.providers.gemini import GeminiBaselineConfig


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_gemini_through_fastapi_pipeline(monkeypatch, tmp_path) -> None:
    if os.getenv("RUN_GEMINI_LIVE_TESTS") != "1":
        pytest.skip("set RUN_GEMINI_LIVE_TESTS=1 to enable the external Gemini API test")
    config = GeminiBaselineConfig.from_environment()
    if not config.api_key or not config.model:
        pytest.skip("GEMINI/GOOGLE API key and GEMINI_MODEL are not configured")

    monkeypatch.setenv("LEDGERGUARD_DB_PATH", str(tmp_path / "audit.sqlite3"))
    service = build_default_service()
    app = create_app(service)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/demo/run",
                json={
                    "scenario_id": "safe-normal-payment-001",
                    "provider": "gemini",
                    "idempotency_key": "gemini-fastapi-live-001",
                },
                timeout=60,
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["provider"] == "gemini"
        assert body["provider_outcome"]["outcome"] == "success"
        assert body["provider_outcome"]["provider"] == "gemini"
        assert body["policy_decision"]["final_action"] in {
            "ALLOW", "REQUIRE_APPROVAL", "REQUEST_CONTEXT", "BLOCK"
        }
    finally:
        await service.aclose()
