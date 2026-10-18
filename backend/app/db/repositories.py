"""Transactional SQLite audit and execution repository."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.models.action import ProposedAction
from backend.app.models.policy import PolicyDecision
from backend.app.models.workflow import ExecutionResult, HumanReviewResponse


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class IdempotencyConflictError(RuntimeError):
    pass


class AuditRepository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._setup()

    def _setup(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS actions (
                    action_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    audit_id TEXT NOT NULL,
                    scenario_id TEXT,
                    provider TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    state_json TEXT,
                    final_action TEXT,
                    reason_codes_json TEXT,
                    latency_ms REAL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT NOT NULL,
                    audit_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS executions (
                    action_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    audit_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT
                );
                CREATE TABLE IF NOT EXISTS execution_authorizations (
                    action_id TEXT PRIMARY KEY,
                    audit_id TEXT NOT NULL,
                    authorization_type TEXT NOT NULL,
                    assessment_hash TEXT,
                    actor TEXT,
                    created_at TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    review_json TEXT
                );
                """
            )

    def create_received(
        self,
        action: ProposedAction,
        *,
        audit_id: str,
        provider: str,
        scenario_id: str | None,
        idempotency_key: str | None,
    ) -> str:
        with self._lock, self.connection:
            now = _utcnow()
            statement = (
                """INSERT OR IGNORE INTO actions
                (action_id,idempotency_key,audit_id,scenario_id,provider,created_at,updated_at,status,action_json)
                VALUES (?,?,?,?,?,?,?,?,?)"""
                if idempotency_key
                else
                """INSERT INTO actions
                (action_id,idempotency_key,audit_id,scenario_id,provider,created_at,updated_at,status,action_json)
                VALUES (?,?,?,?,?,?,?,?,?)"""
            )
            cursor = self.connection.execute(
                statement,
                (
                    action.action_id, idempotency_key, audit_id, scenario_id, provider,
                    now, now, "received",
                    json.dumps(action.model_dump(mode="json"), sort_keys=True),
                ),
            )
            if idempotency_key and cursor.rowcount == 0:
                existing = self.connection.execute(
                    """SELECT action_id,provider,scenario_id FROM actions
                    WHERE idempotency_key = ?""",
                    (idempotency_key,),
                ).fetchone()
                if existing is None:
                    raise RuntimeError("idempotent action insert lost its conflict row")
                if existing["provider"] != provider or existing["scenario_id"] != scenario_id:
                    raise IdempotencyConflictError(
                        "idempotency key was already used for a different request"
                    )
                return str(existing["action_id"])
            return action.action_id

    def save_workflow_state(self, action_id: str, state: dict[str, Any]) -> None:
        decision = state.get("policy_decision") or {}
        outcome = state.get("provider_outcome") or {}
        with self._lock, self.connection:
            updated = self.connection.execute(
                """UPDATE actions SET updated_at=?, status=?, state_json=?, final_action=?,
                reason_codes_json=?, latency_ms=? WHERE action_id=?""",
                (
                    _utcnow(), state.get("status", "unknown"),
                    json.dumps(state, sort_keys=True, default=str),
                    decision.get("final_action"),
                    json.dumps(decision.get("reason_codes", [])),
                    outcome.get("latency_ms"), action_id,
                ),
            )
            if updated.rowcount != 1:
                raise KeyError(action_id)

    def append_event(
        self,
        action_id: str,
        audit_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """INSERT INTO audit_events
                (action_id,audit_id,event_type,created_at,schema_version,payload_json)
                VALUES (?,?,?,?,?,?)""",
                (
                    action_id, audit_id, event_type, _utcnow(), "1",
                    json.dumps(payload, sort_keys=True, default=str),
                ),
            )
            return self.event(int(cursor.lastrowid))

    def event(self, event_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM audit_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return _event_row(row)

    def events_after(self, event_id: int = 0, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE event_id>? ORDER BY event_id LIMIT ?",
            (event_id, limit),
        ).fetchall()
        return [_event_row(row) for row in rows]

    def events_for_action(self, action_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE action_id=? ORDER BY event_id", (action_id,)
        ).fetchall()
        return [_event_row(row) for row in rows]

    def get_action(self, action_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM actions WHERE action_id=?", (action_id,)
        ).fetchone()
        return _action_row(row) if row else None

    def list_actions(
        self,
        *,
        final_action: str | None = None,
        reason_code: str | None = None,
        provider: str | None = None,
        scenario: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where, params = _action_filters(
            final_action=final_action, reason_code=reason_code,
            provider=provider, scenario=scenario,
        )
        params.extend((limit, offset))
        rows = self.connection.execute(
            f"SELECT * FROM actions {where} ORDER BY created_at DESC, action_id LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [_action_row(row) for row in rows]

    def count_actions(
        self,
        *,
        final_action: str | None = None,
        reason_code: str | None = None,
        provider: str | None = None,
        scenario: str | None = None,
    ) -> int:
        where, params = _action_filters(
            final_action=final_action, reason_code=reason_code,
            provider=provider, scenario=scenario,
        )
        row = self.connection.execute(
            f"SELECT COUNT(*) AS count FROM actions {where}", params
        ).fetchone()
        return int(row["count"])

    def dashboard(self) -> dict[str, Any]:
        rows = self.connection.execute(
            "SELECT final_action, latency_ms FROM actions WHERE final_action IS NOT NULL"
        ).fetchall()
        counts = {name: 0 for name in ("ALLOW", "REQUIRE_APPROVAL", "REQUEST_CONTEXT", "BLOCK")}
        latencies: list[float] = []
        for row in rows:
            counts[str(row["final_action"])] = counts.get(str(row["final_action"]), 0) + 1
            if row["latency_ms"] is not None:
                latencies.append(float(row["latency_ms"]))
        latencies.sort()
        median = None
        if latencies:
            middle = len(latencies) // 2
            median = (
                latencies[middle] if len(latencies) % 2
                else (latencies[middle - 1] + latencies[middle]) / 2
            )
        return {"processed": len(rows), "counts": counts, "median_provider_latency_ms": median}

    def begin_execution(self, action_id: str, execution_id: str, audit_id: str) -> bool:
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT status FROM executions WHERE action_id=?", (action_id,)
            ).fetchone()
            if existing:
                return False
            self.connection.execute(
                "INSERT INTO executions VALUES (?,?,?,?,?,NULL)",
                (action_id, execution_id, audit_id, "INTENT", _utcnow()),
            )
            return True

    def record_execution_authorization(
        self,
        decision: PolicyDecision,
        *,
        review: HumanReviewResponse | None = None,
    ) -> dict[str, Any]:
        authorization_type = "HUMAN_APPROVAL" if review is not None else "POLICY_ALLOW"
        actor = review.reviewer if review is not None else None
        review_json = (
            json.dumps(review.model_dump(mode="json"), sort_keys=True)
            if review is not None else None
        )
        decision_json = json.dumps(decision.model_dump(mode="json"), sort_keys=True)
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT * FROM execution_authorizations WHERE action_id=?",
                (decision.action_id,),
            ).fetchone()
            if existing:
                parsed = _authorization_row(existing)
                if (
                    parsed["audit_id"] != decision.audit_id
                    or parsed["assessment_hash"] != decision.assessment_hash
                    or parsed["authorization_type"] != authorization_type
                ):
                    raise RuntimeError("conflicting execution authorization")
                return parsed
            self.connection.execute(
                """INSERT INTO execution_authorizations
                (action_id,audit_id,authorization_type,assessment_hash,actor,created_at,
                 decision_json,review_json)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    decision.action_id, decision.audit_id, authorization_type,
                    decision.assessment_hash, actor, _utcnow(), decision_json, review_json,
                ),
            )
            row = self.connection.execute(
                "SELECT * FROM execution_authorizations WHERE action_id=?",
                (decision.action_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("execution authorization was not persisted")
            return _authorization_row(row)

    def get_execution_authorization(self, action_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM execution_authorizations WHERE action_id=?", (action_id,)
        ).fetchone()
        return _authorization_row(row) if row else None

    def complete_execution(self, result: ExecutionResult) -> None:
        with self._lock, self.connection:
            updated = self.connection.execute(
                "UPDATE executions SET status='COMPLETED', result_json=? WHERE action_id=? AND status='INTENT'",
                (json.dumps(result.model_dump(mode="json"), sort_keys=True), result.action_id),
            )
            if updated.rowcount != 1:
                raise RuntimeError("execution intent is missing or already completed")

    def get_execution(self, action_id: str) -> ExecutionResult | None:
        row = self.connection.execute(
            "SELECT result_json FROM executions WHERE action_id=? AND status='COMPLETED'",
            (action_id,),
        ).fetchone()
        return ExecutionResult.model_validate_json(row["result_json"]) if row else None

    def get_execution_intent(self, action_id: str) -> dict[str, str] | None:
        row = self.connection.execute(
            """SELECT action_id,execution_id,audit_id,status,created_at FROM executions
            WHERE action_id=? AND status='INTENT'""",
            (action_id,),
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self.connection.close()


def _action_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["action"] = json.loads(result.pop("action_json"))
    state_json = result.pop("state_json")
    reasons_json = result.pop("reason_codes_json")
    result["state"] = json.loads(state_json) if state_json else None
    result["reason_codes"] = json.loads(reasons_json) if reasons_json else []
    return result


def _event_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["type"] = result.pop("event_type")
    result["payload"] = json.loads(result.pop("payload_json"))
    return result


def _authorization_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["decision"] = json.loads(result.pop("decision_json"))
    review_json = result.pop("review_json")
    result["review"] = json.loads(review_json) if review_json else None
    return result


def _action_filters(
    *,
    final_action: str | None,
    reason_code: str | None,
    provider: str | None,
    scenario: str | None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("final_action", final_action), ("provider", provider), ("scenario_id", scenario)
    ):
        if value is not None:
            clauses.append(f"{column}=?")
            params.append(value)
    if reason_code is not None:
        clauses.append(
            "EXISTS (SELECT 1 FROM json_each(actions.reason_codes_json) WHERE value = ?)"
        )
        params.append(reason_code)
    return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params
