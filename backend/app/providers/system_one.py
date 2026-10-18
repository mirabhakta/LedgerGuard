"""Typed adapter for the TypeSafe System One API."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.app.models.risk import (
    ProviderFailure,
    ProviderFailureCode,
    ProviderOutcome,
    RiskAssessment,
)
from backend.app.models.state import AccountingState
from backend.app.providers.system_one_questions import QUESTION_NAMES, build_system_one_questions


class SystemOneConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str | None = None
    base_url: str = "https://api.typesafe.ai"
    model: str | None = None
    connect_timeout_seconds: float = Field(default=2.0, gt=0)
    read_timeout_seconds: float = Field(default=5.0, gt=0)
    write_timeout_seconds: float = Field(default=5.0, gt=0)
    pool_timeout_seconds: float = Field(default=2.0, gt=0)
    max_retries: int = Field(default=1, ge=0, le=3)

    @classmethod
    def from_environment(cls) -> "SystemOneConfig":
        return cls(
            api_key=os.getenv("TYPESAFE_API_KEY"),
            base_url=os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai"),
            model=os.getenv("TYPESAFE_MODEL"),
        )


class _ScoreAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["score"]
    score: float = Field(ge=0, le=2)
    confidence: float = Field(ge=0, le=1)
    legend: dict[str, Any]
    probabilities: dict[str, Annotated[float, Field(ge=0, le=1)]]

    @model_validator(mode="after")
    def validate_probability_distribution(self) -> "_ScoreAnswer":
        if set(self.legend) != set(self.probabilities):
            raise ValueError("legend and probability levels must match")
        if not 0.99 <= sum(self.probabilities.values()) <= 1.01:
            raise ValueError("score probabilities must sum approximately to one")
        return self


class _SystemOneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    answers: dict[str, _ScoreAnswer]
    usage: dict[str, int]


class SystemOneProvider:
    name = "system_one"

    def __init__(
        self,
        config: SystemOneConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or SystemOneConfig.from_environment()
        self._client = client
        self._owns_client = client is None
        self._model_name: str | None = None

    async def __aenter__(self) -> "SystemOneProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def build_request(self, state: AccountingState, model_name: str) -> dict[str, Any]:
        return {
            "model": model_name,
            "state": state.inference_view(),
            "questions": build_system_one_questions(),
        }

    async def discover_model(self) -> str | ProviderFailure:
        started = time.monotonic()
        if not self.config.api_key:
            return self._failure(
                ProviderFailureCode.CONFIGURATION_ERROR,
                "TYPESAFE_API_KEY is not configured",
                False,
                started,
            )
        response = await self._request("GET", "/v1/models", started=started)
        if isinstance(response, ProviderFailure):
            return response
        try:
            payload = _json_body(response)
            models = payload["models"]
            names = [item["name"] for item in models if isinstance(item, dict)]
            if not names or not all(isinstance(name, str) and name for name in names):
                raise ValueError("models must contain non-empty names")
            selected = self.config.model or names[0]
            if selected not in names:
                raise ValueError(f"configured model {selected!r} is unavailable")
        except (ValueError, KeyError, TypeError) as exc:
            return self._failure(
                ProviderFailureCode.MODEL_DISCOVERY_ERROR,
                f"invalid model discovery response: {exc}",
                False,
                started,
            )
        self._model_name = selected
        return selected

    async def evaluate(self, state: AccountingState) -> ProviderOutcome:
        started = time.monotonic()
        model_name = self._model_name
        if model_name is None:
            discovered = await self.discover_model()
            if isinstance(discovered, ProviderFailure):
                return discovered.model_copy(update={"latency_ms": _elapsed_ms(started)})
            model_name = discovered
        response = await self._request(
            "POST", "/v1/systemone", started=started,
            json=self.build_request(state, model_name),
        )
        if isinstance(response, ProviderFailure):
            return response.model_copy(update={"model_name": model_name})
        try:
            return self._parse_response(_json_body(response), latency_ms=_elapsed_ms(started))
        except (ValueError, TypeError, ValidationError) as exc:
            return self._failure(
                ProviderFailureCode.INVALID_RESPONSE,
                f"invalid System One response: {exc}",
                False,
                started,
                model_name=model_name,
            )

    def _parse_response(self, payload: Any, *, latency_ms: float) -> RiskAssessment:
        parsed = _SystemOneResponse.model_validate(payload)
        if set(parsed.answers) != set(QUESTION_NAMES):
            missing = sorted(set(QUESTION_NAMES) - set(parsed.answers))
            extra = sorted(set(parsed.answers) - set(QUESTION_NAMES))
            raise ValueError(f"answer names differ; missing={missing}, extra={extra}")
        values = parsed.answers
        return RiskAssessment(
            goal_alignment_probability=values["goal_alignment"].score / 2,
            goal_alignment_confidence=values["goal_alignment"].confidence,
            duplicate_obligation_probability=values["duplicate_obligation_risk"].score / 2,
            duplicate_obligation_confidence=values["duplicate_obligation_risk"].confidence,
            counterparty_change_score=values["counterparty_change_risk"].score / 2,
            counterparty_change_confidence=values["counterparty_change_risk"].confidence,
            missing_context_probability=values["missing_context"].score / 2,
            missing_context_confidence=values["missing_context"].confidence,
            action_anomaly_score=values["action_anomaly"].score / 2,
            action_anomaly_confidence=values["action_anomaly"].confidence,
            provider=self.name,
            model_name=parsed.model,
            latency_ms=latency_ms,
        )

    async def _request(
        self, method: str, path: str, *, started: float, json: Any = None
    ) -> httpx.Response | ProviderFailure:
        client = self._get_client()
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.request(method, path, json=json)
            except httpx.TimeoutException:
                failure = self._failure(
                    ProviderFailureCode.TIMEOUT, "TypeSafe request timed out", True, started
                )
            except httpx.RequestError:
                failure = self._failure(
                    ProviderFailureCode.UNAVAILABLE, "TypeSafe transport unavailable", True, started
                )
            else:
                failure = self._status_failure(response, started)
                if failure is None:
                    return response
            if not failure.retryable or attempt >= self.config.max_retries:
                return failure
            await asyncio.sleep(0.05 * (2**attempt))
        raise AssertionError("unreachable")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                connect=self.config.connect_timeout_seconds,
                read=self.config.read_timeout_seconds,
                write=self.config.write_timeout_seconds,
                pool=self.config.pool_timeout_seconds,
            )
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=timeout,
            )
        return self._client

    def _status_failure(
        self, response: httpx.Response, started: float
    ) -> ProviderFailure | None:
        if 200 <= response.status_code < 300:
            return None
        if response.status_code in (401, 403):
            code, retryable = ProviderFailureCode.AUTHENTICATION_ERROR, False
        elif response.status_code == 429:
            code, retryable = ProviderFailureCode.RATE_LIMITED, True
        elif response.status_code >= 500:
            code, retryable = ProviderFailureCode.UNAVAILABLE, True
        else:
            code, retryable = ProviderFailureCode.INVALID_REQUEST, False
        return self._failure(
            code, f"TypeSafe returned HTTP {response.status_code}", retryable, started
        )

    def _failure(
        self,
        code: ProviderFailureCode,
        message: str,
        retryable: bool,
        started: float,
        *,
        model_name: str | None = None,
    ) -> ProviderFailure:
        return ProviderFailure(
            provider=self.name, code=code, message=message, retryable=retryable,
            latency_ms=_elapsed_ms(started), model_name=model_name,
        )


def _elapsed_ms(started: float) -> float:
    return max(0.0, (time.monotonic() - started) * 1000)


def _json_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        raise ValueError(f"expected application/json response, got {content_type or 'missing'}")
    return response.json()
