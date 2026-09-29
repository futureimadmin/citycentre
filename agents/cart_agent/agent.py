"""
Cart Agent – persistent shopping cart management.
Owns cart lifecycle: add/remove/update, reserve stock, hand-off to checkout.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# In-memory store (replace with Redis / Firestore in production)
_CARTS: Dict[str, dict] = {}
# Simple product lookup (in production call Inventory/Catalogue Agent via A2A)
_PRODUCTS: Dict[str, dict] = {
    "PRD-DEMO01": {
        "id": "PRD-DEMO01", "sku": "SHOE-RUN-01", "name": "AeroRun Pro Shoes",
        "price": 129.99, "stock": 50, "image": "", "attributes": {"size": "10", "color": "black"}
    },
    "PRD-DEMO02": {
        "id": "PRD-DEMO02", "sku": "HEAD-WL-02", "name": "SonicWave Headphones",
        "price": 89.50, "stock": 120, "image": "", "attributes": {}
    },
}


def _get_or_create_cart(session_id: str, customer_id: Optional[str] = None) -> dict:
    if session_id not in _CARTS:
        _CARTS[session_id] = {
            "id": f"CART-{uuid.uuid4().hex[:8].upper()}",
            "session_id": session_id,
            "customer_id": customer_id,
            "items": [],
            "currency": "USD",
            "updated_at": datetime.utcnow().isoformat(),
        }
    cart = _CARTS[session_id]
    if customer_id and not cart.get("customer_id"):
        cart["customer_id"] = customer_id
    return cart


def _recalc(cart: dict) -> dict:
    subtotal = sum(i["unit_price"] * i["quantity"] for i in cart["items"])
    cart["subtotal"] = round(subtotal, 2)
    cart["item_count"] = sum(i["quantity"] for i in cart["items"])
    cart["updated_at"] = datetime.utcnow().isoformat()
    return cart


def add_item(
    session_id: str,
    product_id: str,
    quantity: int = 1,
    customer_id: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> dict:
    """Add a product to the cart. Validates stock."""
    product = _PRODUCTS.get(product_id)
    if not product:
        return {"error": f"Product {product_id} not found. Ask Catalogue Agent for available products."}
    if product["stock"] < quantity:
        return {"error": f"Only {product['stock']} units available for {product['name']}"}

    cart = _get_or_create_cart(session_id, customer_id)
    attrs = attributes or product.get("attributes", {})

    for item in cart["items"]:
        if item["product_id"] == product_id and item.get("attributes") == attrs:
            item["quantity"] += quantity
            break
    else:
        cart["items"].append({
            "product_id": product_id,
            "sku": product["sku"],
            "name": product["name"],
            "unit_price": product["price"],
            "quantity": quantity,
            "image": product.get("image"),
            "attributes": attrs,
        })

    _recalc(cart)
    return {"cart": cart, "message": f"Added {quantity} × {product['name']}"}


def update_item_quantity(session_id: str, product_id: str, quantity: int) -> dict:
    """Set absolute quantity for a cart line. Quantity 0 removes the item."""
    cart = _CARTS.get(session_id)
    if not cart:
        return {"error": "Cart not found"}
    if quantity < 0:
        return {"error": "Quantity cannot be negative"}

    new_items = []
    found = False
    for item in cart["items"]:
        if item["product_id"] == product_id:
            found = True
            if quantity > 0:
                item["quantity"] = quantity
                new_items.append(item)
        else:
            new_items.append(item)
    if not found:
        return {"error": f"Product {product_id} not in cart"}
    cart["items"] = new_items
    _recalc(cart)
    return {"cart": cart}


def remove_item(session_id: str, product_id: str) -> dict:
    """Remove a product from the cart."""
    return update_item_quantity(session_id, product_id, 0)


def view_cart(session_id: str) -> dict:
    """Return current cart contents and totals."""
    cart = _CARTS.get(session_id)
    if not cart:
        return {"cart": None, "message": "Cart is empty"}
    _recalc(cart)
    return {"cart": cart}


def clear_cart(session_id: str) -> dict:
    """Empty the cart."""
    if session_id in _CARTS:
        _CARTS[session_id]["items"] = []
        _recalc(_CARTS[session_id])
    return {"message": "Cart cleared", "cart": _CARTS.get(session_id)}


def attach_customer(session_id: str, customer_id: str) -> dict:
    """Link a guest cart to a logged-in customer."""
    cart = _get_or_create_cart(session_id, customer_id)
    cart["customer_id"] = customer_id
    return {"cart": cart}


cart_agent = Agent(
    name="cart_agent",
    model="gemini-2.5-flash",
    description="Manages the shopping cart: add/remove/update items, view totals, prepare for checkout.",
    instruction="""
You are the Cart Agent for Agent Commerce.
You own the shopping cart for a session (or customer).

Responsibilities:
- Add products (validate stock via product data)
- Update quantities or remove items
- Show cart summary (items, subtotal, count)
- Clear cart
- Attach a customer_id when the user logs in

Always return the full cart object after mutations so the orchestrator and UI stay in sync.
If a product is missing, tell the user to ask the Catalogue/Inventory Agent.
Never invent products or prices.
When the user mentions a promo code, ask the Offers Agent (via orchestrator) to evaluate_offers and then show the discounted total.
""",
    tools=[
        FunctionTool(add_item),
        FunctionTool(update_item_quantity),
        FunctionTool(remove_item),
        FunctionTool(view_cart),
        FunctionTool(clear_cart),
        FunctionTool(attach_customer),
    ],
)

root_agent = cart_agent
