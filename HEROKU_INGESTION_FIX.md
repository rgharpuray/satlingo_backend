# Heroku Ingestion Processing Fix

## Problem
On Heroku, background threads (daemon threads) are killed when the HTTP request completes. This means ingestion processing that starts in the background may not complete.

## Solution

### Option 1: Use Admin Action (Recommended)
1. Upload files in the admin panel
2. If processing gets stuck on "Processing", select the ingestion(s)
3. Use the "Process selected ingestions" admin action
4. This will restart processing in a new background thread

### Option 2: Use Management Command
If the admin action doesn't work, use the management command:

```bash
# Process all pending ingestions
heroku run python manage.py process_ingestions --app keuvi

# Process a specific ingestion by ID
heroku run python manage.py process_ingestions --id <uuid> --app keuvi

# Re-process failed ingestions
heroku run python manage.py process_ingestions --failed --app keuvi
```

### Option 3: Check Error Messages
If processing fails, check the `error_message` field in the admin panel. It will contain the full error traceback.

## Why This Happens
- Heroku dynos kill daemon threads when HTTP requests complete
- Background processing needs to run in a separate process or use a task queue
- For now, use the admin action or management command to manually trigger processing

## Future Improvement
Consider using Celery or another task queue for reliable background processing on Heroku.









