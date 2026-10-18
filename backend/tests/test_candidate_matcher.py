from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.models import (
    ActionType,
    CanonicalAccountingRecord,
    ProposedAction,
    RecordType,
    SourceMetadata,
)
from backend.app.services.candidate_matcher import CandidateMatcher


def _record(source_id: str, *, company: str = "company-001", days: int = 10, amount: str = "100"):
    return CanonicalAccountingRecord(
        record_id=f"{company}:bill:{source_id}", source_id=source_id,
        company_id=company, dataset_id="world", record_type=RecordType.BILL,
        timestamp=date(2025, 1, days), vendor_id="vend-1", vendor_name="Vendor",
        amount=Decimal(amount), currency="USD", category="supplies",
        source=SourceMetadata(repository="test", relative_path="bills.yaml"),
    )


def _action() -> ProposedAction:
    return ProposedAction(
        action_id="a1", action_type=ActionType.PAY_VENDOR_BILL,
        company_id="company-001", timestamp=datetime(2025, 1, 12, tzinfo=timezone.utc),
        amount=Decimal("100"), currency="USD", vendor_id="vend-1",
        source_document_id="target", proposed_category="supplies", agent_goal="pay vendor bill",
    )


def test_exact_link_ranks_first_and_reasons_are_explainable() -> None:
    results = CandidateMatcher(top_k=2).match(
        _action(), (_record("other"), _record("target", days=1, amount="500"))
    )
    assert results[0].source_id == "target"
    assert "EXACT_DOCUMENT_LINK" in results[0].match_reasons
    assert len(results) == 2


def test_future_out_of_window_and_cross_company_records_are_excluded() -> None:
    results = CandidateMatcher(window_days=20).match(
        _action(),
        (
            _record("future", days=20),
            _record("cross", company="company-002"),
            _record("valid", days=10),
        ),
    )
    assert [item.source_id for item in results] == ["valid"]


def test_equal_score_ties_prefer_the_most_recent_record() -> None:
    results = CandidateMatcher(top_k=1).match(
        _action(), (_record("older", days=9), _record("newer", days=11))
    )
    assert [item.source_id for item in results] == ["newer"]
