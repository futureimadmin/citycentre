# Agent Commerce Platform

Fully **agentic e-commerce** with **Google ADK 2.0**, A2A protocol, and Cloud Run microservices.

## All Agents (13)

| Agent | Domain |
|-------|--------|
| Inventory | Catalogue, stock, uploads |
| Cart | Shopping cart |
| Customer | Profiles & addresses |
| Offers | Promo codes & discounts |
| Loyalty | Points & tiers |
| Recommendations | Similar, FBT, personalized |
| Payment | Capture & refunds |
| Shipping | Rates, tracking, dispatch |
| Fulfillment | Order lifecycle |
| Returns | RMA & refunds |
| Sales Partner | Affiliates |
| Shopper | Conversational UX |
| Root Orchestrator | Multi-agent coordination |

## Demo cheatsheet

| Feature | Values |
|---------|--------|
| Promo codes | `WELCOME10` · `SAVE15` · `FREESHIP` · `FOOT20` |
| Loyalty | 1 pt/$1 · 100 pts = $1 · tiers to Platinum |
| Returns | 30-day window · 10% restock fee (change of mind) |

## Quick Start

```bash
pip install "google-adk>=2.0" --pre
cd agents/returns_agent && adk web   # any specialist

cd frontend && npm i && npm run dev
```

## Deploy all to Cloud Run

```bash
export GOOGLE_CLOUD_PROJECT=your-project
./infrastructure/deploy.sh
```

Each agent is an independent Cloud Run service (scale-to-zero).
