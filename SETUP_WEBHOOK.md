# Stripe Webhook Setup

After creating the webhook endpoint in Stripe, run this command with your webhook secret:

```bash
heroku config:set STRIPE_WEBHOOK_SECRET='whsec_YOUR_WEBHOOK_SECRET_HERE'
```

Replace `whsec_YOUR_WEBHOOK_SECRET_HERE` with the actual secret you copied from Stripe.

## Quick Checklist

- [x] Stripe keys configured
- [x] Price created ($5/month)
- [ ] Webhook endpoint created in Stripe
- [ ] Webhook secret set on Heroku
- [ ] Test subscription flow

## Testing

Once everything is set up, you can test the subscription flow:
1. Log in to your app
2. Click "Upgrade to Premium"
3. Use test card: `4242 4242 4242 4242`
4. Complete checkout
5. Verify subscription status updates




