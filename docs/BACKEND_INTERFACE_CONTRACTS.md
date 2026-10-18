# LedgerGuard Backend Interface Contracts

**Project:** LA Hacks 2026 — LedgerGuard / Agent Firewall  
**Purpose:** Canonical backend contracts shared by the live app, System One provider, LLM/rules baselines, policy engine, LangGraph workflow, and evaluation pipeline.

> **Freeze rule:** The live app and evaluation path must use the same `AccountingState`, `RiskAssessment`, `PolicyEngine.decide(...)`, and `build_accounting_state(...)` contracts. Do not create eval-only serialization or competing model definitions.

---

## 1. Canonical Data Flow

```text
Scenario
   ↓
build_accounting_state()
   ↓
AccountingState
   ↓
DecisionProvider
   ↓
RiskAssessment
   ↓
PolicyEngine.decide(...)
   ↓
PolicyDecision
   ↓
FinalAction
```

All providers receive the same `AccountingState` and return the same `RiskAssessment`.

Supported providers:

```text
RulesProvider
LLMBaselineProvider
SystemOneProvider
```

---

# 2. `FinalAction` and `ProposedAction`

**File:** `backend/app/models/action.py`

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FinalAction(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUEST_CONTEXT = "REQUEST_CONTEXT"
    BLOCK = "BLOCK"


class ProposedAction(BaseModel):
    action_id: str
    action_type: str
    timestamp: datetime | None = None
    amount: float | None = None
    currency: str | None = None
    vendor: str | None = None
    counterparty: str | None = None
    destination_account: str | None = None
    source_document_id: str | None = None
    proposed_category: str | None = None
    agent_goal: str
    agent_reasoning_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Contract notes

- `FinalAction` is intentionally limited to four values.
- For a semantic duplicate, use:

```text
final_action = BLOCK
reason_code = DUPLICATE_OBLIGATION
```

rather than adding a fifth final action such as `MATCH_EXISTING`.

---

# 3. `AccountingState`

**File:** `backend/app/models/state.py`

```python
from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from .action import ProposedAction


class CandidateMatch(BaseModel):
    record_id: str
    # Annotated as dt.date: a bare `date` annotation is shadowed by this field's own name.
    date: dt.date | None = None
    amount: float | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessContext(BaseModel):
    company_id: str | None = None
    business_type: str | None = None
    current_account: str | None = None
    vendor_history: dict[str, Any] = Field(default_factory=dict)
    historical_amount_stats: dict[str, float] = Field(default_factory=dict)
    known_payment_destinations: list[str] = Field(default_factory=list)
    known_accounting_patterns: list[str] = Field(default_factory=list)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccountingState(BaseModel):
    proposed_action: ProposedAction
    candidate_matches: list[CandidateMatch] = Field(default_factory=list)
    business_context: BusinessContext
    recent_ledger_history: list[dict[str, Any]] = Field(default_factory=list)
    deterministic_features: dict[str, Any] = Field(default_factory=dict)
    scenario_id: str | None = None
```

### Contract notes

`AccountingState` must be provider-neutral.

Do **not** create separate versions such as:

```text
SystemOneAccountingState
LLMAccountingState
EvalAccountingState
```

The same state must be usable by all decision providers.

---

# 4. `RiskSignal` and `RiskAssessment`

**File:** `backend/app/models/risk.py`

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class RiskSignal(BaseModel):
    # value: 0.0 = low risk, 1.0 = high risk
    value: float = Field(ge=0.0, le=1.0)

    # confidence: 0.0 = uncertain, 1.0 = highly confident
    confidence: float = Field(ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    goal_misalignment_risk: RiskSignal
    duplicate_obligation_risk: RiskSignal
    counterparty_change_risk: RiskSignal
    missing_context_risk: RiskSignal
    action_anomaly_risk: RiskSignal

    model_name: str
    latency_ms: float = Field(ge=0.0)

    had_error: bool = False
    used_fallback: bool = False

    error_code: str | None = None
    error_message: str | None = None
```

## Risk semantic convention

Every signal uses the same direction:

```text
0.0 = low risk
1.0 = high risk
```

Therefore use:

```text
goal_misalignment_risk
```

instead of:

```text
goal_alignment
```

This avoids inverted policy logic and makes threshold sweeps easier.

---

# 5. `PrecheckResult` and `PolicyDecision`

**File:** `backend/app/models/policy.py`

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .action import FinalAction


class PrecheckResult(BaseModel):
    passed: bool = True
    hard_block: bool = False
    requires_review: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    deterministic_features: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    final_action: FinalAction
    reason_codes: list[str] = Field(default_factory=list)
    triggered_thresholds: list[str] = Field(default_factory=list)
    provider: str
    audit_id: str | None = None
    fail_safe_triggered: bool = False
```

---

# 6. `PolicyConfig`

**File:** `backend/app/policy/config.py`

```python
from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    goal_misalignment_block_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    duplicate_block_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    counterparty_review_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    missing_context_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    anomaly_review_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    minimum_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
```

## Why thresholds must be passed through config

The evaluation pipeline must be able to sweep thresholds without editing production code.

Correct:

```python
config = PolicyConfig(
    duplicate_block_threshold=0.85
)
```

Avoid hard-coded values scattered throughout the engine.

---

# 7. `PolicyEngine.decide(...)`

**File:** `backend/app/policy/engine.py`

```python
from __future__ import annotations

from backend.app.models.action import FinalAction
from backend.app.models.policy import PolicyDecision, PrecheckResult
from backend.app.models.risk import RiskAssessment
from backend.app.models.state import AccountingState
from backend.app.policy.config import PolicyConfig


class PolicyEngine:
    def decide(
        self,
        state: AccountingState,
        assessment: RiskAssessment,
        precheck_result: PrecheckResult,
        config: PolicyConfig,
    ) -> PolicyDecision:
        provider = assessment.model_name

        if assessment.had_error:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["PROVIDER_ERROR"],
                triggered_thresholds=[],
                provider=provider,
                fail_safe_triggered=True,
            )

        if precheck_result.hard_block:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=precheck_result.reason_codes,
                triggered_thresholds=[],
                provider=provider,
            )

        if precheck_result.requires_review:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=precheck_result.reason_codes,
                triggered_thresholds=[],
                provider=provider,
            )

        all_signals = [
            assessment.goal_misalignment_risk,
            assessment.duplicate_obligation_risk,
            assessment.counterparty_change_risk,
            assessment.missing_context_risk,
            assessment.action_anomaly_risk,
        ]

        min_confidence = min(signal.confidence for signal in all_signals)

        if min_confidence < config.minimum_confidence_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["LOW_PROVIDER_CONFIDENCE"],
                triggered_thresholds=["minimum_confidence_threshold"],
                provider=provider,
            )

        if assessment.goal_misalignment_risk.value >= config.goal_misalignment_block_threshold:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=["GOAL_MISALIGNMENT"],
                triggered_thresholds=["goal_misalignment_block_threshold"],
                provider=provider,
            )

        if assessment.duplicate_obligation_risk.value >= config.duplicate_block_threshold:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=["DUPLICATE_OBLIGATION"],
                triggered_thresholds=["duplicate_block_threshold"],
                provider=provider,
            )

        if assessment.counterparty_change_risk.value >= config.counterparty_review_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["COUNTERPARTY_CHANGE_RISK"],
                triggered_thresholds=["counterparty_review_threshold"],
                provider=provider,
            )

        if assessment.missing_context_risk.value >= config.missing_context_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUEST_CONTEXT,
                reason_codes=["MISSING_CONTEXT"],
                triggered_thresholds=["missing_context_threshold"],
                provider=provider,
            )

        if assessment.action_anomaly_risk.value >= config.anomaly_review_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["ACTION_ANOMALY"],
                triggered_thresholds=["anomaly_review_threshold"],
                provider=provider,
            )

        return PolicyDecision(
            final_action=FinalAction.ALLOW,
            reason_codes=["LOW_RISK"],
            triggered_thresholds=[],
            provider=provider,
        )
```

---

# 8. `Scenario`

**File:** `backend/app/models/scenario.py`

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .action import FinalAction, ProposedAction


class Scenario(BaseModel):
    scenario_id: str
    scenario_type: str
    proposed_action: ProposedAction
    source_record_ids: list[str] = Field(default_factory=list)
    original_data: dict[str, Any] = Field(default_factory=dict)
    modifications: dict[str, Any] = Field(default_factory=dict)
    modification_reason: str | None = None
    expected_action: FinalAction | None = None
    expected_risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

# 9. `build_accounting_state(...)`

**File:** `backend/app/services/context_builder.py`

```python
from __future__ import annotations

from backend.app.models.scenario import Scenario
from backend.app.models.state import AccountingState, BusinessContext, CandidateMatch


def build_accounting_state(
    scenario: Scenario,
) -> AccountingState:
    """
    Build the canonical provider-neutral AccountingState.

    IMPORTANT:
    The live application and evaluation pipeline must both use
    this exact function.

    No eval-only serialization or alternate state representation.
    """

    action = scenario.proposed_action

    raw_candidate_matches = scenario.original_data.get(
        "candidate_matches",
        []
    )

    candidate_matches = [
        CandidateMatch.model_validate(item)
        for item in raw_candidate_matches
    ]

    business_context_data = scenario.original_data.get(
        "business_context",
        {}
    )

    business_context = BusinessContext.model_validate(
        business_context_data
    )

    recent_ledger_history = scenario.original_data.get(
        "recent_ledger_history",
        []
    )

    deterministic_features = scenario.original_data.get(
        "deterministic_features",
        {}
    )

    return AccountingState(
        proposed_action=action,
        candidate_matches=candidate_matches,
        business_context=business_context,
        recent_ledger_history=recent_ledger_history,
        deterministic_features=deterministic_features,
        scenario_id=scenario.scenario_id,
    )
```

## Important

The live app and evaluation pipeline must both call:

```python
build_accounting_state(scenario)
```

Do not build a separate evaluation-only JSON representation.

---

# 10. `DecisionProvider`

**File:** `backend/app/providers/base.py`

```python
from __future__ import annotations

from typing import Protocol

from backend.app.models.risk import RiskAssessment
from backend.app.models.state import AccountingState


class DecisionProvider(Protocol):
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
```

Canonical provider implementations:

```python
class SystemOneProvider:
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
```

```python
class LLMBaselineProvider:
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
```

```python
class RulesProvider:
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
```

---

# 11. Example `RulesProvider`

**File:** `backend/app/providers/rules.py`

```python
from __future__ import annotations

import time

from backend.app.models.risk import RiskAssessment, RiskSignal
from backend.app.models.state import AccountingState


class RulesProvider:
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:

        started = time.perf_counter()

        features = state.deterministic_features

        duplicate_score = float(
            features.get("duplicate_rule_score", 0.0)
        )

        anomaly_score = float(
            features.get("amount_anomaly_score", 0.0)
        )

        destination_changed = bool(
            features.get("payment_destination_changed", False)
        )

        latency_ms = (time.perf_counter() - started) * 1000

        return RiskAssessment(
            goal_misalignment_risk=RiskSignal(
                value=0.0,
                confidence=0.5,
            ),
            duplicate_obligation_risk=RiskSignal(
                value=max(0.0, min(1.0, duplicate_score)),
                confidence=1.0,
            ),
            counterparty_change_risk=RiskSignal(
                value=1.0 if destination_changed else 0.0,
                confidence=1.0,
            ),
            missing_context_risk=RiskSignal(
                value=0.0,
                confidence=0.5,
            ),
            action_anomaly_risk=RiskSignal(
                value=max(0.0, min(1.0, anomaly_score)),
                confidence=1.0,
            ),
            model_name="rules-v1",
            latency_ms=latency_ms,
        )
```

---

# 12. Provider Error Helper

**File:** `backend/app/providers/helpers.py`

```python
from backend.app.models.risk import RiskAssessment, RiskSignal


def provider_error_assessment(
    *,
    model_name: str,
    latency_ms: float,
    error_code: str,
    error_message: str,
) -> RiskAssessment:
    unknown = RiskSignal(
        value=0.5,
        confidence=0.0,
    )

    return RiskAssessment(
        goal_misalignment_risk=unknown,
        duplicate_obligation_risk=unknown,
        counterparty_change_risk=unknown,
        missing_context_risk=unknown,
        action_anomaly_risk=unknown,
        model_name=model_name,
        latency_ms=latency_ms,
        had_error=True,
        used_fallback=True,
        error_code=error_code,
        error_message=error_message,
    )
```

## Fail-safe rule

Never allow this failure mode:

```text
provider error
→ missing values default to 0
→ interpreted as low risk
→ ALLOW
```

A malformed or unavailable semantic provider must fail safe to review/block.

---

# 13. End-to-End Usage Example

```python
from backend.app.policy.config import PolicyConfig
from backend.app.policy.engine import PolicyEngine
from backend.app.models.policy import PrecheckResult
from backend.app.services.context_builder import build_accounting_state


async def evaluate_scenario(
    scenario,
    provider,
):
    state = build_accounting_state(scenario)

    precheck = PrecheckResult(
        passed=True,
        hard_block=False,
        requires_review=False,
    )

    assessment = await provider.evaluate(state)

    config = PolicyConfig()

    engine = PolicyEngine()

    decision = engine.decide(
        state=state,
        assessment=assessment,
        precheck_result=precheck,
        config=config,
    )

    return {
        "state": state,
        "assessment": assessment,
        "decision": decision,
    }
```

---

# 14. Evaluation Threshold Sweep Example

```python
async def sweep_duplicate_thresholds(
    scenarios,
    provider,
):
    engine = PolicyEngine()

    thresholds = [
        0.50,
        0.60,
        0.70,
        0.80,
        0.90,
        0.95,
    ]

    results = []

    for threshold in thresholds:
        config = PolicyConfig(
            duplicate_block_threshold=threshold
        )

        for scenario in scenarios:
            state = build_accounting_state(scenario)
            assessment = await provider.evaluate(state)
            precheck = PrecheckResult()

            decision = engine.decide(
                state=state,
                assessment=assessment,
                precheck_result=precheck,
                config=config,
            )

            results.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "threshold": threshold,
                    "predicted_action": decision.final_action,
                    "expected_action": scenario.expected_action,
                }
            )

    return results
```

This enables analysis such as:

```text
threshold
vs.
safe autonomous execution coverage
vs.
unsafe action escape rate
```

---

# 15. Canonical Frozen Signatures

These are the interfaces teammates should build against.

## Context Builder

```python
def build_accounting_state(
    scenario: Scenario,
) -> AccountingState:
    ...
```

## Decision Provider

```python
class DecisionProvider(Protocol):
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
```

## Policy Engine

```python
class PolicyEngine:
    def decide(
        self,
        state: AccountingState,
        assessment: RiskAssessment,
        precheck_result: PrecheckResult,
        config: PolicyConfig,
    ) -> PolicyDecision:
        ...
```

## Risk Signal

```python
class RiskSignal(BaseModel):
    value: float       # [0, 1], low risk -> high risk
    confidence: float  # [0, 1], uncertain -> confident
```

---

# 16. Team Integration Rules

1. Do not commit competing definitions of the canonical models.
2. Local temporary stubs are fine until the real implementations land.
3. Live and eval paths must share `build_accounting_state()`.
4. All providers consume the same `AccountingState`.
5. All providers return the same `RiskAssessment`.
6. `PolicyEngine` must be deterministic and side-effect free.
7. Thresholds must come from `PolicyConfig`.
8. Provider failures must fail safe.
9. No provider may directly execute a financial action.
10. Do not hard-code scenario-specific answers.
11. Do not add eval-only serialization.
12. Keep risk semantics consistent: `0 = low risk`, `1 = high risk`.

---

# 17. Recommended Immediate Freeze

Freeze these names and signatures now:

```text
AccountingState
RiskSignal
RiskAssessment
PrecheckResult
PolicyConfig
PolicyDecision
FinalAction
Scenario
DecisionProvider.evaluate(...)
PolicyEngine.decide(...)
build_accounting_state(...)
```

Changing these after backend and evaluation work have started will create unnecessary integration and merge cost.
