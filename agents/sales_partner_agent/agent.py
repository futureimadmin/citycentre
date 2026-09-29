"""
Sales Partner Agent – affiliate / partner channel management.
Partners can upload inventory, track commissions, and receive leads.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional
import uuid

_PARTNERS: dict[str, dict] = {
    "partner_acme": {"name": "Acme Affiliates", "commission_rate": 0.12, "balance": 0.0},
}
_COMMISSIONS: list[dict] = []


def register_partner(name: str, commission_rate: float = 0.10) -> dict:
    pid = f"partner_{uuid.uuid4().hex[:6]}"
    _PARTNERS[pid] = {"name": name, "commission_rate": commission_rate, "balance": 0.0}
    return {"partner_id": pid, "partner": _PARTNERS[pid]}


def record_commission(partner_id: str, order_id: str, order_total: float) -> dict:
    partner = _PARTNERS.get(partner_id)
    if not partner:
        return {"error": "Unknown partner"}
    amount = round(order_total * partner["commission_rate"], 2)
    partner["balance"] += amount
    rec = {
        "id": str(uuid.uuid4()),
        "partner_id": partner_id,
        "order_id": order_id,
        "amount": amount,
        "rate": partner["commission_rate"],
    }
    _COMMISSIONS.append(rec)
    return {"commission": rec, "new_balance": partner["balance"]}


def get_partner_dashboard(partner_id: str) -> dict:
    partner = _PARTNERS.get(partner_id)
    if not partner:
        return {"error": "Unknown partner"}
    commissions = [c for c in _COMMISSIONS if c["partner_id"] == partner_id]
    return {
        "partner": partner,
        "commissions": commissions,
        "total_earned": sum(c["amount"] for c in commissions),
    }


sales_partner_agent = Agent(
    name="sales_partner_agent",
    model="gemini-2.5-flash",
    description="Manages sales partners / affiliates: registration, inventory contribution, and commission tracking.",
    instruction="""
You are the Sales Partner Agent.
You help external partners:
- Register as affiliates
- Upload or contribute inventory (hand off to Inventory Agent)
- View their dashboard and commissions
- Receive attributed leads/orders

Be professional and transparent about commission rates.
""",
    tools=[
        FunctionTool(register_partner),
        FunctionTool(record_commission),
        FunctionTool(get_partner_dashboard),
    ],
)

root_agent = sales_partner_agent
