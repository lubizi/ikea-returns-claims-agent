from datetime import date

from agent import ClaimRequest, Decision, IssueType, evaluate_claim, load_orders


TODAY = date(2026, 11, 17)
ORDERS = load_orders()


def request(**overrides):
    values = {
        "order_id": "HK-2026-1001",
        "email": "alex.chan@example.com",
        "issue_type": IssueType.DAMAGED.value,
        "description": "The tabletop arrived cracked.",
        "requested_resolution": "Replacement",
        "evidence_provided": True,
        "item_opened_or_assembled": False,
    }
    values.update(overrides)
    return ClaimRequest(**values)


def assess(**overrides):
    return evaluate_claim(request(**overrides), today=TODAY, orders=ORDERS)


def test_standard_damage_claim_is_ready_for_confirmation():
    result = assess()
    assert result.decision == Decision.AUTO_ELIGIBLE
    assert len(result.workflow) == 6
    assert result.estimated_amount_hkd == 1299


def test_unknown_order_requests_information_without_leaking_order_data():
    result = assess(order_id="HK-2026-9999")
    assert result.decision == Decision.REQUEST_INFO
    assert result.order is None


def test_email_mismatch_blocks_claim_and_order_data():
    result = assess(email="attacker@example.com")
    assert result.decision == Decision.REQUEST_INFO
    assert result.order is None
    assert "Identity mismatch" in result.guardrails_triggered[0]


def test_damage_claim_requires_evidence():
    result = assess(evidence_provided=False)
    assert result.decision == Decision.REQUEST_INFO
    assert result.required_information


def test_high_value_claim_requires_human_review():
    result = assess(
        order_id="HK-2026-1002",
        email="jamie.wong@example.com",
        issue_type=IssueType.RETURN.value,
        description="The sofa does not fit.",
        requested_resolution="Refund",
    )
    assert result.decision == Decision.HUMAN_REVIEW
    assert any("High-value" in item for item in result.guardrails_triggered)


def test_safety_language_gets_urgent_human_review():
    result = assess(description="The lamp produced smoke and an electric shock.")
    assert result.decision == Decision.HUMAN_REVIEW
    assert any("safety" in item.lower() for item in result.guardrails_triggered)


def test_outside_return_window_is_not_eligible():
    result = assess(
        order_id="HK-2026-1004",
        email="taylor.lam@example.com",
        issue_type=IssueType.RETURN.value,
        description="Changed my mind.",
        requested_resolution="Refund",
    )
    assert result.decision == Decision.NOT_ELIGIBLE


def test_refund_delay_always_routes_to_staff():
    result = assess(
        issue_type=IssueType.REFUND_DELAY.value,
        description="The expected refund has not arrived.",
        requested_resolution="Status update",
    )
    assert result.decision == Decision.HUMAN_REVIEW
    assert any("Payment status" in item for item in result.guardrails_triggered)

