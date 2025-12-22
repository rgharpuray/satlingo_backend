#!/bin/bash
# Set Stripe webhook secret on Heroku
# Replace 'your-app-name' with your actual Heroku app name

heroku config:set STRIPE_WEBHOOK_SECRET='whsec_jwwBIkszH9yYFY9SssP83Uu0lXCudUfo' --app your-app-name

