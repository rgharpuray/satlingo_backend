# Discount Codes Architecture

## Executive Summary

This document defines the architecture for implementing discount code management in Keuvi's web checkout flow. The design enables admin-managed discount codes that sync bidirectionally with Stripe, providing a simple Django admin interface while leveraging Stripe's robust discount infrastructure.

**Key Design Decisions**:
1. Django admin as primary interface for code management (no Stripe Dashboard required)
2. Bidirectional sync with Stripe Coupons and Promotion Codes APIs
3. Enable `allow_promotion_codes=True` on checkout sessions for user-entered codes
4. Track usage statistics locally for reporting

---

## System Context

```
+------------------+          +-------------------+          +------------------+
|                  |          |                   |          |                  |
|   Django Admin   | -------> |  DiscountCode     | -------> |  Stripe API      |
|   (Admin User)   |  Create/ |  Model            |  Sync    |  (Coupons/Promos)|
|                  |  Update  |                   |          |                  |
+------------------+          +-------------------+          +------------------+
                                       |
                                       | FK
                                       v
+------------------+          +-------------------+
|                  |          |                   |
|  Web Checkout    | -------> |  Checkout Session |
|  (End User)      |  Enter   |  (Stripe)         |
|                  |  Code    |                   |
+------------------+          +-------------------+
```

### External Dependencies
- **Stripe API**: Coupons and Promotion Codes endpoints
- **Django Admin**: Admin interface for CRUD operations
- **Existing Components**: `Subscription` model, `stripe_views.py` checkout flow

### Boundaries
- **In Scope**: Web checkout discount codes via Django admin
- **Out of Scope**: Mobile apps (use App Store/Play Store subscriptions)

---

## Component Architecture

### 1. Data Model: `DiscountCode`

A new Django model that represents a discount code and maintains sync with Stripe.

```python
class DiscountCode(models.Model):
    """
    Represents a discount/promotion code for web subscriptions.
    Syncs with Stripe Coupons and Promotion Codes.
    """

    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage Off'),
        ('amount', 'Fixed Amount Off'),
    ]

    DURATION_CHOICES = [
        ('once', 'Once (first payment only)'),
        ('forever', 'Forever (all recurring payments)'),
        ('repeating', 'Repeating (X months)'),
    ]

    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Customer-facing code (e.g., 'STUDENT20', 'WELCOME')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name for admin reference"
    )

    # Discount configuration
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent'
    )
    percent_off = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentage discount (1-100)"
    )
    amount_off = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        help_text="Fixed amount off in cents (USD)"
    )

    # Duration settings
    duration = models.CharField(
        max_length=10,
        choices=DURATION_CHOICES,
        default='forever'
    )
    duration_in_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of months (only for 'repeating' duration)"
    )

    # Restrictions
    max_redemptions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total uses (leave blank for unlimited)"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date (leave blank for no expiration)"
    )
    first_time_transaction = models.BooleanField(
        default=False,
        help_text="Only allow for first-time customers"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Stripe references (populated on sync)
    stripe_coupon_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    stripe_promotion_code_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # Usage tracking (updated via webhooks or periodic sync)
    times_redeemed = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discount_codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.code} ({self.percent_off}% off)"
        return f"{self.code} (${self.amount_off/100:.2f} off)"

    def clean(self):
        """Validate discount configuration"""
        from django.core.exceptions import ValidationError

        if self.discount_type == 'percent' and not self.percent_off:
            raise ValidationError('Percentage off is required for percent discount type')
        if self.discount_type == 'amount' and not self.amount_off:
            raise ValidationError('Amount off is required for fixed amount discount type')
        if self.duration == 'repeating' and not self.duration_in_months:
            raise ValidationError('Duration in months is required for repeating duration')

    def is_valid(self):
        """Check if code is currently valid for use"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_redemptions and self.times_redeemed >= self.max_redemptions:
            return False
        return True
```

### 2. Stripe Sync Service

A service module that handles bidirectional sync with Stripe.

**Location**: `api/discount_sync.py`

```python
# Pseudocode/Interface definition

class DiscountSyncService:
    """Handles sync between DiscountCode model and Stripe API"""

    @staticmethod
    def create_in_stripe(discount_code: DiscountCode) -> tuple[str, str]:
        """
        Create coupon and promotion code in Stripe.
        Returns: (stripe_coupon_id, stripe_promotion_code_id)

        Steps:
        1. Create Stripe Coupon with discount configuration
        2. Create Stripe Promotion Code linked to coupon
        3. Return both IDs for storage
        """
        pass

    @staticmethod
    def update_in_stripe(discount_code: DiscountCode) -> None:
        """
        Update Stripe promotion code (mainly active status).
        Note: Stripe coupons are mostly immutable after creation.

        Steps:
        1. Update promotion code active status
        2. If major changes needed, deactivate old and create new
        """
        pass

    @staticmethod
    def deactivate_in_stripe(discount_code: DiscountCode) -> None:
        """
        Deactivate promotion code in Stripe.

        Steps:
        1. Set promotion code active=False
        2. Optionally delete coupon if no other promo codes use it
        """
        pass

    @staticmethod
    def sync_usage_from_stripe(discount_code: DiscountCode) -> int:
        """
        Fetch current redemption count from Stripe.
        Returns: times_redeemed count
        """
        pass
```

### 3. Model Signal Handler

Automatically sync to Stripe when DiscountCode is saved.

**Location**: `api/models.py` (bottom of file with other signals)

```python
@receiver(post_save, sender=DiscountCode)
def sync_discount_code_to_stripe(sender, instance, created, **kwargs):
    """Sync discount code to Stripe on save"""
    from .discount_sync import DiscountSyncService

    if created:
        # New code - create in Stripe
        coupon_id, promo_id = DiscountSyncService.create_in_stripe(instance)
        # Update without triggering signal again
        DiscountCode.objects.filter(pk=instance.pk).update(
            stripe_coupon_id=coupon_id,
            stripe_promotion_code_id=promo_id
        )
    else:
        # Existing code - update active status in Stripe
        DiscountSyncService.update_in_stripe(instance)

@receiver(pre_delete, sender=DiscountCode)
def deactivate_discount_code_in_stripe(sender, instance, **kwargs):
    """Deactivate promotion code in Stripe before deletion"""
    from .discount_sync import DiscountSyncService
    DiscountSyncService.deactivate_in_stripe(instance)
```

---

## Admin Interface

### Admin Configuration

**Location**: `api/admin.py`

```python
@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'name',
        'discount_display',
        'duration',
        'is_active',
        'times_redeemed_display',
        'expires_at',
        'created_at'
    ]
    list_filter = ['is_active', 'discount_type', 'duration', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = [
        'id',
        'stripe_coupon_id',
        'stripe_promotion_code_id',
        'times_redeemed',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('Code Details', {
            'fields': ('code', 'name', 'is_active')
        }),
        ('Discount Configuration', {
            'fields': ('discount_type', 'percent_off', 'amount_off')
        }),
        ('Duration', {
            'fields': ('duration', 'duration_in_months')
        }),
        ('Restrictions', {
            'fields': ('max_redemptions', 'expires_at', 'first_time_transaction')
        }),
        ('Stripe Sync (Read-Only)', {
            'fields': ('stripe_coupon_id', 'stripe_promotion_code_id', 'times_redeemed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_codes', 'deactivate_codes', 'sync_usage_stats']

    def discount_display(self, obj):
        """Display discount amount/percentage"""
        if obj.discount_type == 'percent':
            return f"{obj.percent_off}% off"
        return f"${obj.amount_off/100:.2f} off"
    discount_display.short_description = 'Discount'

    def times_redeemed_display(self, obj):
        """Display redemption count with max if set"""
        if obj.max_redemptions:
            return f"{obj.times_redeemed} / {obj.max_redemptions}"
        return str(obj.times_redeemed)
    times_redeemed_display.short_description = 'Redemptions'

    @admin.action(description='Activate selected codes')
    def activate_codes(self, request, queryset):
        queryset.update(is_active=True)
        # Sync will happen via signal

    @admin.action(description='Deactivate selected codes')
    def deactivate_codes(self, request, queryset):
        queryset.update(is_active=False)
        # Sync will happen via signal

    @admin.action(description='Sync usage stats from Stripe')
    def sync_usage_stats(self, request, queryset):
        from .discount_sync import DiscountSyncService
        for code in queryset:
            if code.stripe_promotion_code_id:
                count = DiscountSyncService.sync_usage_from_stripe(code)
                code.times_redeemed = count
                code.save(update_fields=['times_redeemed'])
```

---

## Checkout Flow Changes

### Current Flow
```
User clicks "Subscribe" → create_checkout_session() → Stripe Checkout → Webhook → Subscription created
```

### Updated Flow
```
User clicks "Subscribe" → create_checkout_session() → Stripe Checkout (with promo code field) → Webhook → Subscription created
```

### Code Change Required

**File**: `api/stripe_views.py`
**Function**: `create_checkout_session`
**Change**: Add `allow_promotion_codes=True` parameter

```python
# Current (line 92-105):
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
    metadata={
        'user_id': str(user.id),
    },
)

# Updated:
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
    allow_promotion_codes=True,  # <-- ADD THIS LINE
    metadata={
        'user_id': str(user.id),
    },
)
```

This single line enables Stripe's built-in promotion code UI on the checkout page.

---

## Data Flow Diagrams

### Creating a Discount Code

```
Admin           Django Admin       DiscountCode        Signal Handler     Stripe API
  |                  |                  |                    |                |
  | Create code      |                  |                    |                |
  |----------------->|                  |                    |                |
  |                  | Save model       |                    |                |
  |                  |----------------->|                    |                |
  |                  |                  | post_save signal   |                |
  |                  |                  |------------------->|                |
  |                  |                  |                    | Create coupon  |
  |                  |                  |                    |--------------->|
  |                  |                  |                    |                |
  |                  |                  |                    | Create promo   |
  |                  |                  |                    |--------------->|
  |                  |                  |                    |                |
  |                  |                  |                    | Return IDs     |
  |                  |                  |                    |<---------------|
  |                  |                  | Update Stripe IDs  |                |
  |                  |                  |<-------------------|                |
  |                  | Success          |                    |                |
  |<-----------------|                  |                    |                |
```

### User Applying Discount at Checkout

```
User            Web Client        Django API         Stripe Checkout      Stripe API
  |                  |                  |                    |                |
  | Click Subscribe  |                  |                    |                |
  |----------------->|                  |                    |                |
  |                  | POST /checkout   |                    |                |
  |                  |----------------->|                    |                |
  |                  |                  | Create session     |                |
  |                  |                  | (allow_promo=True) |                |
  |                  |                  |------------------->|                |
  |                  |                  |                    |                |
  |                  | Redirect to      |                    |                |
  |                  | Stripe Checkout  |                    |                |
  |<-----------------|                  |                    |                |
  |                  |                  |                    |                |
  | Enter promo code |                  |                    |                |
  |----------------->|                  |                    |                |
  |                  |                  |                    | Validate code  |
  |                  |                  |                    |--------------->|
  |                  |                  |                    | Apply discount |
  |                  |                  |                    |<---------------|
  |                  |                  |                    |                |
  | Complete payment |                  |                    |                |
  |----------------->|                  |                    |                |
  |                  |                  | Webhook: session   |                |
  |                  |                  | completed          |                |
  |                  |                  |<-------------------|                |
```

---

## API Specifications

### No New API Endpoints Required

The discount code functionality is entirely managed through:
1. Django Admin (for code management)
2. Stripe Checkout (for code application by users)
3. Existing webhook handler (already processes subscriptions with discounts)

### Webhook Handling

The existing `stripe_webhook` function already handles `customer.subscription.created` and `customer.subscription.updated` events. Discounted subscriptions are processed identically to full-price subscriptions - Stripe applies the discount and reports the subscription status.

No webhook changes are required.

---

## Technology Decisions

| Decision | Rationale |
|----------|-----------|
| `allow_promotion_codes=True` over `discounts` param | Simpler implementation; Stripe handles UI and validation |
| Django signals for sync | Automatic, transparent sync without custom save logic |
| Local usage tracking | Enables admin reporting without Stripe Dashboard |
| UUID primary key | Consistent with existing models |
| Separate coupon/promo ID storage | Supports future flexibility (multiple codes per coupon) |

---

## Security Architecture

### Threats and Mitigations

| Threat | Mitigation |
|--------|------------|
| Unauthorized code creation | Django admin authentication required |
| Code enumeration/guessing | Stripe handles validation; no API exposure |
| Expired code abuse | Stripe validates expiration on checkout |
| Over-redemption | Stripe enforces max_redemptions |

### Admin Access

Only Django admin users with appropriate permissions can:
- Create discount codes
- Modify discount codes
- Deactivate discount codes
- View usage statistics

---

## Deployment Architecture

### Migration Strategy

1. Create and apply Django migration for `DiscountCode` model
2. Deploy code changes (`allow_promotion_codes=True` + admin)
3. Create initial discount codes via admin (sync to Stripe automatically)
4. Test in Stripe test mode

### Environment Variables

No new environment variables required. Existing Stripe configuration is sufficient:
- `STRIPE_SECRET_KEY` (already configured)
- `STRIPE_WEBHOOK_SECRET` (already configured)

---

## Implementation Guidelines

### File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `api/models.py` | Add | `DiscountCode` model + signal handlers |
| `api/discount_sync.py` | New | Stripe sync service |
| `api/admin.py` | Add | `DiscountCodeAdmin` registration |
| `api/stripe_views.py` | Modify | Add `allow_promotion_codes=True` |
| `api/migrations/XXXX_discount_code.py` | New | Database migration |

### Suggested Implementation Order

1. **Create model and migration** - `DiscountCode` in `models.py`
2. **Create sync service** - `discount_sync.py` with Stripe API calls
3. **Add signal handlers** - In `models.py` after model definition
4. **Add admin interface** - `DiscountCodeAdmin` in `admin.py`
5. **Update checkout** - Add `allow_promotion_codes=True`
6. **Test end-to-end** - Create code via admin, apply in checkout

### Code Style Notes

- Follow existing model patterns (UUID primary key, `created_at`/`updated_at`)
- Use existing Stripe error handling patterns from `stripe_views.py`
- Keep sync service stateless (class methods, no instance state)
- Log all Stripe API calls for debugging

---

## Implementation Roadmap

### Phase 1: Core Implementation (Day 1)
- [ ] Create `DiscountCode` model
- [ ] Create database migration
- [ ] Implement `DiscountSyncService`
- [ ] Add signal handlers
- [ ] Add admin interface
- [ ] Update checkout session creation

### Phase 2: Testing (Day 1-2)
- [ ] Unit tests for model validation
- [ ] Integration tests for Stripe sync
- [ ] Manual testing in Stripe test mode
- [ ] Admin workflow testing

### Phase 3: Deployment (Day 2)
- [ ] Deploy to staging
- [ ] Create test discount codes
- [ ] End-to-end checkout test
- [ ] Deploy to production

### Milestones

| Milestone | Deliverable | Acceptance Criteria |
|-----------|-------------|---------------------|
| M1: Model Complete | `DiscountCode` model + migration | Model validates, migration applies |
| M2: Stripe Sync | Sync service + signals | Codes created in admin appear in Stripe |
| M3: Checkout Ready | Updated checkout flow | Promo code field visible in Stripe Checkout |
| M4: Production | Live system | Admin can create codes, users can apply them |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Stripe API rate limiting | Low | Medium | Batch updates, async processing |
| Sync failure leaves orphaned codes | Low | Low | Error handling, admin can manually fix |
| Coupon immutability surprises | Medium | Low | Document that major changes require new code |
| Webhook timing issues | Low | Low | Existing webhook handling is robust |

---

## Testing Strategy

### Unit Tests
- Model validation (discount_type, percent_off, etc.)
- `is_valid()` method logic
- Clean method validation

### Integration Tests
- Stripe API mocking for sync service
- Signal handler triggering
- Admin action execution

### End-to-End Tests
- Create code in admin -> verify in Stripe
- Apply code in checkout -> verify discounted subscription
- Deactivate code -> verify rejection in checkout

---

## Appendix: Default 20% Discount Setup

To create the standard 20% discount code as mentioned in requirements:

1. Navigate to Django Admin -> Discount Codes
2. Click "Add Discount Code"
3. Fill in:
   - **Code**: `STUDENT20` (or preferred code)
   - **Name**: "Student 20% Discount"
   - **Discount Type**: Percentage Off
   - **Percent Off**: 20
   - **Duration**: Forever
   - **Active**: Checked
4. Save - code will sync to Stripe automatically

---

*Architecture document created: 2024-02-09*
*Author: PACT Architect Agent*
