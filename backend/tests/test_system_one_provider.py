from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from backend.app.models import (
    AccountingState,
    ActionType,
    BusinessContext,
    HistoricalAmountStats,
    ProposedAction,
    ProviderFailure,
    RiskAssessment,
)
from backend.app.models.risk import ProviderFailureCode
from backend.app.providers.system_one import QUESTION_NAMES, SystemOneConfig, SystemOneProvider


def _state() -> AccountingState:
    action = ProposedAction(
        action_id="a1", action_type=ActionType.PAY_VENDOR_BILL, company_id="company-001",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc), amount=Decimal("100"),
        currency="USD", vendor_id="v1", agent_goal="Pay an approved bill",
    )
    return AccountingState(
        proposed_action=action, candidate_matches=(),
        business_context=BusinessContext(
            company_id="company-001", vendor_transaction_count=0,
            historical_amount_stats=HistoricalAmountStats(observation_count=0),
        ),
        recent_ledger_history=(), deterministic_features={"history_count": 0},
    )


def _valid_response(model: str = "jev-1.14.0") -> dict:
    answer = {
        "type": "score", "score": 1.5, "confidence": 0.8,
        "legend": {"0": "low", "1": "medium", "2": "high"},
        "probabilities": {"0": 0.1, "1": 0.3, "2": 0.6},
    }
    return {
        "model": model,
        "answers": {name: dict(answer) for name in QUESTION_NAMES},
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.typesafe.ai",
        headers={"Authorization": "Bearer test-key"},
    )


@pytest.mark.asyncio
async def test_discovers_model_then_maps_all_five_score_answers() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"models": [{"name": "jev-1.14.0"}]})
        return httpx.Response(200, json=_valid_response())

    client = _client(handler)
    provider = SystemOneProvider(SystemOneConfig(api_key="test-key", max_retries=0), client=client)
    result = await provider.evaluate(_state())
    assert isinstance(result, RiskAssessment)
    assert result.model_name == "jev-1.14.0"
    assert result.goal_alignment_probability == 0.75
    assert result.action_anomaly_confidence == 0.8
    assert result.latency_ms >= 0
    body = requests[1].content.decode()
    assert set(provider.build_request(_state(), "jev-1.14.0")["questions"]) == set(QUESTION_NAMES)
    assert "policy_threshold" not in body and "final_action" not in body
    assert "sim_" not in body and "provenance_note" not in body
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["answers"].pop("missing_context"),
        lambda payload: payload["answers"]["action_anomaly"].update(score=3),
        lambda payload: payload["answers"]["goal_alignment"].update(confidence="high"),
        lambda payload: payload["answers"]["goal_alignment"]["probabilities"].update({"2": 1.5}),
    ],
)
async def test_malformed_responses_fail_closed(mutate) -> None:
    payload = _valid_response()
    mutate(payload)
    client = _client(lambda request: httpx.Response(200, json=payload))
    provider = SystemOneProvider(
        SystemOneConfig(api_key="test", model="jev-1.14.0", max_retries=0), client=client
    )
    provider._model_name = "jev-1.14.0"
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.INVALID_RESPONSE
    assert result.outcome == "failure"
    await client.aclose()


@pytest.mark.asyncio
async def test_non_json_success_response_is_invalid() -> None:
    client = _client(lambda request: httpx.Response(200, text="not-json"))
    provider = SystemOneProvider(
        SystemOneConfig(api_key="test", model="jev-1.14.0", max_retries=0), client=client
    )
    provider._model_name = "jev-1.14.0"
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_retry_exhaustion_returns_typed_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"error": "temporary"})

    client = _client(handler)
    provider = SystemOneProvider(
        SystemOneConfig(api_key="test", model="jev-1.14.0", max_retries=2), client=client
    )
    provider._model_name = "jev-1.14.0"
    result = await provider.evaluate(_state())
    assert attempts == 3
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.UNAVAILABLE
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (401, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (403, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (422, ProviderFailureCode.INVALID_REQUEST, False),
        (429, ProviderFailureCode.RATE_LIMITED, True),
        (503, ProviderFailureCode.UNAVAILABLE, True),
    ],
)
async def test_http_failures_are_typed(status, code, retryable) -> None:
    client = _client(lambda request: httpx.Response(status, json={"error": "test"}))
    provider = SystemOneProvider(
        SystemOneConfig(api_key="test", model="jev-1.14.0", max_retries=0), client=client
    )
    provider._model_name = "jev-1.14.0"
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert (result.code, result.retryable) == (code, retryable)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (httpx.ReadTimeout("slow"), ProviderFailureCode.TIMEOUT),
        (httpx.ConnectError("offline"), ProviderFailureCode.UNAVAILABLE),
    ],
)
async def test_transport_failures_are_typed(exception, code) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    client = _client(handler)
    provider = SystemOneProvider(
        SystemOneConfig(api_key="test", model="jev-1.14.0", max_retries=0), client=client
    )
    provider._model_name = "jev-1.14.0"
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure) and result.code is code
    assert str(exception) not in result.message
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_key_and_empty_discovery_are_failures() -> None:
    no_key = SystemOneProvider(SystemOneConfig(api_key=None, max_retries=0))
    result = await no_key.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.CONFIGURATION_ERROR
    client = _client(lambda request: httpx.Response(200, json={"models": []}))
    provider = SystemOneProvider(SystemOneConfig(api_key="test", max_retries=0), client=client)
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.MODEL_DISCOVERY_ERROR
    await client.aclose()
