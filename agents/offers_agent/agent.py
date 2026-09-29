"""
Offers / Promotions Agent – create, evaluate, and apply discounts.
Integrates with Cart (preview) and Fulfillment (final order totals).
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

_OFFERS: Dict[str, dict] = {}
_REDEMPTIONS: List[dict] = []  # {offer_id, customer_id, order_id, at}


def _seed_offers():
    """Demo offers so the system is usable out of the box."""
    if _OFFERS:
        return
    now = datetime.utcnow()
    seeds = [
        {
            "id": "OFF-WELCOME10",
            "code": "WELCOME10",
            "name": "Welcome 10% Off",
            "description": "10% off your first order",
            "type": "percentage",
            "value": 10.0,
            "min_subtotal": 0.0,
            "max_discount": 50.0,
            "applicable_product_ids": [],
            "applicable_categories": [],
            "excluded_product_ids": [],
            "usage_limit": None,
            "usage_count": 0,
            "per_customer_limit": 1,
            "partner_id": None,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=365)).isoformat(),
            "status": "active",
            "stackable": False,
            "created_at": now.isoformat(),
        },
        {
            "id": "OFF-SAVE15",
            "code": "SAVE15",
            "name": "$15 Off Orders $75+",
            "description": "Flat $15 discount when subtotal >= $75",
            "type": "fixed_amount",
            "value": 15.0,
            "min_subtotal": 75.0,
            "max_discount": None,
            "applicable_product_ids": [],
            "applicable_categories": [],
            "excluded_product_ids": [],
            "usage_limit": 1000,
            "usage_count": 0,
            "per_customer_limit": 3,
            "partner_id": None,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=90)).isoformat(),
            "status": "active",
            "stackable": False,
            "created_at": now.isoformat(),
        },
        {
            "id": "OFF-FREESHIP",
            "code": "FREESHIP",
            "name": "Free Standard Shipping",
            "description": "Free standard shipping on any order",
            "type": "free_shipping",
            "value": 0.0,
            "min_subtotal": 0.0,
            "max_discount": None,
            "applicable_product_ids": [],
            "applicable_categories": [],
            "excluded_product_ids": [],
            "usage_limit": None,
            "usage_count": 0,
            "per_customer_limit": 10,
            "partner_id": None,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=180)).isoformat(),
            "status": "active",
            "stackable": True,
            "created_at": now.isoformat(),
        },
        {
            "id": "OFF-FOOT20",
            "code": "FOOT20",
            "name": "20% Off Footwear",
            "description": "20% off all Footwear category items",
            "type": "percentage",
            "value": 20.0,
            "min_subtotal": 0.0,
            "max_discount": 40.0,
            "applicable_product_ids": [],
            "applicable_categories": ["Footwear"],
            "excluded_product_ids": [],
            "usage_limit": None,
            "usage_count": 0,
            "per_customer_limit": 5,
            "partner_id": None,
            "starts_at": (now - timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=60)).isoformat(),
            "status": "active",
            "stackable": False,
            "created_at": now.isoformat(),
        },
    ]
    for s in seeds:
        _OFFERS[s["id"]] = s


_seed_offers()


def _is_active(offer: dict, now: datetime) -> bool:
    if offer.get("status") != "active":
        return False
    starts = offer.get("starts_at")
    ends = offer.get("ends_at")
    if starts and datetime.fromisoformat(starts) > now:
        return False
    if ends and datetime.fromisoformat(ends) < now:
        return False
    limit = offer.get("usage_limit")
    if limit is not None and offer.get("usage_count", 0) >= limit:
        return False
    return True


def _customer_redemption_count(offer_id: str, customer_id: Optional[str]) -> int:
    if not customer_id:
        return 0
    return sum(1 for r in _REDEMPTIONS if r["offer_id"] == offer_id and r.get("customer_id") == customer_id)


def create_offer(
    name: str,
    type: str,
    value: float,
    code: Optional[str] = None,
    description: str = "",
    min_subtotal: float = 0.0,
    max_discount: Optional[float] = None,
    applicable_categories: Optional[List[str]] = None,
    applicable_product_ids: Optional[List[str]] = None,
    usage_limit: Optional[int] = None,
    per_customer_limit: int = 1,
    partner_id: Optional[str] = None,
    days_valid: int = 30,
    stackable: bool = False,
) -> dict:
    """Create a new promotional offer."""
    type = type.lower()
    if type not in ("percentage", "fixed_amount", "free_shipping", "bogo", "bundle"):
        return {"error": f"Unsupported offer type: {type}"}
    if type == "percentage" and (value < 0 or value > 100):
        return {"error": "Percentage value must be 0-100"}

    oid = f"OFF-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    offer = {
        "id": oid,
        "code": code.upper() if code else None,
        "name": name,
        "description": description,
        "type": type,
        "value": float(value),
        "min_subtotal": float(min_subtotal),
        "max_discount": max_discount,
        "applicable_product_ids": applicable_product_ids or [],
        "applicable_categories": applicable_categories or [],
        "excluded_product_ids": [],
        "usage_limit": usage_limit,
        "usage_count": 0,
        "per_customer_limit": per_customer_limit,
        "partner_id": partner_id,
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(days=days_valid)).isoformat(),
        "status": "active",
        "stackable": stackable,
        "created_at": now.isoformat(),
    }
    _OFFERS[oid] = offer
    return {"offer": offer, "message": f"Offer {oid} created" + (f" with code {offer['code']}" if offer["code"] else "")}


def list_offers(status: str = "active", partner_id: Optional[str] = None) -> dict:
    """List offers, optionally filtered by status or partner."""
    now = datetime.utcnow()
    results = []
    for o in _OFFERS.values():
        if status and o.get("status") != status:
            continue
        if partner_id and o.get("partner_id") != partner_id:
            continue
        if status == "active" and not _is_active(o, now):
            continue
        results.append(o)
    return {"offers": results, "count": len(results)}


def get_offer(offer_id: Optional[str] = None, code: Optional[str] = None) -> dict:
    """Lookup offer by id or promo code."""
    if offer_id:
        o = _OFFERS.get(offer_id)
        if not o:
            return {"error": f"Offer {offer_id} not found"}
        return {"offer": o}
    if code:
        code = code.upper().strip()
        for o in _OFFERS.values():
            if o.get("code") == code:
                return {"offer": o}
        return {"error": f"No offer with code {code}"}
    return {"error": "Provide offer_id or code"}


def evaluate_offers(
    cart_items: List[dict],
    subtotal: float,
    codes: Optional[List[str]] = None,
    customer_id: Optional[str] = None,
    shipping_method: str = "standard",
) -> dict:
    """
    Evaluate which offers apply to the current cart and compute total discount.
    cart_items: [{product_id, name, unit_price, quantity, category?}]
    codes: optional list of promo codes the user entered.
    """
    now = datetime.utcnow()
    codes = [c.upper().strip() for c in (codes or [])]
    applied: List[dict] = []
    messages: List[str] = []
    total_discount = 0.0
    free_shipping = False
    used_non_stackable = False

    # Candidate offers: explicit codes + auto-applicable (no code required)
    candidates = []
    for o in _OFFERS.values():
        if not _is_active(o, now):
            continue
        if o.get("code"):
            if o["code"] not in codes:
                continue
        # auto offers (no code) are always considered
        candidates.append(o)

    # Also include any coded offer that was requested even if we already have it
    for code in codes:
        found = False
        for o in _OFFERS.values():
            if o.get("code") == code:
                found = True
                if o not in candidates and _is_active(o, now):
                    candidates.append(o)
                break
        if not found:
            messages.append(f"Code '{code}' is invalid or expired.")

    for offer in candidates:
        # per-customer limit
        if customer_id and _customer_redemption_count(offer["id"], customer_id) >= offer.get("per_customer_limit", 1):
            messages.append(f"You have already used '{offer.get('code') or offer['name']}' the maximum times.")
            continue

        if subtotal < offer.get("min_subtotal", 0):
            messages.append(
                f"'{offer.get('code') or offer['name']}' requires min subtotal ${offer['min_subtotal']:.2f}."
            )
            continue

        if used_non_stackable and not offer.get("stackable"):
            messages.append(f"'{offer.get('code') or offer['name']}' cannot be combined with other offers.")
            continue

        discount = 0.0
        is_free_ship = False
        otype = offer["type"]

        # Eligible line items
        eligible_items = cart_items
        cats = offer.get("applicable_categories") or []
        pids = offer.get("applicable_product_ids") or []
        if cats or pids:
            eligible_items = [
                i for i in cart_items
                if (pids and i.get("product_id") in pids)
                or (cats and i.get("category") in cats)
            ]
            if not eligible_items:
                messages.append(f"'{offer.get('code') or offer['name']}' does not apply to items in your cart.")
                continue

        eligible_subtotal = sum(i["unit_price"] * i["quantity"] for i in eligible_items)

        if otype == "percentage":
            discount = eligible_subtotal * (offer["value"] / 100.0)
            if offer.get("max_discount") is not None:
                discount = min(discount, offer["max_discount"])
        elif otype == "fixed_amount":
            discount = min(offer["value"], eligible_subtotal)
        elif otype == "free_shipping":
            is_free_ship = True
            discount = 0.0
        elif otype == "bogo":
            # Simple BOGO: discount cheapest item among eligible when qty >= 2
            if sum(i["quantity"] for i in eligible_items) >= 2:
                cheapest = min(i["unit_price"] for i in eligible_items)
                discount = cheapest
            else:
                messages.append(f"BOGO '{offer.get('code') or offer['name']}' needs at least 2 eligible items.")
                continue
        else:
            continue

        discount = round(discount, 2)
        applied.append({
            "offer_id": offer["id"],
            "code": offer.get("code"),
            "name": offer["name"],
            "type": otype,
            "discount_amount": discount,
            "free_shipping": is_free_ship,
        })
        total_discount += discount
        if is_free_ship:
            free_shipping = True
        if not offer.get("stackable"):
            used_non_stackable = True

    total_discount = round(min(total_discount, subtotal), 2)
    return {
        "applicable": applied,
        "total_discount": total_discount,
        "free_shipping": free_shipping,
        "messages": messages,
        "final_subtotal_after_discount": round(subtotal - total_discount, 2),
    }


def redeem_offer(
    offer_id: str,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
) -> dict:
    """Record that an offer was successfully used on an order."""
    offer = _OFFERS.get(offer_id)
    if not offer:
        return {"error": f"Offer {offer_id} not found"}
    offer["usage_count"] = offer.get("usage_count", 0) + 1
    _REDEMPTIONS.append({
        "offer_id": offer_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "at": datetime.utcnow().isoformat(),
    })
    return {"message": f"Offer {offer_id} redeemed", "usage_count": offer["usage_count"]}


def deactivate_offer(offer_id: str) -> dict:
    offer = _OFFERS.get(offer_id)
    if not offer:
        return {"error": f"Offer {offer_id} not found"}
    offer["status"] = "paused"
    return {"offer": offer, "message": f"Offer {offer_id} paused"}


offers_agent = Agent(
    name="offers_agent",
    model="gemini-2.5-flash",
    description="Creates and evaluates promotional offers, promo codes, and discounts. Used at cart preview and order finalization.",
    instruction="""
You are the Offers / Promotions Agent for Agent Commerce.

Capabilities:
- Create offers (percentage, fixed amount, free shipping, BOGO)
- List / lookup offers by id or promo code
- Evaluate which offers apply to a cart (given items + subtotal + optional codes)
- Redeem an offer after a successful order
- Deactivate / pause offers

When evaluating:
- Respect min_subtotal, category/product restrictions, usage limits, stackability
- Return structured AppliedOffer list + total_discount + free_shipping flag

Demo codes available: WELCOME10, SAVE15, FREESHIP, FOOT20.
Always return structured data. Never invent discounts that the tools did not compute.
""",
    tools=[
        FunctionTool(create_offer),
        FunctionTool(list_offers),
        FunctionTool(get_offer),
        FunctionTool(evaluate_offers),
        FunctionTool(redeem_offer),
        FunctionTool(deactivate_offer),
    ],
)

root_agent = offers_agent
