"""Adapter for a locally hosted OpenJev System One-style server.

OpenJev is an independent masked-logit implementation, not the official TypeSafe
Jev model. Keeping a distinct provider identity prevents benchmark provenance from
being conflated.
"""

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


class OpenJevConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "http://127.0.0.1:8771"
    expected_model: str | None = None
    api_key: str | None = None
    connect_timeout_seconds: float = Field(default=2.0, gt=0)
    read_timeout_seconds: float = Field(default=120.0, gt=0)
    write_timeout_seconds: float = Field(default=10.0, gt=0)
    pool_timeout_seconds: float = Field(default=2.0, gt=0)
    max_retries: int = Field(default=0, ge=0, le=2)

    @classmethod
    def from_environment(cls) -> "OpenJevConfig":
        return cls(
            base_url=os.getenv("OPENJEV_BASE_URL", "http://127.0.0.1:8771"),
            expected_model=os.getenv("OPENJEV_MODEL"),
            api_key=os.getenv("OPENJEV_API_KEY"),
        )


class _OpenJevHealth(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["ok"]
    engine_loaded: bool
    model_id: str = Field(min_length=1)


class _OpenJevScoreAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["score"]
    score: float = Field(ge=0, le=2)
    confidence: float = Field(ge=0, le=1)
    legend: list[str]
    probabilities: dict[str, Annotated[float, Field(ge=0, le=1)]]

    @model_validator(mode="after")
    def validate_three_level_distribution(self) -> "_OpenJevScoreAnswer":
        if len(self.legend) != 3 or any(not item.strip() for item in self.legend):
            raise ValueError("OpenJev score legend must contain three non-empty levels")
        if set(self.probabilities) != {"0", "1", "2"}:
            raise ValueError("OpenJev score probabilities must contain levels 0, 1, and 2")
        if not 0.99 <= sum(self.probabilities.values()) <= 1.01:
            raise ValueError("OpenJev score probabilities must sum approximately to one")
        return self


class _OpenJevResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    answers: dict[str, _OpenJevScoreAnswer]
    usage: dict[str, Any]


class OpenJevProvider:
    name = "openjev"

    def __init__(
        self,
        config: OpenJevConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or OpenJevConfig.from_environment()
        self._client = client
        self._owns_client = client is None
        self._model_name: str | None = None

    async def __aenter__(self) -> "OpenJevProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def build_request(self, state: AccountingState) -> dict[str, Any]:
        return {
            "state": state.inference_view(),
            "questions": build_system_one_questions(),
        }

    async def discover_model(self) -> str | ProviderFailure:
        started = time.monotonic()
        response = await self._request("GET", "/health", started=started)
        if isinstance(response, ProviderFailure):
            return response
        try:
            health = _OpenJevHealth.model_validate(_json_body(response))
            if self.config.expected_model and health.model_id != self.config.expected_model:
                raise ValueError(
                    f"server model {health.model_id!r} does not match configured model "
                    f"{self.config.expected_model!r}"
                )
        except (ValueError, TypeError, ValidationError) as exc:
            return self._failure(
                ProviderFailureCode.MODEL_DISCOVERY_ERROR,
                f"invalid OpenJev health response: {exc}",
                False,
                started,
            )
        self._model_name = health.model_id
        return health.model_id

    async def evaluate(self, state: AccountingState) -> ProviderOutcome:
        started = time.monotonic()
        model_name = self._model_name
        if model_name is None:
            discovered = await self.discover_model()
            if isinstance(discovered, ProviderFailure):
                return discovered.model_copy(update={"latency_ms": _elapsed_ms(started)})
            model_name = discovered

        response = await self._request(
            "POST", "/v1/systemone", started=started, json=self.build_request(state)
        )
        if isinstance(response, ProviderFailure):
            return response.model_copy(update={"model_name": model_name})
        try:
            parsed = _OpenJevResponse.model_validate(_json_body(response))
            if not _response_matches_discovered(parsed.model, model_name):
                raise ValueError(
                    f"response model {parsed.model!r} differs from discovered model {model_name!r}"
                )
            if set(parsed.answers) != set(QUESTION_NAMES):
                missing = sorted(set(QUESTION_NAMES) - set(parsed.answers))
                extra = sorted(set(parsed.answers) - set(QUESTION_NAMES))
                raise ValueError(f"answer names differ; missing={missing}, extra={extra}")
        except (ValueError, TypeError, ValidationError) as exc:
            return self._failure(
                ProviderFailureCode.INVALID_RESPONSE,
                f"invalid OpenJev response: {exc}",
                False,
                started,
                model_name=model_name,
            )

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
            latency_ms=_elapsed_ms(started),
        )

    async def _request(
        self, method: str, path: str, *, started: float, json: Any = None
    ) -> httpx.Response | ProviderFailure:
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._get_client().request(method, path, json=json)
            except httpx.TimeoutException:
                failure = self._failure(
                    ProviderFailureCode.TIMEOUT, "OpenJev request timed out", True, started
                )
            except httpx.RequestError:
                failure = self._failure(
                    ProviderFailureCode.UNAVAILABLE,
                    "OpenJev transport unavailable",
                    True,
                    started,
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
            headers = (
                {"Authorization": f"Bearer {self.config.api_key}"}
                if self.config.api_key else None
            )
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url, headers=headers, timeout=timeout
            )
        return self._client

    def _status_failure(
        self, response: httpx.Response, started: float
    ) -> ProviderFailure | None:
        if 200 <= response.status_code < 300:
            return None
        if response.status_code in (401, 403):
            code, retryable = ProviderFailureCode.AUTHENTICATION_ERROR, False
        elif response.status_code == 408:
            code, retryable = ProviderFailureCode.TIMEOUT, True
        elif response.status_code == 429:
            code, retryable = ProviderFailureCode.RATE_LIMITED, True
        elif response.status_code >= 500:
            code, retryable = ProviderFailureCode.UNAVAILABLE, True
        else:
            code, retryable = ProviderFailureCode.INVALID_REQUEST, False
        return self._failure(
            code, f"OpenJev returned HTTP {response.status_code}", retryable, started
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
            provider=self.name,
            code=code,
            message=message,
            retryable=retryable,
            latency_ms=_elapsed_ms(started),
            model_name=model_name or self._model_name or self.config.expected_model,
        )


def _elapsed_ms(started: float) -> float:
    return max(0.0, (time.monotonic() - started) * 1000)


def _json_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        raise ValueError(f"expected application/json response, got {content_type or 'missing'}")
    return response.json()


def _response_matches_discovered(response_model: str, discovered_model: str) -> bool:
    """OpenJev prefixes response model IDs while /health returns the raw ID."""
    return response_model in {discovered_model, f"openjev/{discovered_model}"}
