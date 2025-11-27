# Authentication & Premium Features Guide

## Overview

The backend now supports:
- JWT-based authentication
- User registration and login
- Premium subscription management via Stripe
- Premium content filtering (premium passages only accessible to premium users)

## Authentication Endpoints

### Register
```
POST /api/v1/auth/register
Body: {
  "email": "user@example.com",
  "password": "securepassword"
}
Response: {
  "user": {...},
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

### Login
```
POST /api/v1/auth/login
Body: {
  "email": "user@example.com",
  "password": "securepassword"
}
Response: {
  "user": {...},
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

### Get Current User
```
GET /api/v1/auth/me
Headers: Authorization: Bearer <access_token>
Response: {
  "id": "...",
  "email": "...",
  "is_premium": false,
  "has_active_subscription": false
}
```

### Refresh Token
```
POST /api/v1/auth/refresh
Body: {
  "refresh": "<refresh_token>"
}
Response: {
  "access": "<new_access_token>"
}
```

## Payment Endpoints

### Create Checkout Session
```
POST /api/v1/payments/checkout
Headers: Authorization: Bearer <access_token>
Response: {
  "session_id": "...",
  "url": "https://checkout.stripe.com/..."
}
```

### Get Subscription Status
```
GET /api/v1/payments/subscription
Headers: Authorization: Bearer <access_token>
Response: {
  "has_subscription": true,
  "status": "active",
  "current_period_end": "...",
  "cancel_at_period_end": false
}
```

### Create Portal Session (Manage Subscription)
```
POST /api/v1/payments/portal
Headers: Authorization: Bearer <access_token>
Response: {
  "url": "https://billing.stripe.com/..."
}
```

## Premium Content Access

### How It Works

1. **Free Users**: Can only access passages with `tier: "free"`
2. **Premium Users**: Can access both `free` and `premium` passages
3. **API Filtering**: The `/api/v1/passages` endpoint automatically filters out premium content for non-premium users
4. **Direct Access**: Attempting to access a premium passage directly returns a `403 PREMIUM_REQUIRED` error

### Premium Check

The API checks premium status in two ways:
- `user.is_premium` - Boolean flag
- `user.has_active_subscription` - Checks for active Stripe subscription

## iOS Client Integration

### 1. Store Tokens

```swift
// After login/register
let accessToken = response.tokens.access
let refreshToken = response.tokens.refresh

// Store securely (Keychain)
KeychainHelper.save(accessToken, forKey: "access_token")
KeychainHelper.save(refreshToken, forKey: "refresh_token")
```

### 2. Include Token in Requests

```swift
var request = URLRequest(url: url)
request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
```

### 3. Handle Token Refresh

```swift
// If you get 401, refresh the token
func refreshAccessToken() {
    let refreshToken = KeychainHelper.load(forKey: "refresh_token")
    // POST to /api/v1/auth/refresh
    // Update stored access token
}
```

### 4. Check Premium Status

```swift
// After login, check user.is_premium
if user.is_premium {
    // Show premium content
} else {
    // Show upgrade prompt
}
```

## Web Frontend

The web frontend is available at:
- Main app: `http://localhost:8000/web/`
- Login/Register: Modal dialogs
- Premium upgrade: Click "Upgrade to Premium" button
- Stripe checkout: Redirects to Stripe hosted checkout

## Environment Variables

Set these in your environment or `.env` file:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

See `STRIPE_SETUP.md` for detailed Stripe setup instructions.


