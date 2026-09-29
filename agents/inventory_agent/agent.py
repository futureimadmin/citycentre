"""
Inventory / Catalogue Agent – product catalogue, stock, search, uploads.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io
import uuid

_CATALOGUE: Dict[str, dict] = {
    "PRD-DEMO01": {
        "id": "PRD-DEMO01",
        "sku": "SHOE-RUN-01",
        "name": "AeroRun Pro Shoes",
        "description": "Lightweight running shoes with responsive cushioning.",
        "price": 129.99,
        "currency": "USD",
        "stock": 50,
        "reserved_stock": 0,
        "category": "Footwear",
        "subcategory": "Running",
        "images": [],
        "attributes": {"brand": "Aero", "gender": "unisex"},
        "tags": ["running", "sport", "lightweight"],
        "status": "active",
        "merchant_id": "default",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    "PRD-DEMO02": {
        "id": "PRD-DEMO02",
        "sku": "HEAD-WL-02",
        "name": "SonicWave Headphones",
        "description": "Wireless over-ear headphones with 40h battery.",
        "price": 89.50,
        "currency": "USD",
        "stock": 120,
        "reserved_stock": 0,
        "category": "Electronics",
        "subcategory": "Audio",
        "images": [],
        "attributes": {"brand": "Sonic", "connectivity": "Bluetooth 5.3"},
        "tags": ["headphones", "wireless", "audio"],
        "status": "active",
        "merchant_id": "default",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    "PRD-DEMO03": {
        "id": "PRD-DEMO03",
        "sku": "BAG-DAY-03",
        "name": "TrailDay Backpack 25L",
        "description": "Durable daypack for hiking and commute.",
        "price": 64.00,
        "currency": "USD",
        "stock": 80,
        "reserved_stock": 0,
        "category": "Bags",
        "subcategory": "Backpacks",
        "images": [],
        "attributes": {"capacity_l": 25, "color": "olive"},
        "tags": ["backpack", "outdoor", "travel"],
        "status": "active",
        "merchant_id": "default",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
}


def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock_only: bool = True,
    limit: int = 20,
) -> dict:
    """Browse / search the product catalogue."""
    products = list(_CATALOGUE.values())
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    if search:
        q = search.lower()
        products = [
            p for p in products
            if q in p["name"].lower()
            or q in p.get("description", "").lower()
            or any(q in t.lower() for t in p.get("tags", []))
        ]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    if in_stock_only:
        products = [p for p in products if (p["stock"] - p.get("reserved_stock", 0)) > 0]

    return {
        "products": products[:limit],
        "count": len(products),
        "returned": min(limit, len(products)),
    }


def get_product(product_id: str) -> dict:
    """Get full product details by ID or SKU."""
    p = _CATALOGUE.get(product_id)
    if not p:
        for prod in _CATALOGUE.values():
            if prod.get("sku") == product_id:
                return prod
        return {"error": f"Product {product_id} not found"}
    return p


def check_stock(product_id: str, quantity: int = 1) -> dict:
    """Check whether enough available stock exists."""
    p = get_product(product_id)
    if "error" in p:
        return p
    available = p["stock"] - p.get("reserved_stock", 0)
    return {
        "product_id": p["id"],
        "requested": quantity,
        "available": available,
        "sufficient": available >= quantity,
    }


def reserve_stock(product_id: str, quantity: int) -> dict:
    """Reserve stock for a cart or pending order."""
    p = _CATALOGUE.get(product_id)
    if not p:
        return {"error": f"Product {product_id} not found"}
    available = p["stock"] - p.get("reserved_stock", 0)
    if available < quantity:
        return {"error": f"Insufficient stock. Available: {available}"}
    p["reserved_stock"] = p.get("reserved_stock", 0) + quantity
    p["updated_at"] = datetime.utcnow().isoformat()
    return {"product_id": product_id, "reserved": quantity, "available_after": available - quantity}


def release_stock(product_id: str, quantity: int) -> dict:
    """Release previously reserved stock."""
    p = _CATALOGUE.get(product_id)
    if not p:
        return {"error": f"Product {product_id} not found"}
    p["reserved_stock"] = max(0, p.get("reserved_stock", 0) - quantity)
    p["updated_at"] = datetime.utcnow().isoformat()
    return {"product_id": product_id, "released": quantity}


def commit_stock(product_id: str, quantity: int) -> dict:
    """Convert reserved stock into actual sale (decrement stock)."""
    p = _CATALOGUE.get(product_id)
    if not p:
        return {"error": f"Product {product_id} not found"}
    p["reserved_stock"] = max(0, p.get("reserved_stock", 0) - quantity)
    p["stock"] = max(0, p["stock"] - quantity)
    p["updated_at"] = datetime.utcnow().isoformat()
    return {"product_id": product_id, "sold": quantity, "remaining_stock": p["stock"]}


def upload_inventory(format: str, content: str, merchant_id: str = "default") -> dict:
    """Upload products via CSV or JSON. Headers: sku,name,description,price,stock,category"""
    added = updated = 0
    errors = []
    try:
        if format == "json":
            data = json.loads(content)
            items = data if isinstance(data, list) else data.get("products", [])
        elif format == "csv":
            reader = csv.DictReader(io.StringIO(content))
            items = list(reader)
        else:
            return {"success": False, "errors": ["format must be csv or json"]}

        for item in items:
            try:
                sku = str(item.get("sku") or item.get("id") or "").strip()
                if not sku:
                    errors.append("Missing sku/id")
                    continue
                existing_id = None
                for pid, prod in _CATALOGUE.items():
                    if prod.get("sku") == sku:
                        existing_id = pid
                        break

                product = {
                    "sku": sku,
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "price": float(item["price"]),
                    "currency": item.get("currency", "USD"),
                    "stock": int(item.get("stock", 0)),
                    "reserved_stock": 0,
                    "category": item.get("category", "general"),
                    "subcategory": item.get("subcategory"),
                    "images": item.get("images", []) if isinstance(item.get("images"), list) else [],
                    "attributes": {},
                    "tags": item.get("tags", "").split(",") if isinstance(item.get("tags"), str) else item.get("tags", []),
                    "status": "active",
                    "merchant_id": merchant_id,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                if existing_id:
                    _CATALOGUE[existing_id].update(product)
                    updated += 1
                else:
                    pid = f"PRD-{uuid.uuid4().hex[:8].upper()}"
                    product["id"] = pid
                    product["created_at"] = datetime.utcnow().isoformat()
                    _CATALOGUE[pid] = product
                    added += 1
            except Exception as e:
                errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "products_added": added,
            "products_updated": updated,
            "errors": errors,
        }
    except Exception as e:
        return {"success": False, "errors": [str(e)]}


inventory_agent = Agent(
    name="inventory_agent",
    model="gemini-2.5-flash",
    description="Owns the product catalogue, search, stock levels, reservations, and inventory uploads.",
    instruction="""
You are the Inventory / Catalogue Agent.

You manage:
- Product catalogue (list, search, get details)
- Stock availability, reservation, release, and commit (sale)
- Bulk inventory upload (CSV / JSON)

When other agents need product data or stock checks they call you.
Always return structured product objects. Never invent products.
""",
    tools=[
        FunctionTool(list_products),
        FunctionTool(get_product),
        FunctionTool(check_stock),
        FunctionTool(reserve_stock),
        FunctionTool(release_stock),
        FunctionTool(commit_stock),
        FunctionTool(upload_inventory),
    ],
)

root_agent = inventory_agent
