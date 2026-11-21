"""Streamlit interface for the IKEA Returns & Claims AI Agent prototype."""

from __future__ import annotations

import json

import streamlit as st

from llm_agent import run_llm_agent


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
    </div>
    """,
    unsafe_allow_html=True,
)

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


tab_claim, tab_chat, tab_architecture, tab_roi = st.tabs(
    ["Submit & assess claim", "Chat with Agent", "Agent workflow", "Business value"]
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
                ["Return / changed mind", "Damaged item", "Missing part", "Wrong item", "Refund delay"],
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
        if not order_id.strip():
            st.error("Please enter the order number.")
        else:
            # Build a natural-language ticket for the LLM agent
            ticket = f"""
    Order ID: {order_id}
    Purchasing email: {email}
    Issue type: {issue_type}
    Description: {description}
    Requested resolution: {requested_resolution}
    Evidence provided: {evidence_provided}
    Item opened or assembled: {assembled}
    """
            with st.spinner("Agent is gathering data and evaluating the claim..."):
                st.session_state["result"] = run_llm_agent(ticket)

    result = st.session_state.get("result")
    if result:
        st.divider()
        st.subheader("Agent Response")
        st.success(result["final_message"])
    
        st.subheader("Tools Called by the Agent")
        if result.get("tool_trace"):
            for i, step in enumerate(result["tool_trace"], 1):
                with st.expander(f"{i}. {step['tool']}"):
                    st.write("Arguments:")
                    st.json(step["args"])
                    st.write("Result:")
                    st.code(step["result"], language="json")
        else:
            st.info("No tools were called.")
    
        st.caption(f"Status: {result.get('status', 'COMPLETED')}")

with tab_chat:
    st.subheader("Chat with the Returns & Claims Agent")
    st.caption("You can ask follow-up questions. The agent remembers the conversation.")

    # 1. Initialise chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # 2. Display all existing messages FIRST
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3. Chat input comes LAST (this keeps it at the bottom)
    if prompt := st.chat_input("Type your message (e.g. I want a refund for order ORD-1001)"):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent reply
        with st.chat_message("assistant"):
            with st.spinner("Agent is thinking..."):
                result = run_llm_agent(prompt)
                reply = result.get("final_message", "Sorry, I could not process that.")
                st.markdown(reply)

                if result.get("tool_trace"):
                    with st.expander("Tools called"):
                        for step in result["tool_trace"]:
                            st.write(f"**{step['tool']}**")
                            st.json(step["args"])

        # Save assistant reply
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})

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

