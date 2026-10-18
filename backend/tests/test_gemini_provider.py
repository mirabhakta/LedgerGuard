import json

import httpx
import pytest

from backend.app.models import ProviderFailure, RiskAssessment
from backend.app.models.risk import ProviderFailureCode
from backend.app.providers.gemini import GeminiBaselineConfig, GeminiBaselineProvider
from backend.tests.test_rules_provider import _state


def _signals(**changes):
    values = {
        "goal_alignment_probability": 0.9,
        "goal_alignment_confidence": 0.8,
        "duplicate_obligation_probability": 0.1,
        "duplicate_obligation_confidence": 0.8,
        "counterparty_change_score": 0.1,
        "counterparty_change_confidence": 0.8,
        "missing_context_probability": 0.1,
        "missing_context_confidence": 0.8,
        "action_anomaly_score": 0.1,
        "action_anomaly_confidence": 0.8,
    }
    values.update(changes)
    return values


def _response(signals=None, *, finish_reason="STOP"):
    return {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps(signals or _signals())}]},
            "finishReason": finish_reason,
        }],
        "modelVersion": "gemini-test-version",
    }


@pytest.mark.asyncio
async def test_gemini_uses_generate_content_structured_output_contract() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_response())

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiBaselineProvider(
        GeminiBaselineConfig(api_key="test-key", model="models/gemini-test"), client=client
    )
    result = await provider.evaluate(_state())

    assert isinstance(result, RiskAssessment)
    assert result.provider == "gemini"
    assert result.model_name == "gemini-test-version"
    request = seen[0]
    assert request.url.path == "/v1beta/models/gemini-test:generateContent"
    assert request.headers["x-goog-api-key"] == "test-key"
    body = json.loads(request.content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"]["additionalProperties"] is False
    assert body["contents"][0]["role"] == "user"
    serialized = json.dumps(body)
    assert "final_action" not in serialized and "policy_threshold" not in serialized
    assert "sim_" not in serialized and "provenance_note" not in serialized
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        _response(_signals(action_anomaly_score=2)),
        _response(finish_reason="MAX_TOKENS"),
        {"promptFeedback": {"blockReason": "SAFETY"}},
        {"candidates": []},
        {"candidates": [{"content": {"parts": [{}]}, "finishReason": "STOP"}]},
    ],
)
async def test_invalid_gemini_output_fails_closed(payload) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiBaselineProvider(
        GeminiBaselineConfig(api_key="test", model="gemini-test"), client=client
    )
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (400, ProviderFailureCode.INVALID_REQUEST, False),
        (401, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (403, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (408, ProviderFailureCode.TIMEOUT, True),
        (429, ProviderFailureCode.RATE_LIMITED, True),
        (500, ProviderFailureCode.UNAVAILABLE, True),
    ],
)
async def test_gemini_http_errors_are_typed(status, code, retryable) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status)),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiBaselineProvider(
        GeminiBaselineConfig(api_key="test", model="gemini-test"), client=client
    )
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is code
    assert result.retryable is retryable
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_gemini_configuration_fails_closed() -> None:
    result = await GeminiBaselineProvider(GeminiBaselineConfig()).evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.CONFIGURATION_ERROR


@pytest.mark.asyncio
async def test_malformed_gemini_model_name_fails_closed_without_network() -> None:
    result = await GeminiBaselineProvider(
        GeminiBaselineConfig(api_key="test", model="models/")
    ).evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.CONFIGURATION_ERROR


def test_google_api_key_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    config = GeminiBaselineConfig.from_environment()
    assert config.api_key == "google-key"
    assert config.model == "gemini-test"


@pytest.mark.asyncio
async def test_transport_error_details_are_not_persisted_in_gemini_failure() -> None:
    secret = "secret-transport-detail"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(secret, request=request)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiBaselineProvider(
        GeminiBaselineConfig(api_key="test", model="gemini-test"), client=client
    )
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.UNAVAILABLE
    assert secret not in result.message
    await client.aclose()


@pytest.mark.asyncio
async def test_default_fastapi_service_registers_gemini_not_legacy_llm(
    monkeypatch, tmp_path
) -> None:
    from backend.app.main import build_default_service

    monkeypatch.setenv("LEDGERGUARD_DB_PATH", str(tmp_path / "audit.sqlite3"))
    service = build_default_service()
    try:
        assert service.providers.names == ("gemini", "openjev", "rules", "system_one")
    finally:
        await service.aclose()
