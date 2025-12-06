# Ingestion Workflow Guide

## Overview

This guide explains how to process passages locally and sync them to production.

## File Storage Location

When you upload files in the admin panel:
- **Location**: `media/ingestions/` (relative to project root)
- **Full path**: `/Users/rishi/argosventures/satlingo_backend/media/ingestions/`
- Files are automatically saved here when you upload via admin panel

## Local Development Workflow

### Step 1: Upload Files (Admin Panel)
1. Go to `http://localhost:8000/admin/api/passageingestion/add/`
2. Select files (images, PDFs, .docx, .txt)
3. Click "Save"
4. Files are saved to `media/ingestions/`
5. Processing starts automatically in background

### Step 2: Process Ingestions (if needed)
If processing didn't complete automatically, or you want to reprocess:

```bash
# Process all pending ingestions
python manage.py process_ingestions

# Process specific ingestion by ID
python manage.py process_ingestions --id <uuid>

# Re-process failed ingestions
python manage.py process_ingestions --failed
```

### Step 3: Export Parsed Data
Export the successfully parsed data for syncing to production:

```bash
# Export all completed ingestions with parsed_data
python manage.py export_ingestions --output passages_export.json

# Export only completed ones
python manage.py export_ingestions --status completed --output passages_export.json
```

This creates `passages_export.json` with all the parsed data ready to import.

## Production Sync Workflow

### Option 1: Direct Database Sync (Recommended)

#### Setup Heroku Postgres

1. **Add Postgres addon to Heroku:**
```bash
heroku addons:create heroku-postgresql:mini --app keuvi
```

2. **Get database URL:**
```bash
heroku config:get DATABASE_URL --app keuvi
```

3. **Update local settings for production DB:**
```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgres://..."
```

4. **Run migrations on production:**
```bash
# Connect to production DB
heroku run python manage.py migrate --app keuvi
```

5. **Import passages directly to production:**
```bash
# Set production DATABASE_URL
export DATABASE_URL="$(heroku config:get DATABASE_URL --app keuvi)"

# Import passages
python manage.py import_passages passages_export.json
```

### Option 2: Export/Import JSON (Safer)

1. **Export locally:**
```bash
python manage.py export_ingestions --output passages_export.json
```

2. **Transfer file to production server:**
```bash
# Copy file to Heroku
heroku run bash --app keuvi
# Then upload passages_export.json via SCP or similar
```

3. **Import on production:**
```bash
heroku run python manage.py import_passages passages_export.json --app keuvi
```

## Database Setup

### Local (SQLite - Default)
- **Location**: `db.sqlite3`
- **Used for**: Development and testing
- **No setup needed** - created automatically

### Production (Heroku Postgres)

1. **Add Postgres addon:**
```bash
heroku addons:create heroku-postgresql:mini --app keuvi
```

2. **Verify it's added:**
```bash
heroku addons --app keuvi
```

3. **DATABASE_URL is automatically set** by Heroku
   - Django will use it via `dj_database_url.config()`

4. **Run migrations:**
```bash
heroku run python manage.py migrate --app keuvi
```

5. **Backfill content_hash (if needed):**
```bash
heroku run python manage.py backfill_content_hash --app keuvi
```

## Complete Workflow Example

### Local Processing:
```bash
# 1. Upload files via admin panel (http://localhost:8000/admin/)
# 2. Wait for automatic processing OR manually process:
python manage.py process_ingestions

# 3. Export parsed data
python manage.py export_ingestions --output my_passages.json
```

### Production Sync:
```bash
# 1. Ensure Heroku Postgres is set up
heroku addons:create heroku-postgresql:mini --app keuvi

# 2. Run migrations
heroku run python manage.py migrate --app keuvi

# 3. Import passages
# Option A: Direct import (if you have DATABASE_URL)
export DATABASE_URL="$(heroku config:get DATABASE_URL --app keuvi)"
python manage.py import_passages my_passages.json

# Option B: Via Heroku CLI
heroku run python manage.py import_passages my_passages.json --app keuvi
# (You'll need to upload the file first)
```

## Environment Variables

### Local Development
- Uses SQLite by default (`db.sqlite3`)
- Can override with `DATABASE_URL` environment variable

### Production (Heroku)
- `DATABASE_URL` - Automatically set by Heroku Postgres addon
- `OPENAI_API_KEY` - Set via: `heroku config:set OPENAI_API_KEY=...`
- `SECRET_KEY` - Set via: `heroku config:set SECRET_KEY=...`

## Troubleshooting

### Files not processing?
```bash
# Check status in admin panel
# Or manually process:
python manage.py process_ingestions --failed
```

### Duplicate detection not working?
```bash
# Backfill content_hash for existing passages
python manage.py backfill_content_hash
```

### Production import fails?
```bash
# Check database connection
heroku run python manage.py dbshell --app keuvi

# Verify migrations are applied
heroku run python manage.py showmigrations --app keuvi
```

