"""
Shared Pydantic domain models for Agent Commerce.
Full e-commerce entities: Product, Catalogue, Cart, Customer, Address,
Order, Payment, Shipping, Dispatch.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4


# ─── Catalogue / Product ─────────────────────────────────────────────────────

class ProductStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"
    OUT_OF_STOCK = "out_of_stock"


class Product(BaseModel):
    id: str = Field(default_factory=lambda: f"PRD-{uuid4().hex[:8].upper()}")
    sku: str
    name: str
    description: str = ""
    price: float
    currency: str = "USD"
    compare_at_price: Optional[float] = None
    stock: int = 0
    reserved_stock: int = 0          # held by open carts / pending orders
    category: str = "general"
    subcategory: Optional[str] = None
    images: List[str] = []
    attributes: Dict[str, Any] = {}  # color, size, brand, etc.
    tags: List[str] = []
    status: ProductStatus = ProductStatus.ACTIVE
    merchant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def available_stock(self) -> int:
        return max(0, self.stock - self.reserved_stock)


class CatalogueFilter(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    tags: List[str] = []
    search: Optional[str] = None
    in_stock_only: bool = True
    limit: int = 20
    offset: int = 0


# ─── Customer & Address ──────────────────────────────────────────────────────

class Address(BaseModel):
    id: str = Field(default_factory=lambda: f"ADDR-{uuid4().hex[:6].upper()}")
    label: str = "Home"              # Home, Work, Other
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    phone: Optional[str] = None
    is_default: bool = False


class Customer(BaseModel):
    id: str = Field(default_factory=lambda: f"CUS-{uuid4().hex[:8].upper()}")
    email: str
    full_name: str
    phone: Optional[str] = None
    addresses: List[Address] = []
    default_address_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


# ─── Cart ───────────────────────────────────────────────────────────────────

class CartItem(BaseModel):
    product_id: str
    sku: str
    name: str
    unit_price: float
    quantity: int
    image: Optional[str] = None
    attributes: Dict[str, Any] = {}  # selected size/color

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.quantity, 2)


class Cart(BaseModel):
    id: str = Field(default_factory=lambda: f"CART-{uuid4().hex[:8].upper()}")
    customer_id: Optional[str] = None   # None = guest
    session_id: str
    items: List[CartItem] = []
    currency: str = "USD"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def subtotal(self) -> float:
        return round(sum(i.line_total for i in self.items), 2)

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)


# ─── Payment ────────────────────────────────────────────────────────────────

class PaymentMethod(str, Enum):
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    COD = "cod"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(BaseModel):
    id: str = Field(default_factory=lambda: f"PAY-{uuid4().hex[:8].upper()}")
    order_id: str
    amount: float
    currency: str = "USD"
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    gateway_ref: Optional[str] = None   # Stripe / Razorpay id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


# ─── Shipping & Dispatch ─────────────────────────────────────────────────────

class ShippingMethod(str, Enum):
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    PICKUP = "pickup"


class ShippingStatus(str, Enum):
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


class ShippingRate(BaseModel):
    method: ShippingMethod
    carrier: str
    amount: float
    currency: str = "USD"
    estimated_days: int
    description: str = ""


class Shipping(BaseModel):
    id: str = Field(default_factory=lambda: f"SHP-{uuid4().hex[:8].upper()}")
    order_id: str
    method: ShippingMethod
    carrier: str
    tracking_number: Optional[str] = None
    status: ShippingStatus = ShippingStatus.PENDING
    address: Address
    rate: float = 0.0
    estimated_delivery: Optional[datetime] = None
    events: List[Dict[str, Any]] = []   # status history
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Dispatch(BaseModel):
    """Warehouse / fulfillment center action."""
    id: str = Field(default_factory=lambda: f"DSP-{uuid4().hex[:8].upper()}")
    order_id: str
    warehouse_id: str = "WH-01"
    status: Literal["pending", "picking", "packed", "dispatched"] = "pending"
    packed_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    carrier_handoff: Optional[str] = None


# ─── Order ───────────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"       # warehouse picking
    DISPATCHED = "dispatched"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderItem(BaseModel):
    product_id: str
    sku: str
    name: str
    unit_price: float
    quantity: int
    line_total: float


class Order(BaseModel):
    id: str = Field(default_factory=lambda: f"ORD-{uuid4().hex[:8].upper()}")
    customer_id: str
    cart_id: Optional[str] = None
    items: List[OrderItem]
    subtotal: float
    shipping_cost: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float
    currency: str = "USD"
    status: OrderStatus = OrderStatus.PENDING_PAYMENT
    shipping_address: Address
    billing_address: Optional[Address] = None
    payment_id: Optional[str] = None
    shipping_id: Optional[str] = None
    dispatch_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Inventory Upload ───────────────────────────────────────────────────────

class InventoryUploadRequest(BaseModel):
    format: Literal["csv", "json"]
    content: str
    merchant_id: str
    source: str = "upload"


class InventoryUploadResult(BaseModel):
    success: bool
    products_added: int
    products_updated: int
    errors: List[str] = []


# ─── Partner ───────────────────────────────────────────────────────────────

class PartnerCommission(BaseModel):
    partner_id: str
    order_id: str
    amount: float
    rate: float


# ─── Offers / Promotions ───────────────────────────────────────────────────

class OfferType(str, Enum):
    PERCENTAGE = "percentage"           # e.g. 20% off
    FIXED_AMOUNT = "fixed_amount"       # e.g. $10 off
    FREE_SHIPPING = "free_shipping"
    BOGO = "bogo"                       # buy X get Y
    BUNDLE = "bundle"                   # specific product set discount


class OfferStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


class Offer(BaseModel):
    id: str = Field(default_factory=lambda: f"OFF-{uuid4().hex[:8].upper()}")
    code: Optional[str] = None          # promo code (optional for auto-applied)
    name: str
    description: str = ""
    type: OfferType
    value: float                        # percent (0-100) or fixed amount
    min_subtotal: float = 0.0           # minimum cart subtotal to qualify
    max_discount: Optional[float] = None
    applicable_product_ids: List[str] = []   # empty = all products
    applicable_categories: List[str] = []
    excluded_product_ids: List[str] = []
    usage_limit: Optional[int] = None   # total redemptions allowed
    usage_count: int = 0
    per_customer_limit: int = 1
    partner_id: Optional[str] = None    # partner-exclusive offer
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    status: OfferStatus = OfferStatus.ACTIVE
    stackable: bool = False             # can combine with other offers
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppliedOffer(BaseModel):
    offer_id: str
    code: Optional[str] = None
    name: str
    type: OfferType
    discount_amount: float
    free_shipping: bool = False


class OfferEvaluationResult(BaseModel):
    applicable: List[AppliedOffer] = []
    total_discount: float = 0.0
    free_shipping: bool = False
    messages: List[str] = []


# ─── Returns & Refunds ──────────────────────────────────────────────────────

class ReturnReason(str, Enum):
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    SIZE_FIT = "size_fit"
    CHANGED_MIND = "changed_mind"
    DAMAGED_IN_SHIPPING = "damaged_in_shipping"
    OTHER = "other"


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    LABEL_SENT = "label_sent"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    REFUNDED = "refunded"
    CLOSED = "closed"


class ReturnItem(BaseModel):
    product_id: str
    sku: str
    name: str
    quantity: int
    unit_price: float
    reason: ReturnReason
    notes: Optional[str] = None


class ReturnRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"RET-{uuid4().hex[:8].upper()}")
    order_id: str
    customer_id: str
    items: List[ReturnItem]
    status: ReturnStatus = ReturnStatus.REQUESTED
    refund_amount: float = 0.0
    restocking_fee: float = 0.0
    return_shipping_label: Optional[str] = None
    refund_payment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


# ─── Loyalty / Rewards ───────────────────────────────────────────────────────

class LoyaltyTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class PointsTransactionType(str, Enum):
    EARN = "earn"
    REDEEM = "redeem"
    ADJUST = "adjust"
    EXPIRE = "expire"


class LoyaltyAccount(BaseModel):
    customer_id: str
    points_balance: int = 0
    lifetime_points: int = 0
    tier: LoyaltyTier = LoyaltyTier.BRONZE
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PointsTransaction(BaseModel):
    id: str = Field(default_factory=lambda: f"PTS-{uuid4().hex[:8].upper()}")
    customer_id: str
    type: PointsTransactionType
    points: int
    order_id: Optional[str] = None
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Recommendations ─────────────────────────────────────────────────────────

class RecommendationType(str, Enum):
    SIMILAR = "similar"
    FREQUENTLY_BOUGHT_TOGETHER = "frequently_bought_together"
    TRENDING = "trending"
    PERSONALIZED = "personalized"
    RECENTLY_VIEWED = "recently_viewed"


class Recommendation(BaseModel):
    product_id: str
    score: float
    reason: str
    type: RecommendationType
