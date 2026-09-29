"""
Root Orchestrator – ADK 2.0
Coordinates all specialist agents for complete e-commerce journeys.
"""

from google.adk import Agent
from google.adk.tools import AgentTool

from agents.inventory_agent.agent import inventory_agent
from agents.cart_agent.agent import cart_agent
from agents.customer_agent.agent import customer_agent
from agents.offers_agent.agent import offers_agent
from agents.payment_agent.agent import payment_agent
from agents.shipping_agent.agent import shipping_agent
from agents.fulfillment_agent.agent import fulfillment_agent
from agents.sales_partner_agent.agent import sales_partner_agent
from agents.shopper_agent.agent import shopper_agent
from agents.returns_agent.agent import returns_agent
from agents.loyalty_agent.agent import loyalty_agent
from agents.recommendations_agent.agent import recommendations_agent

tools = [
    AgentTool(agent=inventory_agent),
    AgentTool(agent=cart_agent),
    AgentTool(agent=customer_agent),
    AgentTool(agent=offers_agent),
    AgentTool(agent=payment_agent),
    AgentTool(agent=shipping_agent),
    AgentTool(agent=fulfillment_agent),
    AgentTool(agent=sales_partner_agent),
    AgentTool(agent=shopper_agent),
    AgentTool(agent=returns_agent),
    AgentTool(agent=loyalty_agent),
    AgentTool(agent=recommendations_agent),
]


root_agent = Agent(
    name="commerce_orchestrator",
    model="gemini-2.5-flash",
    description="Master orchestrator for Agent Commerce. Routes every request across the full agent mesh.",
    instruction="""
You are the Commerce Orchestrator powered by Google ADK 2.0.

Specialist agents:
- inventory_agent          → catalogue, stock, uploads
- cart_agent               → cart mutations & view
- customer_agent           → profile & addresses
- offers_agent             → promo codes & discounts
- loyalty_agent            → points earn/redeem, tiers
- recommendations_agent    → similar, FBT, trending, personalized
- payment_agent            → authorize / capture / refund
- shipping_agent           → rates, shipment, tracking, dispatch
- fulfillment_agent        → order lifecycle
- returns_agent            → RMA, labels, refunds, restock hints
- sales_partner_agent      → affiliates & commissions
- shopper_agent            → friendly conversational guide

=== Purchase path ===
1. Browse / search → inventory (+ recommendations_agent for similar/trending)
2. record_view when user views a product
3. Add to cart → cart_agent (+ recommend_for_cart)
4. Optional: offers_agent.evaluate_offers + loyalty_agent.redeem_points
5. Customer + address → customer_agent
6. Shipping rates → shipping_agent (respect free_shipping from offers)
7. Create order → fulfillment_agent (include discount from offers + loyalty)
8. Pay → payment_agent → attach_payment
9. Ship + dispatch → shipping_agent → attach_shipping
10. Commit stock → inventory_agent
11. Redeem offers → offers_agent.redeem_offer
12. Earn points → loyalty_agent.earn_points
13. record_purchase → recommendations_agent

=== Returns path ===
1. returns_agent.request_return
2. approve_return (label) or reject_return
3. mark_received
4. payment_agent.refund_payment + returns_agent.complete_refund
5. inventory_agent (restock if applicable)

Demo promos: WELCOME10, SAVE15, FREESHIP, FOOT20
Loyalty: 1 pt/$1, 100 pts = $1, tiers bronze→platinum

Always name the agent you are using. Never invent IDs, prices, or discounts — use tool results only.
""",
    tools=tools,
)

root_agent = root_agent
