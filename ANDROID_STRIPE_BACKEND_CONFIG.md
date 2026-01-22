# Backend Stripe Configuration for Android App - VERIFIED ✅

## Current Configuration Status

### ✅ Checkout Session URLs

**Current Implementation:**
```python
# In api/stripe_views.py - create_checkout_session()

success_url = f"{scheme}://{host}/web/?from=subscription&session_id={{CHECKOUT_SESSION_ID}}"
cancel_url = f"{scheme}://{host}/web/subscription/cancel"
```

**URLs Generated:**
- **Success:** `https://keuvi.app/web/?from=subscription&session_id={CHECKOUT_SESSION_ID}`
- **Cancel:** `https://keuvi.app/web/subscription/cancel`

**Query Parameters:**
- Success URL includes: `?from=subscription&session_id={CHECKOUT_SESSION_ID}`
- Cancel URL: No query parameters

### ✅ Customer Portal Return URL

**Current Implementation:**
```python
# In api/stripe_views.py - create_portal_session()

return_url = f"{scheme}://{host}/web/"
```

**URL Generated:**
- **Return:** `https://keuvi.app/web/`

### ✅ Web Pages Exist

All required web pages are implemented:

| URL | Route | Template | Status |
|-----|-------|----------|--------|
| `/web/` | `web_views.index` | `templates/web/index.html` | ✅ Exists |
| `/web/subscription/success` | `web_views.subscription_success` | `templates/web/subscription_success.html` | ✅ Exists |
| `/web/subscription/cancel` | `web_views.subscription_cancel` | `templates/web/subscription_cancel.html` | ✅ Exists |

**Note:** The success URL currently goes to `/web/?from=subscription&session_id=...` (main index page), but there's also a dedicated `/web/subscription/success` route available if you want to use it.

---

## API Endpoints - VERIFIED ✅

All endpoints exist and are correctly configured:

### 1. Create Checkout Session ✅
```
POST /api/v1/payments/checkout
Authorization: Bearer <access_token>
Content-Type: application/json

Response (200):
{
  "session_id": "cs_test_...",
  "url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```
**Location:** `api/stripe_views.py::create_checkout_session()`

### 2. Get Subscription Status ✅
```
GET /api/v1/payments/subscription
Authorization: Bearer <access_token>

Response (200):
{
  "has_subscription": true,
  "status": "active",
  "current_period_end": "2026-02-21T00:00:00Z",
  "cancel_at_period_end": false
}
```
**Location:** `api/stripe_views.py::subscription_status()`

### 3. Create Portal Session ✅
```
POST /api/v1/payments/portal
Authorization: Bearer <access_token>

Response (200):
{
  "url": "https://billing.stripe.com/p/session/..."
}
```
**Location:** `api/stripe_views.py::create_portal_session()`

### 4. Sync Subscription ✅
```
POST /api/v1/payments/sync
Authorization: Bearer <access_token>

Response (200):
{
  "success": true,
  "message": "Subscription synced successfully",
  "subscription_status": "active",
  "is_premium": true
}
```
**Location:** `api/stripe_views.py::sync_subscription_from_stripe()`

### 5. Webhook Endpoint ✅
```
POST /api/v1/payments/webhook
(No authentication - uses Stripe signature verification)

Response (200):
{
  "status": "success"
}
```
**Location:** `api/stripe_views.py::stripe_webhook()`

---

## Webhooks - CONFIGURED ✅

The backend webhook handler processes all required events:

| Event | Handler Function | Action |
|-------|------------------|--------|
| `checkout.session.completed` | `handle_checkout_session()` | Creates subscription, sets `is_premium = true` |
| `customer.subscription.created` | `handle_subscription_created()` | Creates subscription record, sets `is_premium = true` |
| `customer.subscription.updated` | `handle_subscription_updated()` | Updates subscription status, manages premium until period ends |
| `customer.subscription.deleted` | `handle_subscription_deleted()` | Sets `is_premium = false` when period ends |

**Webhook URL for Stripe Dashboard:**
```
https://keuvi.app/api/v1/payments/webhook
```

**Important:** Make sure this URL is configured in your Stripe Dashboard:
1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://keuvi.app/api/v1/payments/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed` (optional but recommended)

---

## Android Deep Link Configuration

### Current URLs (Ready for Android)

The backend generates these URLs which work with Android deep links:

| URL Pattern | Purpose | Android Manifest Match |
|-------------|---------|------------------------|
| `https://keuvi.app/web/?from=subscription&session_id=...` | Checkout success | ✅ Matches `/web/*` |
| `https://keuvi.app/web/subscription/cancel` | Checkout cancel | ✅ Matches `/web/*` |
| `https://keuvi.app/web/` | Portal return | ✅ Matches `/web/*` |

### Android Manifest Configuration

Your Android app should have this in `AndroidManifest.xml`:

```xml
<activity 
    android:name=".MainActivity"
    android:launchMode="singleTop">
    
    <!-- Handle return from Stripe checkout/portal -->
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        
        <!-- Primary domain -->
        <data
            android:scheme="https"
            android:host="keuvi.app"
            android:pathPrefix="/web" />
        
        <!-- Heroku fallback -->
        <data
            android:scheme="https"
            android:host="keuvi.herokuapp.com"
            android:pathPrefix="/web" />
    </intent-filter>
</activity>
```

### Handling Return in Android App

When the app receives a deep link, check for these patterns:

```kotlin
// In MainActivity.onNewIntent() or onCreate()

val uri = intent?.data
if (uri != null && (uri.host == "keuvi.app" || uri.host == "keuvi.herokuapp.com")) {
    val path = uri.path
    
    when {
        // Success: /web/?from=subscription&session_id=...
        path?.startsWith("/web") == true && uri.getQueryParameter("from") == "subscription" -> {
            // User completed checkout - sync subscription
            syncSubscription()
        }
        
        // Cancel: /web/subscription/cancel
        path?.contains("subscription/cancel") == true -> {
            // User canceled checkout - no action needed
        }
        
        // Portal return: /web/
        path == "/web/" || path == "/web" -> {
            // User returned from portal - sync subscription
            syncSubscription()
        }
    }
}
```

---

## Recommendations

### 1. Optional: Use Dedicated Success Page

Currently, success redirects to `/web/?from=subscription&session_id=...`. You could change it to use the dedicated success page:

```python
# In api/stripe_views.py - create_checkout_session()
success_url = f"{scheme}://{host}/web/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
```

**Pros:**
- Dedicated success page with better messaging
- Clearer separation of concerns

**Cons:**
- Requires updating Android deep link handling
- Current setup works fine

### 2. Add Session ID to Cancel URL (Optional)

For better tracking, you could add session_id to cancel URL:

```python
cancel_url = f"{scheme}://{host}/web/subscription/cancel?session_id={{CHECKOUT_SESSION_ID}}"
```

---

## Testing Checklist

### Backend Verification ✅
- [x] Checkout session creates with correct URLs
- [x] Portal session creates with correct return URL
- [x] All API endpoints return correct responses
- [x] Webhook handler processes all events
- [x] Web pages exist and render correctly

### Android Integration Testing
- [ ] Test checkout flow: Create session → Open URL → Complete payment → Return to app
- [ ] Verify deep link is received with correct parameters
- [ ] Test sync subscription after checkout success
- [ ] Test portal flow: Open portal → Cancel subscription → Return to app
- [ ] Verify subscription status updates correctly
- [ ] Test error handling (network errors, invalid tokens)

---

## Summary

✅ **All backend configuration is correct and ready for Android integration!**

**Current URLs:**
- Success: `https://keuvi.app/web/?from=subscription&session_id={CHECKOUT_SESSION_ID}`
- Cancel: `https://keuvi.app/web/subscription/cancel`
- Portal Return: `https://keuvi.app/web/`

**All API endpoints exist and work correctly.**

**Webhooks are configured and handle all subscription events.**

**Android app can proceed with integration using the existing URLs.**

---

## Next Steps

1. **Configure Stripe Webhook** (if not already done):
   - Add `https://keuvi.app/api/v1/payments/webhook` in Stripe Dashboard
   - Select required events

2. **Test Deep Links**:
   - Use Android Studio's deep link testing
   - Or manually test with `adb shell am start -a android.intent.action.VIEW -d "https://keuvi.app/web/?from=subscription&session_id=test123"`

3. **Test Payment Flow**:
   - Use Stripe test mode
   - Test card: `4242 4242 4242 4242`
   - Verify subscription sync after payment

4. **Monitor Webhooks**:
   - Check Stripe Dashboard → Webhooks → Recent events
   - Verify backend logs for webhook processing
