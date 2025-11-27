# Local Development Setup Guide

Step-by-step instructions to run the Django server locally.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

## Quick Start

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

Or if you prefer using a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Database

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations to create database tables
python manage.py migrate
```

This will create a `db.sqlite3` file in your project directory.

### 3. Create Superuser (Optional)

Create an admin user to access the Django admin interface:

```bash
python manage.py createsuperuser
```

Follow the prompts to set email, username, and password.

### 4. Run the Server

```bash
python manage.py runserver
```

The server will start at: **http://localhost:8000**

The API will be available at: **http://localhost:8000/api/v1/**

### 5. Test the API

Open your browser or use curl:

```bash
# Test the API
curl http://localhost:8000/api/v1/passages
```

Or visit in your browser:
- API Root: http://localhost:8000/api/v1/
- Django Admin: http://localhost:8000/admin/

## Running on a Different Port

```bash
# Run on port 8080
python manage.py runserver 8080

# Run on all interfaces (accessible from network)
python manage.py runserver 0.0.0.0:8000
```

## Common Commands

### Database Management

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Reset database (WARNING: deletes all data)
rm db.sqlite3
python manage.py migrate
```

### Django Shell

```bash
# Open Django shell for database queries
python manage.py shell
```

### Create Sample Data

You can create sample data using the Django admin or via the API:

```bash
# Using curl to create a passage
curl -X POST http://localhost:8000/api/v1/admin/passages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sample Passage",
    "content": "This is a sample reading passage...",
    "difficulty": "Medium",
    "questions": [
      {
        "text": "What is the main idea?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer_index": 0,
        "explanation": "The main idea is...",
        "order": 0
      }
    ]
  }'
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Find what's using the port
lsof -i :8000

# Or use a different port
python manage.py runserver 8080
```

### Module Not Found Errors

```bash
# Make sure you're in the project directory
cd /path/to/satlingo_backend

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Errors

```bash
# Delete database and recreate
rm db.sqlite3
python manage.py migrate
```

### Migration Errors

```bash
# Reset migrations (if needed)
python manage.py migrate --run-syncdb
```

## Development Tips

1. **Auto-reload**: Django automatically reloads when you change code
2. **Debug Mode**: `DEBUG=True` in settings.py shows detailed error pages
3. **CORS**: CORS is enabled for localhost in development
4. **Logs**: Check terminal output for request logs and errors

## Next Steps

1. Test the API endpoints using the examples in `API_INTEGRATION.md`
2. Create sample passages using the admin endpoints
3. Use the example clients in `example_client.js` or `example_client.py`

## Production Deployment

For production:
1. Set `DEBUG=False` in `settings.py`
2. Set a secure `SECRET_KEY` environment variable
3. Configure a production database (PostgreSQL recommended)
4. Set up proper CORS origins
5. Use a production WSGI server (gunicorn, uwsgi)
6. Set up static file serving


