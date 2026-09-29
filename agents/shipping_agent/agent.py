"""
Shipping & Dispatch Agent – rates, labels, tracking, warehouse dispatch.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

_SHIPMENTS: Dict[str, dict] = {}
_DISPATCHES: Dict[str, dict] = {}

# Simple rate table (production: EasyPost / Shippo / carrier APIs)
RATE_TABLE = {
    "standard": {"carrier": "USPS", "amount": 5.99, "days": 5},
    "express":  {"carrier": "UPS",  "amount": 14.99, "days": 2},
    "overnight":{"carrier": "FedEx","amount": 29.99, "days": 1},
    "pickup":   {"carrier": "Store","amount": 0.0,  "days": 0},
}


def get_shipping_rates(
    destination_country: str = "US",
    destination_postal_code: str = "",
    weight_kg: float = 1.0,
    subtotal: float = 0.0,
) -> dict:
    """Return available shipping methods and rates."""
    rates = []
    for method, info in RATE_TABLE.items():
        # Free standard shipping over $75
        amount = info["amount"]
        if method == "standard" and subtotal >= 75:
            amount = 0.0
        rates.append({
            "method": method,
            "carrier": info["carrier"],
            "amount": amount,
            "currency": "USD",
            "estimated_days": info["days"],
            "description": f"{info['carrier']} – {info['days']} business day(s)",
        })
    return {"rates": rates}


def create_shipment(
    order_id: str,
    address: dict,
    method: str = "standard",
    items: Optional[List[dict]] = None,
) -> dict:
    """Create a shipment record and generate a tracking number."""
    method = method.lower()
    if method not in RATE_TABLE:
        return {"error": f"Unknown shipping method: {method}"}

    rate_info = RATE_TABLE[method]
    sid = f"SHP-{uuid.uuid4().hex[:8].upper()}"
    tracking = f"{rate_info['carrier'][:3].upper()}{uuid.uuid4().hex[:10].upper()}"

    shipment = {
        "id": sid,
        "order_id": order_id,
        "method": method,
        "carrier": rate_info["carrier"],
        "tracking_number": tracking,
        "status": "label_created",
        "address": address,
        "rate": rate_info["amount"],
        "estimated_delivery": (datetime.utcnow() + timedelta(days=rate_info["days"])).isoformat(),
        "events": [
            {
                "status": "label_created",
                "timestamp": datetime.utcnow().isoformat(),
                "description": "Shipping label created",
            }
        ],
        "created_at": datetime.utcnow().isoformat(),
    }
    _SHIPMENTS[sid] = shipment
    return {"shipment": shipment, "message": f"Shipment created. Tracking: {tracking}"}


def create_dispatch(order_id: str, warehouse_id: str = "WH-01") -> dict:
    """Start warehouse dispatch (picking → packing → hand-off)."""
    did = f"DSP-{uuid.uuid4().hex[:8].upper()}"
    dispatch = {
        "id": did,
        "order_id": order_id,
        "warehouse_id": warehouse_id,
        "status": "picking",
        "packed_at": None,
        "dispatched_at": None,
        "carrier_handoff": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    _DISPATCHES[did] = dispatch
    return {"dispatch": dispatch, "message": "Dispatch started – picking in progress"}


def advance_dispatch(dispatch_id: str, next_status: str) -> dict:
    """Move dispatch through picking → packed → dispatched."""
    d = _DISPATCHES.get(dispatch_id)
    if not d:
        return {"error": f"Dispatch {dispatch_id} not found"}
    allowed = {"picking": "packed", "packed": "dispatched"}
    if d["status"] not in allowed or allowed[d["status"]] != next_status:
        return {"error": f"Cannot move from {d['status']} to {next_status}"}
    d["status"] = next_status
    now = datetime.utcnow().isoformat()
    if next_status == "packed":
        d["packed_at"] = now
    elif next_status == "dispatched":
        d["dispatched_at"] = now
        d["carrier_handoff"] = now
    return {"dispatch": d}


def update_shipment_status(
    shipment_id: str,
    status: str,
    description: Optional[str] = None,
) -> dict:
    """Update tracking status of a shipment."""
    s = _SHIPMENTS.get(shipment_id)
    if not s:
        return {"error": f"Shipment {shipment_id} not found"}
    s["status"] = status
    s["events"].append({
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "description": description or status.replace("_", " ").title(),
    })
    return {"shipment": s}


def get_shipment(shipment_id: Optional[str] = None, tracking_number: Optional[str] = None) -> dict:
    if shipment_id:
        s = _SHIPMENTS.get(shipment_id)
        if not s:
            return {"error": f"Shipment {shipment_id} not found"}
        return {"shipment": s}
    if tracking_number:
        for s in _SHIPMENTS.values():
            if s.get("tracking_number") == tracking_number:
                return {"shipment": s}
        return {"error": f"No shipment with tracking {tracking_number}"}
    return {"error": "Provide shipment_id or tracking_number"}


def get_dispatch(dispatch_id: str) -> dict:
    d = _DISPATCHES.get(dispatch_id)
    if not d:
        return {"error": f"Dispatch {dispatch_id} not found"}
    return {"dispatch": d}


shipping_agent = Agent(
    name="shipping_agent",
    model="gemini-2.5-flash",
    description="Handles shipping rates, label creation, tracking, and warehouse dispatch.",
    instruction="""
You are the Shipping & Dispatch Agent.

Capabilities:
- Quote shipping rates (standard / express / overnight / pickup)
- Create shipment + tracking number
- Create and advance warehouse dispatch (picking → packed → dispatched)
- Update and query shipment status / tracking

Free standard shipping applies when order subtotal ≥ $75.
Always return structured shipment and dispatch objects.
""",
    tools=[
        FunctionTool(get_shipping_rates),
        FunctionTool(create_shipment),
        FunctionTool(create_dispatch),
        FunctionTool(advance_dispatch),
        FunctionTool(update_shipment_status),
        FunctionTool(get_shipment),
        FunctionTool(get_dispatch),
    ],
)

root_agent = shipping_agent
