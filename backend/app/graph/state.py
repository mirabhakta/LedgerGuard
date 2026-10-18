"""JSON-serializable LangGraph state."""

from typing import Any, TypedDict


class AgentGraphState(TypedDict, total=False):
    user_goal: str
    proposed_action: dict[str, Any]
    accounting_state: dict[str, Any] | None
    precheck_result: dict[str, Any] | None
    provider_outcome: dict[str, Any] | None
    policy_decision: dict[str, Any] | None
    human_response: dict[str, Any] | None
    execution_result: dict[str, Any] | None
    audit_id: str
    current_scenario: str | None
    error_state: dict[str, Any] | None
    status: str
    workflow_version: str
