"""
Customer Agent – profiles, addresses, identity.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

_CUSTOMERS: Dict[str, dict] = {}
_EMAIL_INDEX: Dict[str, str] = {}  # email -> customer_id


def create_customer(
    email: str,
    full_name: str,
    phone: Optional[str] = None,
) -> dict:
    """Register a new customer."""
    email = email.lower().strip()
    if email in _EMAIL_INDEX:
        return {"error": "Customer with this email already exists", "customer_id": _EMAIL_INDEX[email]}

    cid = f"CUS-{uuid.uuid4().hex[:8].upper()}"
    customer = {
        "id": cid,
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "addresses": [],
        "default_address_id": None,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {},
    }
    _CUSTOMERS[cid] = customer
    _EMAIL_INDEX[email] = cid
    return {"customer": customer, "message": f"Welcome {full_name}!"}


def get_customer(customer_id: Optional[str] = None, email: Optional[str] = None) -> dict:
    """Lookup customer by id or email."""
    if customer_id:
        c = _CUSTOMERS.get(customer_id)
        if not c:
            return {"error": f"Customer {customer_id} not found"}
        return {"customer": c}
    if email:
        cid = _EMAIL_INDEX.get(email.lower().strip())
        if not cid:
            return {"error": f"No customer for email {email}"}
        return {"customer": _CUSTOMERS[cid]}
    return {"error": "Provide customer_id or email"}


def add_address(
    customer_id: str,
    full_name: str,
    line1: str,
    city: str,
    state: str,
    postal_code: str,
    country: str = "US",
    line2: Optional[str] = None,
    phone: Optional[str] = None,
    label: str = "Home",
    is_default: bool = False,
) -> dict:
    """Add a shipping/billing address to the customer."""
    customer = _CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    addr_id = f"ADDR-{uuid.uuid4().hex[:6].upper()}"
    address = {
        "id": addr_id,
        "label": label,
        "full_name": full_name,
        "line1": line1,
        "line2": line2,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "phone": phone,
        "is_default": is_default,
    }
    customer["addresses"].append(address)
    if is_default or not customer["default_address_id"]:
        customer["default_address_id"] = addr_id
        for a in customer["addresses"]:
            a["is_default"] = a["id"] == addr_id
    return {"address": address, "customer": customer}


def list_addresses(customer_id: str) -> dict:
    customer = _CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}
    return {"addresses": customer["addresses"], "default_address_id": customer["default_address_id"]}


def set_default_address(customer_id: str, address_id: str) -> dict:
    customer = _CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}
    found = False
    for a in customer["addresses"]:
        a["is_default"] = a["id"] == address_id
        if a["id"] == address_id:
            found = True
    if not found:
        return {"error": f"Address {address_id} not found"}
    customer["default_address_id"] = address_id
    return {"customer": customer}


customer_agent = Agent(
    name="customer_agent",
    model="gemini-2.5-flash",
    description="Manages customer profiles and shipping/billing addresses.",
    instruction="""
You are the Customer Agent.
You own customer identity and address book.

Capabilities:
- Create / lookup customer by email or id
- Add, list, and set default shipping/billing addresses

When a user wants to checkout, ensure they have a customer record and at least one address.
Return structured customer and address objects so other agents (Cart, Payment, Shipping) can use them.
""",
    tools=[
        FunctionTool(create_customer),
        FunctionTool(get_customer),
        FunctionTool(add_address),
        FunctionTool(list_addresses),
        FunctionTool(set_default_address),
    ],
)

root_agent = customer_agent
