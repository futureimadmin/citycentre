"""
Shopper Agent – friendly conversational front for discovery & guidance.
Delegates cart, catalogue, and checkout steps to specialist agents via the orchestrator.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional

# Lightweight helpers for demo when called directly
def suggest_products(query: str) -> dict:
    """Return a helpful shopping suggestion based on a free-text query."""
    return {
        "suggestion": f"I recommend searching the catalogue for '{query}'. "
                      "Try asking the Inventory Agent or say 'show me products related to {query}'.",
        "next_steps": [
            "Browse catalogue",
            "Add items to cart",
            "Proceed to checkout",
        ],
    }


shopper_agent = Agent(
    name="shopper_agent",
    model="gemini-2.5-flash",
    description="Friendly shopping assistant that helps users discover products and guides them through the purchase journey.",
    instruction="""
You are a warm, knowledgeable shopping assistant for Agent Commerce.

Your job is to:
- Understand what the shopper wants
- Suggest products and categories
- Guide them to add items to cart
- Explain next steps toward checkout

You do NOT own the cart or catalogue yourself – those live in Cart Agent and Inventory Agent.
When the user is ready to act, clearly tell them (or the orchestrator) which specialist to invoke.

Be concise, helpful, and never invent product data or prices.
""",
    tools=[
        FunctionTool(suggest_products),
    ],
)

root_agent = shopper_agent
