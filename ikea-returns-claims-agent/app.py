"""Streamlit interface for the IKEA Returns & Claims AI Agent prototype."""

from __future__ import annotations

import json

import streamlit as st

from agent import ClaimRequest, Decision, IssueType, evaluate_claim, load_orders


st.set_page_config(
    page_title="IKEA Returns & Claims AI Agent",
    page_icon="🛋️",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { --ikea-blue: #0058A3; --ikea-yellow: #FFDA1A; }
    .stApp { background: #f7f8fa; }
    .hero { background: var(--ikea-blue); color: white; padding: 1.5rem 1.7rem;
            border-radius: 14px; margin-bottom: 1rem; }
    .hero h1 { color: white; margin: 0; font-size: 2rem; }
    .hero p { margin: .45rem 0 0; opacity: .92; }
    .prototype { display: inline-block; background: var(--ikea-yellow); color: #111;
                 padding: .2rem .65rem; border-radius: 999px; font-weight: 700;
                 margin-top: .7rem; }
    .result-card { background: white; border-left: 7px solid var(--ikea-blue);
                   border-radius: 10px; padding: 1rem 1.2rem; }
    .small-note { color: #5c6470; font-size: .85rem; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e4e7eb;
                                  padding: .65rem; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Returns & Claims AI Agent</h1>
      <p>First-line intake, policy checks, risk guardrails and staff routing in one workflow.</p>
      <span class="prototype">Classroom prototype — not affiliated with IKEA</span>
    </div>
    """,
    unsafe_allow_html=True,
)

orders = load_orders()

with st.sidebar:
    st.header("Demo control centre")
    st.caption("Select a scenario to prefill a test case.")
    scenario = st.radio(
        "Scenario",
        [
            "Damaged item — eligible",
            "Missing evidence",
            "High-value return",
            "Safety escalation",
            "Unknown order",
        ],
    )
    st.divider()
    st.subheader("What this agent demonstrates")
    st.markdown(
        """
        - Task decomposition
        - Order-data tool use
        - Policy and evidence checks
        - Fraud and safety guardrails
        - Human-in-the-loop approval
        - Auditable reasoning trail
        """
    )
    st.warning("No real IKEA system, payment service or customer data is connected.")


SCENARIOS = {
    "Damaged item — eligible": {
        "order_id": "HK-2026-1001",
        "email": "alex.chan@example.com",
        "issue": IssueType.DAMAGED.value,
        "description": "The tabletop arrived with a deep crack along one corner.",
        "resolution": "Replacement",
        "evidence": True,
        "assembled": False,
    },
    "Missing evidence": {
        "order_id": "HK-2026-1001",
        "email": "alex.chan@example.com",
        "issue": IssueType.DAMAGED.value,
        "description": "The tabletop was damaged on arrival.",
        "resolution": "Replacement",
        "evidence": False,
        "assembled": False,
    },
    "High-value return": {
        "order_id": "HK-2026-1002",
        "email": "jamie.wong@example.com",
        "issue": IssueType.RETURN.value,
        "description": "The sofa does not fit the intended room.",
        "resolution": "Refund",
        "evidence": True,
        "assembled": False,
    },
    "Safety escalation": {
        "order_id": "HK-2026-1003",
        "email": "sam.lee@example.com",
        "issue": IssueType.DAMAGED.value,
        "description": "The lamp produced smoke and an electric shock when switched on.",
        "resolution": "Refund",
        "evidence": True,
        "assembled": True,
    },
    "Unknown order": {
        "order_id": "HK-2026-9999",
        "email": "customer@example.com",
        "issue": IssueType.RETURN.value,
        "description": "I would like to return this item.",
        "resolution": "Refund",
        "evidence": False,
        "assembled": False,
    },
}

if st.session_state.get("loaded_scenario") != scenario:
    defaults = SCENARIOS[scenario]
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state["loaded_scenario"] = scenario


tab_claim, tab_architecture, tab_roi = st.tabs(
    ["Submit & assess claim", "Agent workflow", "Business value"]
)

with tab_claim:
    st.subheader("Customer claim intake")
    with st.form("claim_form"):
        col1, col2 = st.columns(2)
        with col1:
            order_id = st.text_input("Order number", key="order_id")
            email = st.text_input("Purchasing email", key="email")
            issue_type = st.selectbox(
                "Issue type",
                [item.value for item in IssueType],
                key="issue",
            )
        with col2:
            requested_resolution = st.selectbox(
                "Preferred resolution",
                ["Replacement", "Refund", "Missing part shipment", "Status update"],
                key="resolution",
            )
            evidence_provided = st.checkbox(
                "Photo / receipt evidence supplied", key="evidence"
            )
            assembled = st.checkbox("Item opened or assembled", key="assembled")
        description = st.text_area(
            "Describe what happened",
            key="description",
            height=110,
            placeholder="Include the problem, when it happened and the item condition.",
        )
        submitted = st.form_submit_button(
            "Run agent assessment", type="primary", use_container_width=True
        )

    if submitted:
        if not order_id.strip() or not email.strip():
            st.error("Please enter both the order number and purchasing email.")
        else:
            with st.spinner("Running the six-stage workflow..."):
                st.session_state["result"] = evaluate_claim(
                    ClaimRequest(
                        order_id=order_id,
                        email=email,
                        issue_type=issue_type,
                        description=description,
                        requested_resolution=requested_resolution,
                        evidence_provided=evidence_provided,
                        item_opened_or_assembled=assembled,
                    )
                )

    result = st.session_state.get("result")
    if result:
        st.divider()
        if result.decision == Decision.AUTO_ELIGIBLE:
            st.success(result.decision.value)
        elif result.decision == Decision.REQUEST_INFO:
            st.warning(result.decision.value)
        elif result.decision == Decision.HUMAN_REVIEW:
            st.info(result.decision.value)
        else:
            st.error(result.decision.value)

        st.markdown(
            f"""
            <div class="result-card">
              <strong>{result.summary}</strong><br>
              <span class="small-note">Case {result.case_id}</span>
              <p><strong>Next action:</strong> {result.next_action}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Confidence", f"{result.confidence:.0%}")
        metric2.metric("Claim value", f"HK${result.estimated_amount_hkd:,.0f}")
        metric3.metric("Guardrails", len(result.guardrails_triggered))

        left, right = st.columns([1, 1])
        with left:
            st.subheader("Assessment explanation")
            for reason in result.reasons:
                st.write(f"✓ {reason}")
            for item in result.required_information:
                st.write(f"○ Required: {item}")
            for trigger in result.guardrails_triggered:
                st.write(f"⚠ {trigger}")
        with right:
            st.subheader("Auditable workflow")
            for step in result.workflow:
                with st.expander(f"{step.name} — {step.status}"):
                    st.write(step.detail)

        st.download_button(
            "Download case record (JSON)",
            data=json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            file_name=f"{result.case_id}.json",
            mime="application/json",
        )

with tab_architecture:
    st.subheader("Multi-step business workflow")
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR;
          node [shape=box, style="rounded,filled", fillcolor="#ffffff", color="#0058A3"];
          Intake -> Verify -> Policy -> Evidence -> Risk -> Recommend;
          Risk -> Human [label="high risk", color="#d97706"];
          Recommend -> Human [label="confirm", color="#d97706"];
        }
        """,
        use_container_width=True,
    )
    st.markdown(
        """
        **Tools used by the prototype**

        1. Demo order lookup validates the order and purchasing email.
        2. Policy engine applies transparent, deterministic classroom rules.
        3. Evidence checker identifies missing photos or part information.
        4. Risk engine detects safety language, high values and repeat claims.
        5. Case generator produces a traceable record for staff review.

        **Human-in-the-loop boundary:** the agent only recommends and routes.
        It never sends money, creates a replacement order or rejects an exception automatically.
        """
    )

with tab_roi:
    st.subheader("Illustrative ROI model")
    c1, c2, c3 = st.columns(3)
    monthly_claims = c1.number_input("Claims per month", 100, 100000, 5000, step=100)
    minutes_saved = c2.number_input("Minutes saved per claim", 1, 30, 6)
    hourly_cost = c3.number_input("Staff cost per hour (HK$)", 50, 1000, 160)
    hours_saved = monthly_claims * minutes_saved / 60
    monthly_saving = hours_saved * hourly_cost
    m1, m2, m3 = st.columns(3)
    m1.metric("Hours released / month", f"{hours_saved:,.0f}")
    m2.metric("Illustrative saving / month", f"HK${monthly_saving:,.0f}")
    m3.metric("Illustrative saving / year", f"HK${monthly_saving * 12:,.0f}")
    st.caption(
        "Illustrative assumptions only. A real business case should validate volumes, handling time, "
        "error rates, integration cost and customer satisfaction impact."
    )

st.divider()
st.caption(
    "Academic demonstration only. All customers, orders and rules are fictional. "
    "IKEA is a trademark of its respective owner."
)

