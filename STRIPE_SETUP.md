# Stripe Setup Guide

## 1. Create Stripe Account

1. Go to https://stripe.com and create an account
2. Get your API keys from the Dashboard → Developers → API keys

## 2. Create a Product and Price

1. Go to Products in Stripe Dashboard
2. Create a new product: "SAT Prep Premium Subscription"
3. Set price to $5.00/month (recurring)
4. Copy the Price ID (starts with `price_`)

## 3. Set Environment Variables

Create a `.env` file in the project root:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

Or set them in your environment:

```bash
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export STRIPE_PRICE_ID=price_...
```

## 4. Set Up Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/api/v1/payments/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the webhook signing secret

## 5. Test Mode

- Use test keys (start with `sk_test_` and `pk_test_`)
- Use test card: `4242 4242 4242 4242`
- Any future expiry date and CVC

## 6. Production

- Replace test keys with live keys (start with `sk_live_` and `pk_live_`)
- Update webhook URL to production domain
- Update webhook secret


