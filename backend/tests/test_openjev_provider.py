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
from backend.app.providers.openjev import OpenJevConfig, OpenJevProvider
from backend.app.providers.system_one_questions import QUESTION_NAMES


MODEL_ID = "Qwen/Qwen3-0.6B"


def _state() -> AccountingState:
    action = ProposedAction(
        action_id="openjev-a1",
        action_type=ActionType.PAY_VENDOR_BILL,
        company_id="company-001",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        amount=Decimal("100"),
        currency="USD",
        vendor_id="v1",
        agent_goal="Pay an approved bill",
    )
    return AccountingState(
        proposed_action=action,
        candidate_matches=(),
        business_context=BusinessContext(
            company_id="company-001",
            vendor_transaction_count=0,
            historical_amount_stats=HistoricalAmountStats(observation_count=0),
        ),
        recent_ledger_history=(),
        deterministic_features={"history_count": 0},
    )


def _valid_response(model: str = f"openjev/{MODEL_ID}") -> dict:
    answer = {
        "type": "score",
        "score": 1.5,
        "confidence": 0.8,
        "legend": ["low", "medium", "high"],
        "probabilities": {"0": 0.1, "1": 0.3, "2": 0.6},
    }
    return {
        "model": model,
        "answers": {name: dict(answer) for name in QUESTION_NAMES},
        "usage": {"forward_passes": 5, "input_tokens": 100, "latency_ms_total": 20},
    }


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:8771"
    )


@pytest.mark.asyncio
async def test_health_discovery_then_maps_five_scores_without_policy_leakage() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/health":
            return httpx.Response(
                200,
                json={"status": "ok", "engine_loaded": False, "model_id": MODEL_ID},
            )
        return httpx.Response(200, json=_valid_response())

    client = _client(handler)
    provider = OpenJevProvider(OpenJevConfig(expected_model=MODEL_ID), client=client)
    result = await provider.evaluate(_state())

    assert isinstance(result, RiskAssessment)
    assert result.provider == "openjev"
    assert result.model_name == f"openjev/{MODEL_ID}"
    assert result.goal_alignment_probability == 0.75
    assert result.action_anomaly_confidence == 0.8
    assert [request.url.path for request in requests] == ["/health", "/v1/systemone"]
    body = requests[1].content.decode()
    assert '"model"' not in body
    assert "policy_threshold" not in body and "final_action" not in body
    assert "sim_" not in body and "provenance_note" not in body
    assert set(provider.build_request(_state())["questions"]) == set(QUESTION_NAMES)
    await client.aclose()


@pytest.mark.asyncio
async def test_optional_reverse_proxy_bearer_header_is_configured() -> None:
    provider = OpenJevProvider(OpenJevConfig(api_key="proxy-secret"))
    client = provider._get_client()
    assert client.headers["Authorization"] == "Bearer proxy-secret"
    await provider.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["answers"].pop("missing_context"),
        lambda payload: payload["answers"].update(unexpected=payload["answers"]["missing_context"]),
        lambda payload: payload["answers"]["action_anomaly"].update(score=3),
        lambda payload: payload["answers"]["goal_alignment"].update(legend=["low", "high"]),
        lambda payload: payload["answers"]["goal_alignment"].update(
            probabilities={"0": 0.2, "1": 0.2, "2": 0.2}
        ),
        lambda payload: payload.update(model="openjev/other/model"),
    ],
)
async def test_malformed_or_drifted_responses_fail_closed(mutate) -> None:
    payload = _valid_response()
    mutate(payload)
    client = _client(lambda request: httpx.Response(200, json=payload))
    provider = OpenJevProvider(client=client)
    provider._model_name = MODEL_ID
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_expected_model_mismatch_fails_discovery() -> None:
    client = _client(
        lambda request: httpx.Response(
            200, json={"status": "ok", "engine_loaded": True, "model_id": "other/model"}
        )
    )
    provider = OpenJevProvider(OpenJevConfig(expected_model=MODEL_ID), client=client)
    result = await provider.discover_model()
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.MODEL_DISCOVERY_ERROR
    await client.aclose()


@pytest.mark.asyncio
async def test_non_json_success_response_is_invalid() -> None:
    client = _client(lambda request: httpx.Response(200, text="not-json"))
    provider = OpenJevProvider(client=client)
    provider._model_name = MODEL_ID
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert result.code is ProviderFailureCode.INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (401, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (403, ProviderFailureCode.AUTHENTICATION_ERROR, False),
        (408, ProviderFailureCode.TIMEOUT, True),
        (422, ProviderFailureCode.INVALID_REQUEST, False),
        (429, ProviderFailureCode.RATE_LIMITED, True),
        (503, ProviderFailureCode.UNAVAILABLE, True),
    ],
)
async def test_http_failures_are_typed(status, code, retryable) -> None:
    client = _client(lambda request: httpx.Response(status, json={"error": "test"}))
    provider = OpenJevProvider(OpenJevConfig(max_retries=0), client=client)
    provider._model_name = MODEL_ID
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure)
    assert (result.code, result.retryable) == (code, retryable)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (httpx.ReadTimeout("secret-timeout-detail"), ProviderFailureCode.TIMEOUT),
        (httpx.ConnectError("secret-network-detail"), ProviderFailureCode.UNAVAILABLE),
    ],
)
async def test_transport_failures_are_typed_and_sanitized(exception, code) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    client = _client(handler)
    provider = OpenJevProvider(OpenJevConfig(max_retries=0), client=client)
    provider._model_name = MODEL_ID
    result = await provider.evaluate(_state())
    assert isinstance(result, ProviderFailure) and result.code is code
    assert str(exception) not in result.message
    await client.aclose()


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "warming up"})
        return httpx.Response(200, json=_valid_response())

    client = _client(handler)
    provider = OpenJevProvider(OpenJevConfig(max_retries=1), client=client)
    provider._model_name = MODEL_ID
    result = await provider.evaluate(_state())
    assert attempts == 2
    assert isinstance(result, RiskAssessment)
    await client.aclose()
