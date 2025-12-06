# Quick Start: Ingestion Workflow

## TL;DR - Complete Workflow

### Local Development

1. **Upload files in admin panel:**
   - Go to: `http://localhost:8000/admin/api/passageingestion/add/`
   - Select files → Save
   - Files saved to: `media/ingestions/`
   - Processing starts automatically

2. **If processing didn't complete:**
   ```bash
   python manage.py process_ingestions
   ```

3. **Export for production:**
   ```bash
   python manage.py export_ingestions --output passages.json
   ```

### Production Setup

1. **Add Heroku Postgres:**
   ```bash
   heroku addons:create heroku-postgresql:mini --app keuvi
   ```

2. **Run migrations:**
   ```bash
   heroku run python manage.py migrate --app keuvi
   ```

3. **Import passages:**
   ```bash
   # Set production DB
   export DATABASE_URL="$(heroku config:get DATABASE_URL --app keuvi)"
   
   # Import
   python manage.py import_passages passages.json
   ```

## File Locations

- **Uploaded files**: `media/ingestions/` (local filesystem)
- **Local database**: `db.sqlite3` (SQLite)
- **Production database**: Heroku Postgres (via `DATABASE_URL`)

## Commands Reference

```bash
# Process ingestions
python manage.py process_ingestions              # All pending
python manage.py process_ingestions --failed      # Re-process failed
python manage.py process_ingestions --id <uuid>   # Specific one

# Export parsed data
python manage.py export_ingestions --output passages.json

# Import to production
python manage.py import_passages passages.json

# Backfill content_hash (for duplicate detection)
python manage.py backfill_content_hash
```

## Environment Setup

### Local
- Uses SQLite (`db.sqlite3`) by default
- Files in `media/ingestions/`

### Production
- Uses Heroku Postgres (set via `DATABASE_URL`)
- Files should be processed locally, then imported

## Important Notes

1. **Process locally** - Don't process files on Heroku (expensive, slow)
2. **Export parsed_data** - Only export the JSON, not the files
3. **Import to production** - Import the JSON to create passages
4. **Duplicate detection** - Automatically prevents duplicates during import

