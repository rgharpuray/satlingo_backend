# Heroku Deployment Guide

## Quick Fix for H14 Error (No web processes running)

The H14 error means Heroku doesn't have any web dynos running. Here's how to fix it:

### 1. Scale Up Web Dynos

```bash
# Scale up to 1 web dyno (free tier)
heroku ps:scale web=1

# Or if you have a paid plan
heroku ps:scale web=1 --app keuvi
```

### 2. Check Dyno Status

```bash
heroku ps --app keuvi
```

You should see something like:
```
web.1: up 2024-12-04 04:51:51 +0000 (~ 1m ago)
```

### 3. View Logs

```bash
heroku logs --tail --app keuvi
```

## Files Created for Heroku

1. **Procfile** - Tells Heroku how to run your app
   ```
   web: gunicorn satlingo.wsgi --log-file -
   ```

2. **Updated requirements.txt** - Added:
   - `gunicorn` - WSGI HTTP server
   - `whitenoise` - Static file serving
   - `dj-database-url` - Database URL parsing

3. **Updated settings.py** - Added:
   - WhiteNoise middleware for static files
   - Production database configuration
   - Environment-based DEBUG setting

## Deployment Steps

### 1. Commit Changes

```bash
git add Procfile requirements.txt satlingo/settings.py
git commit -m "Add Heroku deployment configuration"
```

### 2. Push to Heroku

```bash
git push heroku main
# or
git push heroku master
```

### 3. Run Migrations

```bash
heroku run python manage.py migrate --app keuvi
```

### 4. Collect Static Files

```bash
heroku run python manage.py collectstatic --noinput --app keuvi
```

### 5. Create Superuser (if needed)

```bash
heroku run python manage.py createsuperuser --app keuvi
```

### 6. Set Environment Variables

```bash
# Set required environment variables
heroku config:set SECRET_KEY='your-secret-key-here' --app keuvi
heroku config:set DEBUG=False --app keuvi
heroku config:set ALLOWED_HOSTS=keuvi.app,www.keuvi.app --app keuvi

# Optional: Set other configs
heroku config:set OPENAI_API_KEY='your-key' --app keuvi
heroku config:set STRIPE_SECRET_KEY='your-key' --app keuvi
```

### 7. Scale Web Dynos

```bash
heroku ps:scale web=1 --app keuvi
```

## Verify Deployment

1. Check if dynos are running:
   ```bash
   heroku ps --app keuvi
   ```

2. Visit your app:
   ```
   https://keuvi.app
   ```

3. Check logs for errors:
   ```bash
   heroku logs --tail --app keuvi
   ```

## Common Issues

### H14 Error (No web processes)
- **Fix**: Run `heroku ps:scale web=1`

### Static files not loading
- **Fix**: Run `heroku run python manage.py collectstatic --noinput`

### Database errors
- **Fix**: Run `heroku run python manage.py migrate`

### 503 Service Unavailable
- Check logs: `heroku logs --tail`
- Verify dynos are running: `heroku ps`

## Notes

- The errors show requests to `/api/graphql` which don't exist in this Django app
- Those might be from a different service or bot trying wrong endpoints
- Your Django app serves `/api/v1/` endpoints, not GraphQL

