#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satlingo.settings')
django.setup()

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
price_id = settings.STRIPE_PRICE_ID

print(f"Checking Stripe Price ID: {price_id}")
print(f"Stripe Secret Key configured: {bool(settings.STRIPE_SECRET_KEY)}")

try:
    price = stripe.Price.retrieve(price_id)
    print(f"✅ Price is valid!")
    print(f"   ID: {price.id}")
    print(f"   Amount: ${price.unit_amount/100} {price.currency}")
    print(f"   Active: {price.active}")
    print(f"   Type: {price.type}")
    if hasattr(price, 'recurring'):
        print(f"   Recurring: {price.recurring}")
except stripe.error.InvalidRequestError as e:
    print(f"❌ Invalid Price ID: {str(e)}")
except stripe.error.StripeError as e:
    print(f"❌ Stripe Error: {str(e)}")
except Exception as e:
    print(f"❌ Error: {str(e)}")

