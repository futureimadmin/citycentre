"""
Loyalty / Rewards Agent – points earn/redeem, tiers, balance.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

_ACCOUNTS: Dict[str, dict] = {}
_TRANSACTIONS: List[dict] = []

# Points per dollar spent
EARN_RATE = 1  # 1 point per $1
# Tier thresholds (lifetime points)
TIER_THRESHOLDS = {"bronze": 0, "silver": 500, "gold": 2000, "platinum": 5000}
# Redeem: 100 points = $1
REDEEM_RATE = 100  # points per $1 value


def _tier_for(lifetime: int) -> str:
    if lifetime >= 5000:
        return "platinum"
    if lifetime >= 2000:
        return "gold"
    if lifetime >= 500:
        return "silver"
    return "bronze"


def _get_or_create(customer_id: str) -> dict:
    if customer_id not in _ACCOUNTS:
        _ACCOUNTS[customer_id] = {
            "customer_id": customer_id,
            "points_balance": 0,
            "lifetime_points": 0,
            "tier": "bronze",
            "updated_at": datetime.utcnow().isoformat(),
        }
    return _ACCOUNTS[customer_id]


def get_loyalty_account(customer_id: str) -> dict:
    """Get points balance and tier for a customer."""
    acc = _get_or_create(customer_id)
    return {"account": acc}


def earn_points(
    customer_id: str,
    order_id: str,
    order_total: float,
    description: Optional[str] = None,
) -> dict:
    """Award points after a successful order (typically 1 pt per $1)."""
    points = max(0, int(round(order_total * EARN_RATE)))
    if points == 0:
        return {"message": "No points to award", "points": 0}

    acc = _get_or_create(customer_id)
    acc["points_balance"] += points
    acc["lifetime_points"] += points
    acc["tier"] = _tier_for(acc["lifetime_points"])
    acc["updated_at"] = datetime.utcnow().isoformat()

    tx = {
        "id": f"PTS-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "type": "earn",
        "points": points,
        "order_id": order_id,
        "description": description or f"Earned from order {order_id}",
        "created_at": datetime.utcnow().isoformat(),
    }
    _TRANSACTIONS.append(tx)
    return {
        "account": acc,
        "transaction": tx,
        "message": f"+{points} points. Balance: {acc['points_balance']}. Tier: {acc['tier']}",
    }


def redeem_points(
    customer_id: str,
    points: int,
    order_id: Optional[str] = None,
) -> dict:
    """
    Redeem points for discount value.
    Returns discount_amount in currency (100 pts = $1).
    """
    if points <= 0:
        return {"error": "Points must be positive"}
    if points % REDEEM_RATE != 0:
        return {"error": f"Points must be multiples of {REDEEM_RATE}"}

    acc = _get_or_create(customer_id)
    if acc["points_balance"] < points:
        return {"error": f"Insufficient points. Balance: {acc['points_balance']}"}

    discount = round(points / REDEEM_RATE, 2)
    acc["points_balance"] -= points
    acc["updated_at"] = datetime.utcnow().isoformat()

    tx = {
        "id": f"PTS-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "type": "redeem",
        "points": -points,
        "order_id": order_id,
        "description": f"Redeemed {points} pts for ${discount:.2f}",
        "created_at": datetime.utcnow().isoformat(),
    }
    _TRANSACTIONS.append(tx)
    return {
        "account": acc,
        "transaction": tx,
        "discount_amount": discount,
        "message": f"Redeemed {points} points → ${discount:.2f} off",
    }


def adjust_points(customer_id: str, points: int, reason: str) -> dict:
    """Manual adjustment (positive or negative)."""
    acc = _get_or_create(customer_id)
    acc["points_balance"] = max(0, acc["points_balance"] + points)
    if points > 0:
        acc["lifetime_points"] += points
        acc["tier"] = _tier_for(acc["lifetime_points"])
    acc["updated_at"] = datetime.utcnow().isoformat()
    tx = {
        "id": f"PTS-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "type": "adjust",
        "points": points,
        "order_id": None,
        "description": reason,
        "created_at": datetime.utcnow().isoformat(),
    }
    _TRANSACTIONS.append(tx)
    return {"account": acc, "transaction": tx}


def list_transactions(customer_id: str, limit: int = 20) -> dict:
    txs = [t for t in _TRANSACTIONS if t["customer_id"] == customer_id]
    txs.sort(key=lambda x: x["created_at"], reverse=True)
    return {"transactions": txs[:limit], "count": len(txs)}


def get_tier_benefits(tier: Optional[str] = None) -> dict:
    """Describe tier benefits."""
    benefits = {
        "bronze": {"earn_multiplier": 1.0, "perks": ["Standard support"]},
        "silver": {"earn_multiplier": 1.25, "perks": ["Priority support", "Free returns"]},
        "gold": {"earn_multiplier": 1.5, "perks": ["Free express shipping", "Early access to sales"]},
        "platinum": {"earn_multiplier": 2.0, "perks": ["Dedicated concierge", "Exclusive offers", "Birthday bonus"]},
    }
    if tier:
        t = tier.lower()
        if t not in benefits:
            return {"error": f"Unknown tier {tier}"}
        return {"tier": t, "benefits": benefits[t], "threshold": TIER_THRESHOLDS[t]}
    return {"tiers": benefits, "thresholds": TIER_THRESHOLDS, "earn_rate": f"{EARN_RATE} pt per $1", "redeem_rate": f"{REDEEM_RATE} pts = $1"}


loyalty_agent = Agent(
    name="loyalty_agent",
    model="gemini-2.5-flash",
    description="Manages loyalty points: earn on orders, redeem for discounts, tiers (bronze→platinum).",
    instruction="""
You are the Loyalty / Rewards Agent.

- Earn: typically 1 point per $1 of order total (call after order confirmed)
- Redeem: 100 points = $1 discount (call during checkout; pass discount to Fulfillment/Offers)
- Tiers: Bronze → Silver (500) → Gold (2000) → Platinum (5000) lifetime points

After a successful order, the orchestrator should call earn_points.
During checkout, if the customer wants to use points, call redeem_points and apply the discount_amount.

Always return structured account and transaction objects.
""",
    tools=[
        FunctionTool(get_loyalty_account),
        FunctionTool(earn_points),
        FunctionTool(redeem_points),
        FunctionTool(adjust_points),
        FunctionTool(list_transactions),
        FunctionTool(get_tier_benefits),
    ],
)

root_agent = loyalty_agent
