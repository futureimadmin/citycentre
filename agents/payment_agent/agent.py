"""
Payment Agent – authorize / capture payments.
In production integrate Stripe, Razorpay, or a payment MCP server.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

_PAYMENTS: Dict[str, dict] = {}


def authorize_payment(
    order_id: str,
    amount: float,
    method: str = "card",
    currency: str = "USD",
    payment_token: Optional[str] = None,
    customer_id: Optional[str] = None,
) -> dict:
    """
    Authorize (and for demo, auto-capture) a payment.
    method: card | upi | netbanking | wallet | cod
    """
    method = method.lower()
    if method not in ("card", "upi", "netbanking", "wallet", "cod"):
        return {"error": f"Unsupported payment method: {method}"}

    pid = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    status = "captured" if method != "cod" else "pending"

    # Simulate gateway
    gateway_ref = f"gw_{uuid.uuid4().hex[:12]}" if method != "cod" else None
    if method != "cod" and payment_token is None and amount > 0:
        # In real system we would require a token from the frontend SDK
        gateway_ref = f"sim_{uuid.uuid4().hex[:10]}"

    payment = {
        "id": pid,
        "order_id": order_id,
        "amount": round(amount, 2),
        "currency": currency,
        "method": method,
        "status": status,
        "gateway_ref": gateway_ref,
        "customer_id": customer_id,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {},
    }
    _PAYMENTS[pid] = payment

    if status == "captured":
        return {
            "payment": payment,
            "message": f"Payment of {currency} {amount:.2f} captured successfully.",
            "success": True,
        }
    return {
        "payment": payment,
        "message": "Cash-on-delivery order registered. Payment pending.",
        "success": True,
    }


def get_payment(payment_id: str) -> dict:
    p = _PAYMENTS.get(payment_id)
    if not p:
        return {"error": f"Payment {payment_id} not found"}
    return {"payment": p}


def refund_payment(payment_id: str, amount: Optional[float] = None) -> dict:
    p = _PAYMENTS.get(payment_id)
    if not p:
        return {"error": f"Payment {payment_id} not found"}
    if p["status"] not in ("captured", "authorized"):
        return {"error": f"Cannot refund payment in status {p['status']}"}
    refund_amount = amount if amount is not None else p["amount"]
    p["status"] = "refunded"
    p["refund_amount"] = refund_amount
    p["refunded_at"] = datetime.utcnow().isoformat()
    return {"payment": p, "message": f"Refunded {p['currency']} {refund_amount:.2f}"}


payment_agent = Agent(
    name="payment_agent",
    model="gemini-2.5-flash",
    description="Handles payment authorization, capture, and refunds for orders.",
    instruction="""
You are the Payment Agent.
You process payments for orders.

Supported methods: card, upi, netbanking, wallet, cod.
For non-COD you normally expect a payment_token from the frontend.
In this demo environment you may simulate success.

Always return the full payment object with status.
Never claim a payment succeeded if the tool returns an error.
""",
    tools=[
        FunctionTool(authorize_payment),
        FunctionTool(get_payment),
        FunctionTool(refund_payment),
    ],
)

root_agent = payment_agent
