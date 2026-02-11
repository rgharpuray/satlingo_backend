# Stripe Discount Codes Research

## Executive Summary

This document provides research findings for implementing discount code functionality in the Keuvi web checkout flow. The recommended approach uses Stripe's **Promotion Codes** (customer-facing codes) built on top of **Coupons** (the underlying discount definition).

**Key Recommendation**: Enable `allow_promotion_codes=True` on the Checkout Session. This is the simplest approach that:
- Lets Stripe handle promo code UI and validation
- Requires minimal backend changes (one parameter addition)
- Allows admin to manage codes via Stripe Dashboard or Django admin
- Supports percentage and fixed-amount discounts

**Alternative**: For more control (custom validation, usage tracking in our database), we can use the `discounts` parameter to apply specific promotion codes server-side before creating the checkout session.

---

## Technology Overview

### Stripe Coupons
A **Coupon** defines the discount itself:
- Percentage off (e.g., 20% off)
- Fixed amount off (e.g., $5 off)
- Duration: once, forever, or repeating (X months)
- Optional redemption limits and expiration dates

Coupons are internal objects - customers never see or enter coupon IDs directly.

### Stripe Promotion Codes
A **Promotion Code** is a customer-facing code (e.g., "SUMMER20") that maps to a coupon:
- Human-readable code string
- Links to exactly one coupon
- Can have its own restrictions (customer-specific, first-time only, minimum order)
- Can be active/inactive independently of the coupon
- Tracks redemption count

**Relationship**: Promotion Code -> Coupon -> Applied to Subscription

---

## API References

### Creating a Coupon

```python
import stripe

# Percentage discount (20% off)
coupon = stripe.Coupon.create(
    percent_off=20,
    duration="forever",  # applies to all recurring payments
    id="KEUVI_20_PERCENT",  # optional custom ID
    name="20% Off Premium",  # display name
    # Optional restrictions:
    max_redemptions=100,  # limit total uses
    redeem_by=1735689600,  # Unix timestamp for expiration
)
```

### Creating a Promotion Code

```python
promo_code = stripe.PromotionCode.create(
    coupon="KEUVI_20_PERCENT",  # coupon ID
    code="SUMMER2024",  # customer-facing code
    active=True,
    max_redemptions=50,
    expires_at=1735689600,  # Unix timestamp
    restrictions={
        "first_time_transaction": True,  # only new customers
    },
)
```

### Applying Discounts to Checkout Sessions

**Option 1: Allow User-Entered Promotion Codes (Recommended)**

```python
checkout_session = stripe.checkout.Session.create(
    customer=customer.id,
    payment_method_types=['card'],
    line_items=[{
        'price': settings.STRIPE_PRICE_ID,
        'quantity': 1,
    }],
    mode='subscription',
    success_url=success_url,
    cancel_url=cancel_url,
    allow_promotion_codes=True,  # <-- Add this single parameter
    metadata={
        'user_id': str(user.id),
    },
)
```

This adds a "Add promotion code" link to the Stripe Checkout page. Stripe handles all validation and UI.

**Option 2: Apply Specific Promotion Code Server-Side**

```python
promo_codes = stripe.PromotionCode.list(code="SUMMER2024", active=True)
if promo_codes.data:
    promo_code_id = promo_codes.data[0].id

    checkout_session = stripe.checkout.Session.create(
        customer=customer.id,
        line_items=[{'price': settings.STRIPE_PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        discounts=[{
            'promotion_code': promo_code_id,
        }],
    )
```

### Invalidating Codes

```python
# Deactivate a promotion code
stripe.PromotionCode.modify(
    "promo_xxxxx",
    active=False,
)

# Delete a coupon (also invalidates all its promotion codes)
stripe.Coupon.delete("KEUVI_20_PERCENT")
```

---

## Recommendations

### For MVP (Minimal Implementation)

1. **Add `allow_promotion_codes=True`** to `create_checkout_session()` in `api/stripe_views.py`
2. **Create coupons/promotion codes in Stripe Dashboard** (no code needed)
3. **No database model needed** - Stripe tracks everything

**Effort**: ~5 minutes of code changes + admin setup time

### For Enhanced Control (Django Admin Integration)

Add a Django model to track codes locally for:
- Admin interface without Stripe Dashboard access
- Custom reporting
- Syncing with Stripe

### Web-Only Restriction

The discount codes are inherently web-only because:
- iOS uses App Store subscriptions (Apple does not allow external payment methods)
- Android uses Google Play subscriptions (same restriction)
- Only the web checkout (`/web/`) uses Stripe Checkout Sessions

**No additional code needed** to enforce web-only - it's architectural.

### Default 20% Discount

Create a standard coupon in Stripe Dashboard:
- **Name**: "20% Off Premium"
- **Percent off**: 20%
- **Duration**: Forever (applies to all recurring payments)
- **Create promotion codes** as needed (e.g., "STUDENT20", "WELCOME20")

---

## Stripe Changes Required

**Backend code change**: Add `allow_promotion_codes=True` to checkout session

**Stripe Dashboard setup**:
1. Create coupon(s) with desired discount percentages
2. Create promotion codes that map to those coupons
3. Set expiration dates/usage limits as needed

**No new webhooks needed** - existing subscription webhooks already handle discounted subscriptions.

---

## Implementation Checklist

- [ ] Add `allow_promotion_codes=True` to checkout session creation
- [ ] (Optional) Create Django model for admin management
- [ ] (Optional) Add admin interface for code CRUD
- [ ] Create 20% off coupon in Stripe Dashboard
- [ ] Create initial promotion code(s) in Stripe Dashboard
- [ ] Test in Stripe test mode
- [ ] Document admin process for creating/invalidating codes

---

*Research completed: 2024-02-09*
*Author: PACT Preparer Agent*
