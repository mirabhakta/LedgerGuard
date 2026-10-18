import json

import httpx
import pytest

from backend.app.models.action import FinalAction
from backend.app.models.policy import PrecheckResult
from backend.app.policy.config import PolicyConfig
from backend.app.policy.engine import PolicyEngine
from backend.app.providers.llm import LLMBaselineProvider, ProviderUnavailable
from backend.app.providers.questions import SIGNAL_NAMES
from backend.tests.factories import make_state

VALID = {name: {"value": 0.1, "confidence": 0.9} for name in SIGNAL_NAMES}


def provider_with(handler) -> LLMBaselineProvider:
    return LLMBaselineProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        api_key="k",
        transport=httpx.MockTransport(handler),
    )


def completion(content: str, usage=None) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}], "usage": usage or {}})


async def test_valid_response_parses():
    seen = {}

    def handler(request: httpx.Request):
        seen["body"] = json.loads(request.content)
        return completion(json.dumps(VALID), usage={"prompt_tokens": 900, "completion_tokens": 80})

    provider = provider_with(handler)
    a = await provider.evaluate(make_state())
    assert not a.had_error
    assert a.model_name == "llm:test-model"
    assert a.duplicate_obligation_risk.value == 0.1
    assert provider.last_usage["prompt_tokens"] == 900
    assert seen["body"]["temperature"] == 0
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert "scenario_id" not in seen["body"]["messages"][1]["content"]


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({k: v for k, v in VALID.items() if k != "missing_context_risk"}),
        json.dumps({**VALID, "duplicate_obligation_risk": {"value": 1.7, "confidence": 0.9}}),
        json.dumps({**VALID, "goal_misalignment_risk": {"value": 0.2}}),
    ],
    ids=["not_json", "missing_signal", "out_of_range", "missing_confidence"],
)
async def test_malformed_response_fails_safe(content):
    provider = provider_with(lambda request: completion(content))
    a = await provider.evaluate(make_state())
    assert a.had_error and a.used_fallback
    assert a.error_code == "MALFORMED_RESPONSE"
    assert provider.last_attempts == 2

    decision = PolicyEngine().decide(
        state=make_state(), assessment=a, precheck_result=PrecheckResult(), config=PolicyConfig()
    )
    assert decision.final_action == FinalAction.REQUIRE_APPROVAL
    assert decision.fail_safe_triggered


async def test_http_error_fails_safe():
    provider = provider_with(lambda request: httpx.Response(503, text="overloaded"))
    a = await provider.evaluate(make_state())
    assert a.had_error and a.error_code == "HTTP_503"


async def test_timeout_fails_safe():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    a = await provider_with(handler).evaluate(make_state())
    assert a.had_error and a.error_code == "TIMEOUT"


async def test_retry_recovers_after_one_bad_response():
    calls = iter([completion("garbage"), completion(json.dumps(VALID))])
    provider = provider_with(lambda request: next(calls))
    a = await provider.evaluate(make_state())
    assert not a.had_error and provider.last_attempts == 2


def test_from_env_requires_configuration(monkeypatch):
    for key in ("LLM_BASELINE_BASE_URL", "LLM_BASELINE_MODEL", "LLM_BASELINE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ProviderUnavailable):
        LLMBaselineProvider.from_env()
