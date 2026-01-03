#!/bin/bash

# Script to set Stripe environment variables on Heroku
# Usage: ./setup_stripe_heroku.sh

APP_NAME="keuvi"

echo "=========================================="
echo "Stripe Heroku Configuration Setup"
echo "=========================================="
echo ""

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Error: Heroku CLI is not installed."
    echo "   Install it from: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if logged into Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ Error: Not logged into Heroku."
    echo "   Run: heroku login"
    exit 1
fi

echo "You'll need to provide your Stripe keys."
echo "Get them from: https://dashboard.stripe.com/apikeys"
echo ""

# Get Stripe Secret Key
read -p "Enter STRIPE_SECRET_KEY (sk_live_... or sk_test_...): " STRIPE_SECRET_KEY
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "❌ Error: STRIPE_SECRET_KEY is required"
    exit 1
fi

# Get Stripe Publishable Key
read -p "Enter STRIPE_PUBLISHABLE_KEY (pk_live_... or pk_test_...): " STRIPE_PUBLISHABLE_KEY
if [ -z "$STRIPE_PUBLISHABLE_KEY" ]; then
    echo "❌ Error: STRIPE_PUBLISHABLE_KEY is required"
    exit 1
fi

# Price ID (user already has this)
STRIPE_PRICE_ID="price_1SlI0HB8lvHlwl6XN873isr6"
echo ""
echo "Using Price ID: $STRIPE_PRICE_ID"
echo ""

# Get Webhook Secret (optional but recommended)
read -p "Enter STRIPE_WEBHOOK_SECRET (whsec_...) [optional, press Enter to skip]: " STRIPE_WEBHOOK_SECRET

echo ""
echo "Setting environment variables on Heroku ($APP_NAME)..."
echo ""

# Set the required variables
heroku config:set STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" --app $APP_NAME
if [ $? -eq 0 ]; then
    echo "✓ STRIPE_SECRET_KEY set"
else
    echo "❌ Failed to set STRIPE_SECRET_KEY"
    exit 1
fi

heroku config:set STRIPE_PUBLISHABLE_KEY="$STRIPE_PUBLISHABLE_KEY" --app $APP_NAME
if [ $? -eq 0 ]; then
    echo "✓ STRIPE_PUBLISHABLE_KEY set"
else
    echo "❌ Failed to set STRIPE_PUBLISHABLE_KEY"
    exit 1
fi

heroku config:set STRIPE_PRICE_ID="$STRIPE_PRICE_ID" --app $APP_NAME
if [ $? -eq 0 ]; then
    echo "✓ STRIPE_PRICE_ID set"
else
    echo "❌ Failed to set STRIPE_PRICE_ID"
    exit 1
fi

# Set webhook secret if provided
if [ -n "$STRIPE_WEBHOOK_SECRET" ]; then
    heroku config:set STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" --app $APP_NAME
    if [ $? -eq 0 ]; then
        echo "✓ STRIPE_WEBHOOK_SECRET set"
    else
        echo "❌ Failed to set STRIPE_WEBHOOK_SECRET"
        exit 1
    fi
else
    echo "⚠ STRIPE_WEBHOOK_SECRET skipped (you can set it later)"
fi

echo ""
echo "=========================================="
echo "✅ Configuration complete!"
echo "=========================================="
echo ""
echo "Verifying configuration..."
echo ""
heroku config --app $APP_NAME | grep STRIPE
echo ""
echo "Next steps:"
echo "1. Set up webhook in Stripe Dashboard:"
echo "   - Go to: https://dashboard.stripe.com/webhooks"
echo "   - Add endpoint: https://keuvi.app/api/v1/payments/webhook"
echo "   - Select events: checkout.session.completed, customer.subscription.*"
echo "   - Copy the webhook secret and run:"
echo "     heroku config:set STRIPE_WEBHOOK_SECRET='whsec_...' --app keuvi"
echo ""
echo "2. Restart your app:"
echo "   heroku restart --app keuvi"
echo ""


