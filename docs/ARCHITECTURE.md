# Agent Commerce – Architecture (v4)

## Specialist Agents (13)

| # | Agent | Responsibility |
|---|-------|----------------|
| 1 | Inventory | Catalogue, stock reserve/commit, CSV upload |
| 2 | Cart | Add/update/remove items, view cart |
| 3 | Customer | Profile, address book |
| 4 | Offers | Promo codes, discounts, free shipping |
| 5 | Loyalty | Points earn/redeem, tiers |
| 6 | Recommendations | Similar, FBT, trending, personalized |
| 7 | Payment | Authorize, capture, refund |
| 8 | Shipping | Rates, labels, tracking, dispatch |
| 9 | Fulfillment | Order lifecycle |
| 10 | Returns | RMA, labels, refunds, restock hints |
| 11 | Sales Partner | Affiliates, commissions |
| 12 | Shopper | Conversational guide |
| 13 | Root Orchestrator | ADK 2.0 routing of all flows |

## Purchase path (with loyalty + recommendations)

```
Browse / search     → Inventory + Recommendations (similar/trending)
View product        → Recommendations.record_view
Add to cart         → Cart + Recommendations.recommend_for_cart
Promo / points      → Offers.evaluate + Loyalty.redeem_points
Customer + address  → Customer
Shipping rates      → Shipping (free_shipping from offers)
Create order        → Fulfillment (discount = offers + loyalty)
Pay                 → Payment → attach_payment
Ship + dispatch     → Shipping → attach_shipping
Commit stock        → Inventory
Redeem offers       → Offers.redeem_offer
Earn points         → Loyalty.earn_points
Record purchase     → Recommendations.record_purchase
```

## Returns path

```
request_return → approve (label) | reject
→ mark_received → Payment.refund + complete_refund
→ Inventory restock (if applicable)
```

## Demo data

**Promos:** WELCOME10, SAVE15, FREESHIP, FOOT20  
**Loyalty:** 1 pt / $1 · 100 pts = $1 · Bronze→Silver(500)→Gold(2000)→Platinum(5000)  
**Returns:** 30-day window · 10% restocking fee on change-of-mind
