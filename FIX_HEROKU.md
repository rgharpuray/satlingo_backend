# Fix Heroku Database Setup

## The Problem
Your Heroku app is still using SQLite instead of Postgres. That's why you're getting "no such table: users" error.

## Quick Fix - Run These Commands:

```bash
# 1. Add Heroku Postgres (essential-0 tier - $5/month, or check for free tier)
heroku addons:create heroku-postgresql:essential-0 --app keuvi

# Alternative: Check available plans first
# heroku addons:plans heroku-postgresql

# 2. Verify DATABASE_URL is now set
heroku config:get DATABASE_URL --app keuvi

# 3. Run migrations on production
heroku run python manage.py migrate --app keuvi

# 4. Create superuser (if you don't have one)
heroku run python manage.py createsuperuser --app keuvi

# 5. Backfill content_hash (for duplicate detection)
heroku run python manage.py backfill_content_hash --app keuvi
```

## After This:
- Your production will use Postgres
- You can login to admin panel
- Upload passages will be stored in Postgres

## Verify It Worked:
```bash
# Check database type
heroku run python manage.py dbshell --app keuvi
# Should show PostgreSQL, not SQLite
```

