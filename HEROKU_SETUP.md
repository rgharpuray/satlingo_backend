# Heroku Postgres Setup Guide

## Step 1: Add Heroku Postgres Addon

```bash
# Add Postgres mini (free tier) to your Heroku app
heroku addons:create heroku-postgresql:mini --app keuvi

# Verify it was added
heroku addons --app keuvi
```

## Step 2: Verify DATABASE_URL is Set

Heroku automatically sets `DATABASE_URL` when you add Postgres. Verify:

```bash
heroku config:get DATABASE_URL --app keuvi
```

You should see a PostgreSQL connection string like:
```
postgres://user:password@host:port/database
```

## Step 3: Run Migrations on Production

```bash
# Run migrations on Heroku (uses DATABASE_URL automatically)
heroku run python manage.py migrate --app keuvi

# Create superuser on production (if needed)
heroku run python manage.py createsuperuser --app keuvi
```

## Step 4: Backfill Content Hash (for duplicate detection)

```bash
heroku run python manage.py backfill_content_hash --app keuvi
```

## Step 5: Deploy Your Code

```bash
git add .
git commit -m "Configure for Heroku Postgres"
git push heroku main
```

## How It Works

### Production (Heroku)
- Heroku automatically sets `DATABASE_URL` environment variable
- Django uses `dj_database_url.config()` which reads `DATABASE_URL`
- All data goes to Heroku Postgres
- Upload passages via admin panel → stored in Postgres

### Local Development
- No `DATABASE_URL` set → defaults to SQLite (`db.sqlite3`)
- All local data stays in SQLite
- Upload passages via admin panel → stored in local SQLite

## Verify Setup

### Check Production Database
```bash
# Connect to production database
heroku pg:psql --app keuvi

# List tables
\dt

# Check passages
SELECT COUNT(*) FROM passages;
```

### Check Local Database
```bash
# Local uses SQLite
python manage.py dbshell

# Or check file
ls -lh db.sqlite3
```

## Environment Variables on Heroku

Make sure these are set:
```bash
# Check all config vars
heroku config --app keuvi

# Set if missing
heroku config:set OPENAI_API_KEY=your_key --app keuvi
heroku config:set SECRET_KEY=your_secret_key --app keuvi
heroku config:set DEBUG=False --app keuvi
```

## Troubleshooting

### Database connection issues
```bash
# Check database status
heroku pg:info --app keuvi

# Check connection
heroku pg:psql --app keuvi -c "SELECT version();"
```

### Migrations not running
```bash
# Force migrations
heroku run python manage.py migrate --app keuvi --run-syncdb
```

### Static files not loading
```bash
# Collect static files
heroku run python manage.py collectstatic --noinput --app keuvi
```

