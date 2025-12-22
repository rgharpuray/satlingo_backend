#!/usr/bin/env python
"""
Script to create a $5/month subscription price in Stripe.
Run this once to set up your subscription product.

Usage:
    python setup_stripe_price.py

Requires STRIPE_SECRET_KEY environment variable to be set.
"""

import os
import stripe

# Get Stripe secret key from environment
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
if not STRIPE_SECRET_KEY:
    print("Error: STRIPE_SECRET_KEY environment variable is not set.")
    print("Please set it before running this script:")
    print("  export STRIPE_SECRET_KEY='sk_test_...'")
    print("  python setup_stripe_price.py")
    exit(1)

stripe.api_key = STRIPE_SECRET_KEY

def create_subscription_product():
    """Create a $5/month subscription product and price"""
    print("Creating Stripe product and price...")
    print("-" * 60)
    
    try:
        # Create product
        product = stripe.Product.create(
            name='SAT Prep Premium Subscription',
            description='Monthly premium subscription for SAT Prep platform',
        )
        print(f"✓ Product created: {product.id}")
        print(f"  Name: {product.name}")
        
        # Create price: $5/month
        price = stripe.Price.create(
            product=product.id,
            unit_amount=500,  # $5.00 in cents
            currency='usd',
            recurring={
                'interval': 'month',
            },
        )
        print(f"✓ Price created: {price.id}")
        print(f"  Amount: ${price.unit_amount / 100:.2f} {price.currency.upper()}")
        print(f"  Interval: {price.recurring.interval}")
        print()
        print("=" * 60)
        print("✅ Setup complete!")
        print("=" * 60)
        print()
        print("Add these to your environment variables:")
        print(f"STRIPE_SECRET_KEY=<your_secret_key>")
        print(f"STRIPE_PUBLISHABLE_KEY=<your_publishable_key>")
        print(f"STRIPE_PRICE_ID={price.id}")
        print()
        print("For Heroku, run:")
        print(f"heroku config:set STRIPE_SECRET_KEY='<your_secret_key>' --app keuvi")
        print(f"heroku config:set STRIPE_PUBLISHABLE_KEY='<your_publishable_key>' --app keuvi")
        print(f"heroku config:set STRIPE_PRICE_ID='{price.id}' --app keuvi")
        print()
        
        return price.id
        
    except stripe.error.StripeError as e:
        print(f"✗ Stripe error: {str(e)}")
        return None
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None


if __name__ == '__main__':
    price_id = create_subscription_product()
    if price_id:
        print(f"\nPrice ID to use: {price_id}")
    else:
        print("\nFailed to create price. Please check your Stripe keys.")
