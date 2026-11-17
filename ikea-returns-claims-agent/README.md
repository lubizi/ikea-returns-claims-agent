# IKEA Returns & Claims AI Agent

A Streamlit classroom prototype that demonstrates how an AI-style business agent can
handle the first stage of retail returns and claims while keeping consequential actions
under human control.

> Academic demonstration only. This project is not affiliated with IKEA. All customers,
> orders and policy rules are fictional. The application does not connect to real IKEA,
> payment, logistics or customer systems.

## What the agent does

1. Classifies the request.
2. Looks up and verifies a fictional order.
3. Applies transparent simulated policy rules.
4. Checks evidence requirements.
5. triggers safety, fraud and value guardrails.
6. Produces a recommendation and audit trail for staff confirmation.

It never issues a refund, sends a replacement or rejects an exception automatically.

## Demo accounts

| Scenario | Order | Email |
|---|---|---|
| Standard damage claim | `HK-2026-1001` | `alex.chan@example.com` |
| High-value claim | `HK-2026-1002` | `jamie.wong@example.com` |
| Product safety escalation | `HK-2026-1003` | `sam.lee@example.com` |
| Late / repeat claim | `HK-2026-1004` | `taylor.lam@example.com` |

The sidebar can prefill all main scenarios.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
pytest -q
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in at [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Create an app and select this repository.
4. Set the entrypoint to `app.py` and deploy.

No API key or other secret is required for the deterministic demo.

## Architecture

The decision engine is separated from the UI:

- `app.py` — Streamlit presentation and case intake.
- `agent.py` — deterministic workflow, policy and guardrails.
- `data/orders.json` — fictional order lookup tool.
- `tests/test_agent.py` — workflow and safety regression tests.

