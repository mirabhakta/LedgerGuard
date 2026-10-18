"""Google Gemini structured-output baseline provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.models.risk import ProviderFailure, ProviderFailureCode, ProviderOutcome, RiskAssessment
from backend.app.models.state import AccountingState


class GeminiBaselineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str | None = None
    model: str | None = None
    base_url: str = "https://generativelanguage.googleapis.com"
    timeout_seconds: float = Field(default=15, gt=0)

    @classmethod
    def from_environment(cls) -> "GeminiBaselineConfig":
        return cls(
            # This precedence matches Google's documented Gemini API behavior.
            api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL"),
            base_url=os.getenv(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"
            ),
        )


class _GeminiSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_alignment_probability: float = Field(ge=0, le=1)
    goal_alignment_confidence: float = Field(ge=0, le=1)
    duplicate_obligation_probability: float = Field(ge=0, le=1)
    duplicate_obligation_confidence: float = Field(ge=0, le=1)
    counterparty_change_score: float = Field(ge=0, le=1)
    counterparty_change_confidence: float = Field(ge=0, le=1)
    missing_context_probability: float = Field(ge=0, le=1)
    missing_context_confidence: float = Field(ge=0, le=1)
    action_anomaly_score: float = Field(ge=0, le=1)
    action_anomaly_confidence: float = Field(ge=0, le=1)


class GeminiBaselineProvider:
    name = "gemini"

    def __init__(
        self,
        config: GeminiBaselineConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or GeminiBaselineConfig.from_environment()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "GeminiBaselineProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def build_request(self, state: AccountingState) -> dict[str, Any]:
        schema = _GeminiSignals.model_json_schema()
        schema["additionalProperties"] = False
        return {
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "Assess the supplied accounting state using exactly the ten requested "
                        "probability and confidence fields. Do not make a final authorization "
                        "decision and do not invent missing ledger facts."
                    )
                }]
            },
            "contents": [{
                "role": "user",
                "parts": [{"text": json.dumps(state.inference_view(), sort_keys=True)}],
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }

    async def evaluate(self, state: AccountingState) -> ProviderOutcome:
        started = time.monotonic()
        if not self.config.api_key or not self.config.model:
            return self._failure(
                ProviderFailureCode.CONFIGURATION_ERROR,
                "GEMINI_API_KEY (or GOOGLE_API_KEY) and GEMINI_MODEL are required",
                False,
                started,
            )

        try:
            model = _normalize_model_name(self.config.model)
        except ValueError:
            return self._failure(
                ProviderFailureCode.CONFIGURATION_ERROR,
                "GEMINI_MODEL must contain a valid model name",
                False,
                started,
            )
        endpoint = f"/v1beta/models/{quote(model, safe='')}:generateContent"
        try:
            response = await self._get_client().post(
                endpoint,
                headers={"x-goog-api-key": self.config.api_key},
                json=self.build_request(state),
            )
        except httpx.TimeoutException:
            return self._failure(
                ProviderFailureCode.TIMEOUT, "Gemini request timed out", True, started
            )
        except httpx.RequestError:
            return self._failure(
                ProviderFailureCode.UNAVAILABLE,
                "Gemini transport unavailable",
                True,
                started,
            )

        if response.status_code in (401, 403):
            return self._failure(
                ProviderFailureCode.AUTHENTICATION_ERROR,
                "Gemini authentication failed",
                False,
                started,
            )
        if response.status_code == 408:
            return self._failure(
                ProviderFailureCode.TIMEOUT, "Gemini request timed out", True, started
            )
        if response.status_code == 429:
            return self._failure(
                ProviderFailureCode.RATE_LIMITED, "Gemini rate limited", True, started
            )
        if response.status_code >= 500:
            return self._failure(
                ProviderFailureCode.UNAVAILABLE, "Gemini unavailable", True, started
            )
        if response.status_code >= 400:
            return self._failure(
                ProviderFailureCode.INVALID_REQUEST,
                "Gemini rejected request",
                False,
                started,
            )

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Gemini response body must be an object")
            output_text = _extract_output_text(payload)
            signals = _GeminiSignals.model_validate_json(output_text)
        except (ValueError, TypeError, KeyError, ValidationError, json.JSONDecodeError) as exc:
            return self._failure(
                ProviderFailureCode.INVALID_RESPONSE,
                f"invalid structured Gemini response: {exc}",
                False,
                started,
            )

        return RiskAssessment(
            **signals.model_dump(),
            provider=self.name,
            model_name=str(payload.get("modelVersion") or model),
            latency_ms=_elapsed_ms(started),
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
            )
        return self._client

    def _failure(
        self, code: ProviderFailureCode, message: str, retryable: bool, started: float
    ) -> ProviderFailure:
        return ProviderFailure(
            provider=self.name,
            code=code,
            message=message or code.value,
            retryable=retryable,
            latency_ms=_elapsed_ms(started),
            model_name=self.config.model,
        )


def _normalize_model_name(model: str) -> str:
    normalized = model.removeprefix("models/").strip()
    if not normalized:
        raise ValueError("Gemini model name must not be empty")
    return normalized


def _extract_output_text(payload: dict[str, Any]) -> str:
    prompt_feedback = payload.get("promptFeedback")
    if isinstance(prompt_feedback, dict) and prompt_feedback.get("blockReason"):
        raise ValueError("Gemini blocked the prompt")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini response has no candidates")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ValueError("Gemini candidate is malformed")
    finish_reason = candidate.get("finishReason")
    if finish_reason not in (None, "STOP"):
        raise ValueError(f"Gemini candidate did not finish normally: {finish_reason!r}")

    content = candidate.get("content")
    if not isinstance(content, dict):
        raise ValueError("Gemini candidate has no content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ValueError("Gemini candidate content has no parts")
    text_parts = [part.get("text") for part in parts if isinstance(part, dict)]
    if not text_parts or not all(isinstance(text, str) for text in text_parts):
        raise ValueError("Gemini candidate has no text output")
    return "".join(text_parts)


def _elapsed_ms(started: float) -> float:
    return max(0.0, (time.monotonic() - started) * 1000)
