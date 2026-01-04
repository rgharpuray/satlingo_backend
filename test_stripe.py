#!/usr/bin/env python
"""
Test script to verify Stripe integration is configured correctly.
Run this after setting up your Stripe keys to verify everything works.

Usage:
    python test_stripe.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satlingo.settings')
django.setup()

from django.conf import settings
import stripe

def test_stripe_config():
    """Test Stripe configuration"""
    print("=" * 60)
    print("Testing Stripe Configuration")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking Environment Variables:")
    print("-" * 60)
    
    stripe_secret = getattr(settings, 'STRIPE_SECRET_KEY', '')
    stripe_publishable = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
    stripe_price_id = getattr(settings, 'STRIPE_PRICE_ID', '')
    stripe_webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    checks = [
        ('STRIPE_SECRET_KEY', stripe_secret, stripe_secret.startswith('sk_')),
        ('STRIPE_PUBLISHABLE_KEY', stripe_publishable, stripe_publishable.startswith('pk_')),
        ('STRIPE_PRICE_ID', stripe_price_id, stripe_price_id.startswith('price_')),
        ('STRIPE_WEBHOOK_SECRET', stripe_webhook_secret, stripe_webhook_secret.startswith('whsec_')),
    ]
    
    all_configured = True
    for name, value, is_valid in checks:
        status = "✓" if (value and is_valid) else "✗"
        display_value = value[:20] + "..." if value and len(value) > 20 else (value or "NOT SET")
        print(f"   {status} {name}: {display_value}")
        if not value or not is_valid:
            all_configured = False
    
    print()
    
    if not all_configured:
        print("⚠️  Some environment variables are missing or invalid!")
        print("   Please set all required Stripe environment variables.")
        return False
    
    # Test Stripe API connection
    print("2. Testing Stripe API Connection:")
    print("-" * 60)
    
    try:
        stripe.api_key = stripe_secret
        # Try to retrieve account info (this validates the API key)
        account = stripe.Account.retrieve()
        print(f"   ✓ Connected to Stripe account: {account.id}")
        print(f"   ✓ Account type: {'Test' if 'test' in stripe_secret else 'Live'}")
    except stripe.error.AuthenticationError:
        print("   ✗ Authentication failed - check your STRIPE_SECRET_KEY")
        return False
    except Exception as e:
        print(f"   ✗ Error connecting to Stripe: {str(e)}")
        return False
    
    print()
    
    # Test Price ID
    print("3. Testing Price ID:")
    print("-" * 60)
    
    try:
        price = stripe.Price.retrieve(stripe_price_id)
        print(f"   ✓ Price ID is valid: {price.id}")
        print(f"   ✓ Product: {price.product}")
        print(f"   ✓ Amount: ${price.unit_amount / 100:.2f} {price.currency.upper()}")
        print(f"   ✓ Billing: {price.recurring.interval if price.recurring else 'one-time'}")
        
        if price.recurring and price.recurring.interval != 'month':
            print(f"   ⚠️  Warning: Price is {price.recurring.interval}, expected 'month'")
    except stripe.error.InvalidRequestError:
        print(f"   ✗ Price ID '{stripe_price_id}' not found")
        return False
    except Exception as e:
        print(f"   ✗ Error retrieving price: {str(e)}")
        return False
    
    print()
    
    # Test creating a checkout session (dry run)
    print("4. Testing Checkout Session Creation:")
    print("-" * 60)
    
    try:
        # Create a test customer
        test_customer = stripe.Customer.create(
            email='test@example.com',
            description='Test customer for verification'
        )
        print(f"   ✓ Test customer created: {test_customer.id}")
        
        # Try to create a checkout session (we'll delete it immediately)
        checkout_session = stripe.checkout.Session.create(
            customer=test_customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel',
        )
        print(f"   ✓ Checkout session created: {checkout_session.id}")
        print(f"   ✓ Checkout URL: {checkout_session.url[:50]}...")
        
        # Clean up test customer
        stripe.Customer.delete(test_customer.id)
        print(f"   ✓ Test customer cleaned up")
        
    except Exception as e:
        print(f"   ✗ Error creating checkout session: {str(e)}")
        return False
    
    print()
    print("=" * 60)
    print("✅ All Stripe tests passed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Set up webhook endpoint in Stripe Dashboard")
    print("2. Add webhook URL: https://keuvi.app/api/v1/payments/webhook")
    print("3. Select events: checkout.session.completed, customer.subscription.*")
    print("4. Copy webhook secret to STRIPE_WEBHOOK_SECRET")
    print()
    
    return True


if __name__ == '__main__':
    success = test_stripe_config()
    sys.exit(0 if success else 1)









