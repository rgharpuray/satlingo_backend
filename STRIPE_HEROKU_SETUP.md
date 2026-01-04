# Stripe Setup on Heroku

## Quick Setup Steps

### 1. Get Your Stripe Keys

1. Go to https://dashboard.stripe.com
2. Make sure you're in **Live mode** (toggle in top right)
3. Go to **Developers → API keys**
4. Copy your **Secret key** (starts with `sk_live_`)
5. Copy your **Publishable key** (starts with `pk_live_`)

### 2. Create a Product and Price

1. Go to **Products** in Stripe Dashboard
2. Click **+ Add product**
3. Name: "SAT Prep Premium Subscription"
4. Pricing model: **Recurring**
5. Price: $5.00 USD
6. Billing period: Monthly
7. Click **Save product**
8. Copy the **Price ID** (starts with `price_`)

### 3. Set Environment Variables on Heroku

Run these commands (replace with your actual values):

```bash
heroku config:set STRIPE_SECRET_KEY='sk_live_YOUR_SECRET_KEY' --app keuvi
heroku config:set STRIPE_PUBLISHABLE_KEY='pk_live_YOUR_PUBLISHABLE_KEY' --app keuvi
heroku config:set STRIPE_PRICE_ID='price_YOUR_PRICE_ID' --app keuvi
```

### 4. Set Up Webhook (CRITICAL for subscriptions to work)

1. Go to **Developers → Webhooks** in Stripe Dashboard
2. Click **+ Add endpoint**
3. Endpoint URL: `https://keuvi.app/api/v1/payments/webhook`
4. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Click **Add endpoint**
6. Copy the **Signing secret** (starts with `whsec_`)
7. Set it on Heroku:

```bash
heroku config:set STRIPE_WEBHOOK_SECRET='whsec_YOUR_WEBHOOK_SECRET' --app keuvi
```

### 5. Verify Configuration

Check that all variables are set:

```bash
heroku config --app keuvi | grep STRIPE
```

You should see:
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`

### 6. Test the Integration

1. Restart your Heroku app: `heroku restart --app keuvi`
2. Try upgrading to premium from your site
3. Use a real credit card (Stripe will process it)
4. Check Stripe Dashboard → Payments to see the transaction

## Important Notes

- **Webhook is REQUIRED**: Without the webhook, payments will go through but subscriptions won't be activated in your database
- **Use Live Keys for Production**: Make sure you're using `sk_live_` and `pk_live_` keys, not test keys
- **Webhook URL must be HTTPS**: Your production domain must have SSL (Heroku provides this automatically)

## Troubleshooting

### Payments go through but subscription doesn't activate
- Check webhook is configured correctly
- Check webhook secret is set on Heroku
- Check Heroku logs: `heroku logs --tail --app keuvi | grep webhook`

### "Stripe not configured" error
- Verify all 4 environment variables are set on Heroku
- Restart the app after setting variables

### Test Mode vs Live Mode
- **Test mode**: Use `sk_test_` and `pk_test_` keys, test card `4242 4242 4242 4242`
- **Live mode**: Use `sk_live_` and `pk_live_` keys, real credit cards



