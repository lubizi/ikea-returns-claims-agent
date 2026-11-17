"""Deterministic workflow engine for the IKEA Returns & Claims classroom prototype.

The module deliberately keeps policy decisions separate from the Streamlit UI so
the workflow can be tested without a browser or an LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


DATA_PATH = Path(__file__).parent / "data" / "orders.json"


class Decision(str, Enum):
    AUTO_ELIGIBLE = "Eligible — ready for staff confirmation"
    REQUEST_INFO = "More information required"
    HUMAN_REVIEW = "Human review required"
    NOT_ELIGIBLE = "Not eligible under demo policy"


class IssueType(str, Enum):
    RETURN = "Return / changed mind"
    DAMAGED = "Damaged item"
    MISSING_PART = "Missing part"
    WRONG_ITEM = "Wrong item"
    REFUND_DELAY = "Refund delay"


@dataclass
class ClaimRequest:
    order_id: str
    email: str
    issue_type: str
    description: str
    requested_resolution: str
    evidence_provided: bool = False
    item_opened_or_assembled: bool = False


@dataclass
class WorkflowStep:
    name: str
    status: str
    detail: str


@dataclass
class ClaimResult:
    case_id: str
    decision: Decision
    category: str
    summary: str
    next_action: str
    confidence: float
    estimated_amount_hkd: float
    reasons: List[str] = field(default_factory=list)
    required_information: List[str] = field(default_factory=list)
    guardrails_triggered: List[str] = field(default_factory=list)
    workflow: List[WorkflowStep] = field(default_factory=list)
    order: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


def load_orders(path: Path = DATA_PATH) -> Dict[str, Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        orders = json.load(handle)
    return {order["order_id"].upper(): order for order in orders}


def _case_id(order_id: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    clean_id = re.sub(r"[^A-Z0-9]", "", order_id.upper())[-6:] or "NEW"
    return f"RC-{stamp}-{clean_id}"


def _days_since(value: str, today: date) -> int:
    return (today - date.fromisoformat(value)).days


def evaluate_claim(
    request: ClaimRequest,
    *,
    today: Optional[date] = None,
    orders: Optional[Dict[str, Dict[str, Any]]] = None,
) -> ClaimResult:
    """Run the six-stage intake and policy workflow.

    No payment or refund is executed. Even an ``AUTO_ELIGIBLE`` result is only a
    recommendation awaiting a staff confirmation, which is the key HITL guardrail.
    """

    today = today or date.today()
    orders = orders or load_orders()
    order_id = request.order_id.strip().upper()
    email = request.email.strip().lower()
    description = request.description.strip()
    category = request.issue_type
    workflow: List[WorkflowStep] = []

    workflow.append(
        WorkflowStep(
            "1. Intake & classification",
            "Completed",
            f"Classified as: {category}",
        )
    )

    order = orders.get(order_id)
    if not order:
        workflow.append(
            WorkflowStep("2. Order verification", "Blocked", "Order ID not found in demo data")
        )
        return ClaimResult(
            case_id=_case_id(order_id),
            decision=Decision.REQUEST_INFO,
            category=category,
            summary="The order could not be verified.",
            next_action="Check the order number or ask a staff member to locate the purchase.",
            confidence=0.99,
            estimated_amount_hkd=0,
            reasons=["No matching demo order was found."],
            required_information=["A valid order number or purchase receipt"],
            workflow=workflow,
        )

    if email != order["customer_email"].lower():
        workflow.append(
            WorkflowStep("2. Order verification", "Blocked", "Email does not match the order")
        )
        return ClaimResult(
            case_id=_case_id(order_id),
            decision=Decision.REQUEST_INFO,
            category=category,
            summary="Customer verification was unsuccessful.",
            next_action="Re-enter the purchasing email address or contact staff for identity verification.",
            confidence=0.99,
            estimated_amount_hkd=0,
            reasons=["The supplied email does not match the demo order."],
            required_information=["Purchasing email address"],
            guardrails_triggered=["Identity mismatch — no order details or refund recommendation released"],
            workflow=workflow,
        )

    workflow.append(
        WorkflowStep("2. Order verification", "Completed", "Order and purchasing email matched")
    )

    purchase_age = _days_since(order["purchase_date"], today)
    delivery_age = _days_since(order["delivery_date"], today)
    amount = float(order["total_hkd"])
    required: List[str] = []
    reasons: List[str] = []
    guardrails: List[str] = []

    workflow.append(
        WorkflowStep(
            "3. Policy lookup",
            "Completed",
            f"Applied simulated {category} rules; purchase age: {purchase_age} days",
        )
    )

    safety_terms = {
        "fire",
        "smoke",
        "electric shock",
        "injury",
        "sharp",
        "火",
        "冒煙",
        "漏電",
        "受傷",
    }
    safety_risk = any(term in description.lower() for term in safety_terms)

    if category in {IssueType.DAMAGED.value, IssueType.WRONG_ITEM.value} and not request.evidence_provided:
        required.append("Photo(s) showing the item, packaging and product label")
    if category == IssueType.MISSING_PART.value and not description:
        required.append("Missing part number or a description of the part")

    if required:
        workflow.append(
            WorkflowStep("4. Evidence check", "Blocked", "Supporting information is incomplete")
        )
        return ClaimResult(
            case_id=_case_id(order_id),
            decision=Decision.REQUEST_INFO,
            category=category,
            summary="The claim is saved, but evidence is still required.",
            next_action="Upload the requested evidence, then resubmit the assessment.",
            confidence=0.96,
            estimated_amount_hkd=amount,
            reasons=["The evidence requirement for this claim type has not been met."],
            required_information=required,
            workflow=workflow,
            order=order,
        )

    workflow.append(WorkflowStep("4. Evidence check", "Completed", "Minimum evidence checks passed"))

    if safety_risk:
        guardrails.append("Potential product safety issue — urgent staff escalation")
    if amount >= 3000:
        guardrails.append("High-value claim (HK$3,000 or above)")
    if int(order.get("previous_claims", 0)) >= 2:
        guardrails.append("Multiple previous claims require fraud-risk review")

    workflow.append(
        WorkflowStep(
            "5. Risk & guardrail check",
            "Escalated" if guardrails else "Completed",
            "; ".join(guardrails) if guardrails else "No enhanced-risk trigger detected",
        )
    )

    # Simulated classroom rules; deliberately not represented as IKEA's live policy.
    eligible = True
    if category == IssueType.RETURN.value:
        if purchase_age > 365:
            eligible = False
            reasons.append("The purchase is outside the simulated 365-day return window.")
        elif request.item_opened_or_assembled:
            guardrails.append("Opened or assembled item requires condition inspection")
            reasons.append("Condition must be checked before a return can be accepted.")
        else:
            reasons.append("Purchase is inside the simulated return window.")
    elif category == IssueType.DAMAGED.value:
        if delivery_age > 30:
            guardrails.append("Damage reported more than 30 days after delivery")
        reasons.append("Damage evidence was supplied for staff validation.")
    elif category == IssueType.MISSING_PART.value:
        reasons.append("The order is verified and a missing-part request can be created.")
    elif category == IssueType.WRONG_ITEM.value:
        reasons.append("Photo evidence and order details are available for comparison.")
    elif category == IssueType.REFUND_DELAY.value:
        guardrails.append("Payment status must be checked by a staff member")
        reasons.append("Refund tracing requires access to the payment system.")
    else:
        guardrails.append("Unrecognized claim category")

    if not eligible:
        decision = Decision.NOT_ELIGIBLE
        summary = "The request does not meet the simulated return rule."
        next_action = "A staff member may review exceptional circumstances."
    elif guardrails:
        decision = Decision.HUMAN_REVIEW
        summary = "The claim passed intake but needs a staff decision."
        next_action = "Route the prepared case to the Returns & Claims review queue."
    else:
        decision = Decision.AUTO_ELIGIBLE
        summary = "The claim meets the simulated rules and is ready for confirmation."
        next_action = "A staff member confirms the recommendation before any fulfilment action."

    workflow.append(
        WorkflowStep(
            "6. Recommendation & routing",
            "Completed",
            f"Recommendation: {decision.value}; no refund was executed",
        )
    )

    return ClaimResult(
        case_id=_case_id(order_id),
        decision=decision,
        category=category,
        summary=summary,
        next_action=next_action,
        confidence=0.94 if not guardrails else 0.87,
        estimated_amount_hkd=amount,
        reasons=reasons,
        required_information=required,
        guardrails_triggered=guardrails,
        workflow=workflow,
        order=order,
    )

