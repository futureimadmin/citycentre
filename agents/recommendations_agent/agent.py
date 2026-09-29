"""
Personalization / Recommendations Agent – similar products, FBT, trending, personalized.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# Lightweight catalogue mirror for demo scoring (production: call Inventory via A2A)
_CATALOGUE = {
    "PRD-DEMO01": {
        "id": "PRD-DEMO01", "name": "AeroRun Pro Shoes", "category": "Footwear",
        "tags": ["running", "sport", "lightweight"], "price": 129.99,
    },
    "PRD-DEMO02": {
        "id": "PRD-DEMO02", "name": "SonicWave Headphones", "category": "Electronics",
        "tags": ["headphones", "wireless", "audio"], "price": 89.50,
    },
    "PRD-DEMO03": {
        "id": "PRD-DEMO03", "name": "TrailDay Backpack 25L", "category": "Bags",
        "tags": ["backpack", "outdoor", "travel"], "price": 64.00,
    },
    "PRD-DEMO04": {
        "id": "PRD-DEMO04", "name": "PaceRun Socks (3-pack)", "category": "Footwear",
        "tags": ["running", "socks", "sport"], "price": 18.00,
    },
    "PRD-DEMO05": {
        "id": "PRD-DEMO05", "name": "AudioCase Pro", "category": "Electronics",
        "tags": ["headphones", "case", "accessories"], "price": 24.99,
    },
}

# Simple co-occurrence for FBT
_FBT = {
    "PRD-DEMO01": ["PRD-DEMO04", "PRD-DEMO03"],  # shoes → socks, backpack
    "PRD-DEMO02": ["PRD-DEMO05"],                 # headphones → case
    "PRD-DEMO03": ["PRD-DEMO01"],
}

# Per-customer signals (views, purchases) – demo in-memory
_CUSTOMER_SIGNALS: Dict[str, dict] = {}  # customer_id -> {viewed: [], purchased: []}


def _score_similar(source: dict, candidate: dict) -> float:
    score = 0.0
    if source["category"] == candidate["category"]:
        score += 0.5
    src_tags = set(source.get("tags", []))
    cand_tags = set(candidate.get("tags", []))
    if src_tags and cand_tags:
        score += 0.4 * (len(src_tags & cand_tags) / len(src_tags | cand_tags))
    # Prefer similar price band
    if source["price"] > 0:
        ratio = min(source["price"], candidate["price"]) / max(source["price"], candidate["price"])
        score += 0.1 * ratio
    return round(score, 3)


def recommend_similar(product_id: str, limit: int = 5) -> dict:
    """Find products similar to the given product."""
    source = _CATALOGUE.get(product_id)
    if not source:
        return {"error": f"Product {product_id} not found", "recommendations": []}
    scored = []
    for pid, p in _CATALOGUE.items():
        if pid == product_id:
            continue
        s = _score_similar(source, p)
        if s > 0.1:
            scored.append({
                "product_id": pid,
                "name": p["name"],
                "price": p["price"],
                "category": p["category"],
                "score": s,
                "reason": f"Similar to {source['name']} (category/tags)",
                "type": "similar",
            })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"recommendations": scored[:limit], "source_product_id": product_id}


def recommend_frequently_bought_together(product_id: str, limit: int = 3) -> dict:
    """Products often bought with the given product."""
    ids = _FBT.get(product_id, [])
    recs = []
    for pid in ids[:limit]:
        p = _CATALOGUE.get(pid)
        if p:
            recs.append({
                "product_id": pid,
                "name": p["name"],
                "price": p["price"],
                "category": p["category"],
                "score": 0.9,
                "reason": "Frequently bought together",
                "type": "frequently_bought_together",
            })
    return {"recommendations": recs, "source_product_id": product_id}


def recommend_trending(category: Optional[str] = None, limit: int = 5) -> dict:
    """Trending products (demo: highest price as proxy + category filter)."""
    products = list(_CATALOGUE.values())
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    products = sorted(products, key=lambda p: p["price"], reverse=True)
    recs = [
        {
            "product_id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "category": p["category"],
            "score": 0.7,
            "reason": "Trending in catalogue",
            "type": "trending",
        }
        for p in products[:limit]
    ]
    return {"recommendations": recs}


def record_view(customer_id: str, product_id: str) -> dict:
    """Record that a customer viewed a product (for personalization)."""
    sig = _CUSTOMER_SIGNALS.setdefault(customer_id, {"viewed": [], "purchased": []})
    if product_id not in sig["viewed"]:
        sig["viewed"].append(product_id)
    # keep last 20
    sig["viewed"] = sig["viewed"][-20:]
    return {"message": "View recorded", "viewed_count": len(sig["viewed"])}


def record_purchase(customer_id: str, product_ids: List[str]) -> dict:
    """Record purchased products for a customer."""
    sig = _CUSTOMER_SIGNALS.setdefault(customer_id, {"viewed": [], "purchased": []})
    for pid in product_ids:
        if pid not in sig["purchased"]:
            sig["purchased"].append(pid)
    return {"message": "Purchase recorded", "purchased_count": len(sig["purchased"])}


def recommend_personalized(customer_id: str, limit: int = 5) -> dict:
    """Personalized recommendations based on viewed/purchased history."""
    sig = _CUSTOMER_SIGNALS.get(customer_id, {"viewed": [], "purchased": []})
    seed_ids = list(dict.fromkeys(sig["purchased"] + sig["viewed"]))  # preserve order, unique
    if not seed_ids:
        # cold start → trending
        return recommend_trending(limit=limit)

    scores: Dict[str, float] = {}
    reasons: Dict[str, str] = {}
    for seed in seed_ids:
        source = _CATALOGUE.get(seed)
        if not source:
            continue
        for pid, p in _CATALOGUE.items():
            if pid == seed or pid in seed_ids:
                continue
            s = _score_similar(source, p)
            # boost FBT
            if pid in _FBT.get(seed, []):
                s += 0.3
            if s > scores.get(pid, 0):
                scores[pid] = s
                reasons[pid] = f"Because you liked {source['name']}"

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    recs = []
    for pid, score in ranked:
        p = _CATALOGUE[pid]
        recs.append({
            "product_id": pid,
            "name": p["name"],
            "price": p["price"],
            "category": p["category"],
            "score": round(score, 3),
            "reason": reasons[pid],
            "type": "personalized",
        })
    return {"recommendations": recs, "customer_id": customer_id, "based_on": seed_ids[:5]}


def recommend_for_cart(cart_product_ids: List[str], limit: int = 3) -> dict:
    """Suggest add-ons based on current cart contents."""
    scores: Dict[str, float] = {}
    reasons: Dict[str, str] = {}
    for pid in cart_product_ids:
        for fbt_id in _FBT.get(pid, []):
            if fbt_id in cart_product_ids:
                continue
            scores[fbt_id] = scores.get(fbt_id, 0) + 0.9
            p = _CATALOGUE.get(pid, {})
            reasons[fbt_id] = f"Pairs well with {p.get('name', pid)}"
        source = _CATALOGUE.get(pid)
        if source:
            for cid, c in _CATALOGUE.items():
                if cid in cart_product_ids or cid == pid:
                    continue
                s = _score_similar(source, c) * 0.5
                if s > scores.get(cid, 0):
                    scores[cid] = s
                    reasons[cid] = f"Similar to {source['name']} in your cart"

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    recs = []
    for pid, score in ranked:
        p = _CATALOGUE.get(pid)
        if not p:
            continue
        recs.append({
            "product_id": pid,
            "name": p["name"],
            "price": p["price"],
            "category": p["category"],
            "score": round(score, 3),
            "reason": reasons.get(pid, "Cart complement"),
            "type": "frequently_bought_together",
        })
    return {"recommendations": recs, "cart_product_ids": cart_product_ids}


recommendations_agent = Agent(
    name="recommendations_agent",
    model="gemini-2.5-flash",
    description="Product recommendations: similar, frequently bought together, trending, personalized, and cart add-ons.",
    instruction="""
You are the Personalization / Recommendations Agent.

Capabilities:
- recommend_similar(product_id)
- recommend_frequently_bought_together(product_id)
- recommend_trending(category?)
- recommend_personalized(customer_id) – uses view/purchase history
- recommend_for_cart(cart_product_ids) – upsell/cross-sell at cart
- record_view / record_purchase – feed personalization signals

When a user views a product, the orchestrator should record_view.
After order confirmation, record_purchase.
On product pages and cart, surface recommendations.

Never invent product IDs – only return IDs from the catalogue tools.
""",
    tools=[
        FunctionTool(recommend_similar),
        FunctionTool(recommend_frequently_bought_together),
        FunctionTool(recommend_trending),
        FunctionTool(recommend_personalized),
        FunctionTool(recommend_for_cart),
        FunctionTool(record_view),
        FunctionTool(record_purchase),
    ],
)

root_agent = recommendations_agent
