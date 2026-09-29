"""
Returns & Refunds Agent – RMA requests, approval, labels, refunds, restock.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

_RETURNS: Dict[str, dict] = {}

# Policy: days after delivery within which returns are accepted
RETURN_WINDOW_DAYS = 30
RESTOCKING_FEE_PCT = 0.10  # 10% for change-of-mind


def request_return(
    order_id: str,
    customer_id: str,
    items: List[dict],
    order_delivered_at: Optional[str] = None,
) -> dict:
    """
    Start a return request.
    items: [{product_id, sku, name, quantity, unit_price, reason, notes?}]
    reason: defective | wrong_item | not_as_described | size_fit | changed_mind | damaged_in_shipping | other
    """
    if not items:
        return {"error": "At least one item is required"}

    # Simple window check
    if order_delivered_at:
        try:
            delivered = datetime.fromisoformat(order_delivered_at)
            if datetime.utcnow() - delivered > timedelta(days=RETURN_WINDOW_DAYS):
                return {"error": f"Return window of {RETURN_WINDOW_DAYS} days has expired"}
        except Exception:
            pass

    valid_reasons = {
        "defective", "wrong_item", "not_as_described", "size_fit",
        "changed_mind", "damaged_in_shipping", "other",
    }
    return_items = []
    refund_subtotal = 0.0
    restocking = 0.0

    for i in items:
        reason = (i.get("reason") or "other").lower()
        if reason not in valid_reasons:
            return {"error": f"Invalid reason: {reason}"}
        qty = int(i["quantity"])
        price = float(i["unit_price"])
        line = round(price * qty, 2)
        refund_subtotal += line
        if reason == "changed_mind":
            restocking += round(line * RESTOCKING_FEE_PCT, 2)
        return_items.append({
            "product_id": i["product_id"],
            "sku": i.get("sku", ""),
            "name": i.get("name", ""),
            "quantity": qty,
            "unit_price": price,
            "reason": reason,
            "notes": i.get("notes"),
        })

    refund_amount = round(max(0, refund_subtotal - restocking), 2)
    rid = f"RET-{uuid.uuid4().hex[:8].upper()}"

    ret = {
        "id": rid,
        "order_id": order_id,
        "customer_id": customer_id,
        "items": return_items,
        "status": "requested",
        "refund_amount": refund_amount,
        "restocking_fee": restocking,
        "return_shipping_label": None,
        "refund_payment_id": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "notes": None,
    }
    _RETURNS[rid] = ret
    return {
        "return": ret,
        "message": f"Return {rid} requested. Refund estimate: ${refund_amount:.2f}"
        + (f" (restocking fee ${restocking:.2f})" if restocking else ""),
    }


def approve_return(return_id: str) -> dict:
    """Approve a return and generate a return shipping label."""
    ret = _RETURNS.get(return_id)
    if not ret:
        return {"error": f"Return {return_id} not found"}
    if ret["status"] not in ("requested",):
        return {"error": f"Cannot approve return in status {ret['status']}"}
    label = f"RMA-{uuid.uuid4().hex[:10].upper()}"
    ret["status"] = "label_sent"
    ret["return_shipping_label"] = label
    ret["updated_at"] = datetime.utcnow().isoformat()
    return {
        "return": ret,
        "message": f"Return approved. Shipping label: {label}. Customer should ship items back.",
    }


def reject_return(return_id: str, reason: str) -> dict:
    ret = _RETURNS.get(return_id)
    if not ret:
        return {"error": f"Return {return_id} not found"}
    ret["status"] = "rejected"
    ret["notes"] = reason
    ret["updated_at"] = datetime.utcnow().isoformat()
    return {"return": ret, "message": f"Return rejected: {reason}"}


def mark_received(return_id: str) -> dict:
    """Warehouse received the returned items."""
    ret = _RETURNS.get(return_id)
    if not ret:
        return {"error": f"Return {return_id} not found"}
    if ret["status"] not in ("label_sent", "in_transit", "approved"):
        return {"error": f"Unexpected status {ret['status']}"}
    ret["status"] = "received"
    ret["updated_at"] = datetime.utcnow().isoformat()
    return {"return": ret, "message": "Items received at warehouse. Ready for refund."}


def complete_refund(return_id: str, refund_payment_id: Optional[str] = None) -> dict:
    """Mark return as refunded (Payment Agent should have issued the refund)."""
    ret = _RETURNS.get(return_id)
    if not ret:
        return {"error": f"Return {return_id} not found"}
    if ret["status"] != "received":
        return {"error": "Items must be received before refund"}
    ret["status"] = "refunded"
    ret["refund_payment_id"] = refund_payment_id or f"PAY-REF-{uuid.uuid4().hex[:6].upper()}"
    ret["updated_at"] = datetime.utcnow().isoformat()
    return {
        "return": ret,
        "message": f"Refund of ${ret['refund_amount']:.2f} completed. Restock via Inventory Agent if applicable.",
        "items_to_restock": [
            {"product_id": i["product_id"], "quantity": i["quantity"]}
            for i in ret["items"]
            if i["reason"] not in ("defective", "damaged_in_shipping")
        ],
    }


def get_return(return_id: str) -> dict:
    ret = _RETURNS.get(return_id)
    if not ret:
        return {"error": f"Return {return_id} not found"}
    return {"return": ret}


def list_returns(customer_id: Optional[str] = None, order_id: Optional[str] = None) -> dict:
    results = list(_RETURNS.values())
    if customer_id:
        results = [r for r in results if r["customer_id"] == customer_id]
    if order_id:
        results = [r for r in results if r["order_id"] == order_id]
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return {"returns": results, "count": len(results)}


returns_agent = Agent(
    name="returns_agent",
    model="gemini-2.5-flash",
    description="Handles return requests (RMA), approval, shipping labels, warehouse receipt, and refunds.",
    instruction="""
You are the Returns & Refunds Agent.

Flow:
1. request_return (customer initiates with items + reasons)
2. approve_return → generates return label  OR  reject_return
3. mark_received (warehouse)
4. complete_refund (after Payment Agent refunds) → suggest restock via Inventory

Policy:
- 30-day return window after delivery
- 10% restocking fee for "changed_mind"
- Defective / damaged items: full refund, usually no restock

Coordinate with Payment Agent for actual money movement and Inventory Agent for restock.
Always return structured return objects.
""",
    tools=[
        FunctionTool(request_return),
        FunctionTool(approve_return),
        FunctionTool(reject_return),
        FunctionTool(mark_received),
        FunctionTool(complete_refund),
        FunctionTool(get_return),
        FunctionTool(list_returns),
    ],
)

root_agent = returns_agent
