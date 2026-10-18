"""Routing only; all financial policy remains in PolicyEngine."""

from backend.app.models.policy import FinalAction, PolicyDecision

from .state import AgentGraphState


def route_after_context(state: AgentGraphState) -> str:
    return "blocked_terminal" if state.get("error_state") else "hard_precheck"


def route_after_precheck(state: AgentGraphState) -> str:
    precheck = state.get("precheck_result") or {}
    return "policy_decide" if precheck.get("hard_violation") else "evaluate_risk"


def route_after_policy(state: AgentGraphState) -> str:
    decision = PolicyDecision.model_validate(state["policy_decision"])
    return {
        FinalAction.ALLOW: "execute_action",
        FinalAction.REQUIRE_APPROVAL: "human_review",
        FinalAction.REQUEST_CONTEXT: "request_context",
        FinalAction.BLOCK: "blocked_terminal",
    }[decision.final_action]
