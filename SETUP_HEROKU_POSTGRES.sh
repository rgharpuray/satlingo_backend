#!/bin/bash
# Quick setup script for Heroku Postgres

echo "🚀 Setting up Heroku Postgres for keuvi app..."

# Step 1: Add Postgres addon
echo "📦 Adding Heroku Postgres (mini tier)..."
heroku addons:create heroku-postgresql:mini --app keuvi

# Step 2: Verify DATABASE_URL is set
echo "✅ Verifying DATABASE_URL..."
heroku config:get DATABASE_URL --app keuvi

# Step 3: Run migrations
echo "🔄 Running migrations on production..."
heroku run python manage.py migrate --app keuvi

# Step 4: Backfill content_hash for duplicate detection
echo "🔍 Backfilling content_hash for duplicate detection..."
heroku run python manage.py backfill_content_hash --app keuvi

# Step 5: Verify setup
echo "✅ Setup complete! Verifying..."
heroku pg:info --app keuvi

echo ""
echo "🎉 Done! Your production database is now using Heroku Postgres."
echo ""
echo "To upload passages on production:"
echo "1. Go to: https://keuvi.app/admin/"
echo "2. Login with your superuser account"
echo "3. Upload files in Passage Ingestion"
echo "4. All data will be stored in Heroku Postgres"
echo ""
echo "Local development still uses SQLite (db.sqlite3)"

