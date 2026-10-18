from backend.app.models.risk import RiskAssessment
from backend.app.providers.rules import RulesProvider
from backend.tests.factories import make_state

provider = RulesProvider()


async def test_ordinary_payment_is_low_risk():
    a = await provider.evaluate(make_state())
    assert isinstance(a, RiskAssessment)
    assert a.model_name == "rules-v1"
    for name in ("goal_misalignment_risk", "duplicate_obligation_risk", "counterparty_change_risk", "action_anomaly_risk"):
        assert getattr(a, name).value < 0.5, name


async def test_near_duplicate_candidate_scores_high():
    state = make_state(features={
        "candidate_count": 1,
        "closest_candidate_amount_delta_pct": 0.001,
        "closest_candidate_days_apart": 2,
        "closest_candidate_same_counterparty": True,
    })
    assert (await provider.evaluate(state)).duplicate_obligation_risk.value >= 0.9


async def test_recent_destination_change_scores_high():
    state = make_state(features={"payment_destination_changed": True, "destination_first_seen_days_ago": 1})
    assert (await provider.evaluate(state)).counterparty_change_risk.value >= 0.8


async def test_large_amount_is_anomalous():
    state = make_state(amount=1800.0, features={"amount_ratio_to_vendor_median": 3.6, "amount_robust_z": 40.0})
    assert (await provider.evaluate(state)).action_anomaly_risk.value >= 0.8


async def test_unknown_vendor_without_document_needs_context():
    state = make_state(
        vendor="Northline Advisory Group",
        source_document_id=None,
        metadata={"memo": "Services rendered"},
        features={"vendor_known": False, "has_source_document": False},
    )
    assert (await provider.evaluate(state)).missing_context_risk.value >= 0.7


async def test_only_utilities_constraint_flags_rent_payment():
    state = make_state(constraints=["Only pay utility bills today; hold everything else."])
    assert (await provider.evaluate(state)).goal_misalignment_risk.value >= 0.9


async def test_only_utilities_constraint_allows_utility_payment():
    state = make_state(
        vendor="Havenwood Municipal Utilities",
        constraints=["Only pay utility bills today; hold everything else."],
        features={"vendor_supply_role": "utility"},
    )
    assert (await provider.evaluate(state)).goal_misalignment_risk.value < 0.5


async def test_vendor_hold_constraint():
    state = make_state(constraints=["Do not pay anything to Granite Bay Commercial Properties until the dispute is resolved."])
    assert (await provider.evaluate(state)).goal_misalignment_risk.value >= 0.9
