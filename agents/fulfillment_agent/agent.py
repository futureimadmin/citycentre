"""
Order / Fulfillment Agent – order lifecycle from checkout to delivery.
Coordinates Cart → Payment → Shipping → Dispatch → Inventory commit.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

_ORDERS: Dict[str, dict] = {}


def create_order(
    customer_id: str,
    items: List[dict],
    shipping_address: dict,
    shipping_cost: float = 0.0,
    tax: float = 0.0,
    discount: float = 0.0,
    cart_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Create an order from cart items + shipping address.
    Status starts as pending_payment.
    items: list of {product_id, sku, name, unit_price, quantity}
    """
    if not items:
        return {"error": "Cannot create order with empty items"}
    if not shipping_address:
        return {"error": "shipping_address is required"}

    order_items = []
    subtotal = 0.0
    for i in items:
        qty = int(i["quantity"])
        price = float(i["unit_price"])
        line = round(price * qty, 2)
        subtotal += line
        order_items.append({
            "product_id": i["product_id"],
            "sku": i.get("sku", ""),
            "name": i.get("name", ""),
            "unit_price": price,
            "quantity": qty,
            "line_total": line,
        })

    total = round(subtotal + shipping_cost + tax - discount, 2)
    oid = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    order = {
        "id": oid,
        "customer_id": customer_id,
        "cart_id": cart_id,
        "items": order_items,
        "subtotal": round(subtotal, 2),
        "shipping_cost": shipping_cost,
        "tax": tax,
        "discount": discount,
        "total": total,
        "currency": "USD",
        "status": "pending_payment",
        "shipping_address": shipping_address,
        "billing_address": shipping_address,
        "payment_id": None,
        "shipping_id": None,
        "dispatch_id": None,
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _ORDERS[oid] = order
    return {
        "order": order,
        "message": f"Order {oid} created. Total: ${total:.2f}. Awaiting payment.",
    }


def attach_payment(order_id: str, payment_id: str) -> dict:
    """Link a successful payment and move order to confirmed."""
    order = _ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    order["payment_id"] = payment_id
    order["status"] = "confirmed"
    order["updated_at"] = datetime.utcnow().isoformat()
    return {"order": order, "message": f"Order {order_id} confirmed after payment."}


def attach_shipping(order_id: str, shipping_id: str, dispatch_id: Optional[str] = None) -> dict:
    """Link shipment (and optional dispatch) and update status."""
    order = _ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    order["shipping_id"] = shipping_id
    if dispatch_id:
        order["dispatch_id"] = dispatch_id
    order["status"] = "processing"
    order["updated_at"] = datetime.utcnow().isoformat()
    return {"order": order}


def update_order_status(order_id: str, status: str) -> dict:
    """Advance order status: confirmed → processing → dispatched → shipped → delivered."""
    allowed = {
        "confirmed", "processing", "dispatched", "shipped",
        "delivered", "cancelled", "refunded",
    }
    if status not in allowed:
        return {"error": f"Invalid status {status}"}
    order = _ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    order["status"] = status
    order["updated_at"] = datetime.utcnow().isoformat()
    return {"order": order, "message": f"Order {order_id} is now {status}"}


def get_order(order_id: str) -> dict:
    order = _ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    return {"order": order}


def list_orders(customer_id: str) -> dict:
    orders = [o for o in _ORDERS.values() if o["customer_id"] == customer_id]
    orders.sort(key=lambda x: x["created_at"], reverse=True)
    return {"orders": orders, "count": len(orders)}


def cancel_order(order_id: str, reason: Optional[str] = None) -> dict:
    order = _ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    if order["status"] in ("shipped", "delivered", "cancelled"):
        return {"error": f"Cannot cancel order in status {order['status']}"}
    order["status"] = "cancelled"
    order["notes"] = (order.get("notes") or "") + f" | Cancelled: {reason or 'user request'}"
    order["updated_at"] = datetime.utcnow().isoformat()
    return {"order": order, "message": f"Order {order_id} cancelled. Stock should be released."}


fulfillment_agent = Agent(
    name="fulfillment_agent",
    model="gemini-2.5-flash",
    description="Owns the order lifecycle: create order, attach payment & shipping, status updates, cancellation.",
    instruction="""
You are the Order / Fulfillment Agent.

End-to-end checkout flow you participate in:
1. Cart Agent provides items
2. Customer Agent provides address
3. You create the order (status = pending_payment)
4. Payment Agent authorizes → you attach_payment → status = confirmed
5. Shipping Agent creates shipment + dispatch → you attach_shipping → status = processing
6. Later: update to dispatched / shipped / delivered

You also list orders for a customer and support cancellation (with stock release via Inventory Agent).

Always return the full order object.
""",
    tools=[
        FunctionTool(create_order),
        FunctionTool(attach_payment),
        FunctionTool(attach_shipping),
        FunctionTool(update_order_status),
        FunctionTool(get_order),
        FunctionTool(list_orders),
        FunctionTool(cancel_order),
    ],
)

root_agent = fulfillment_agent
