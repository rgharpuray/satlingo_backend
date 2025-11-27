# SAT Prep Reading Comprehension Backend API

Django REST Framework backend API for SAT Prep Reading Comprehension application.

## Features

- Complete REST API implementation matching the API specification
- UUID-based primary keys for all models
- Support for anonymous and authenticated users
- Passage management with questions and options
- User progress tracking
- Answer submission and review
- Admin endpoints for content management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

4. Run the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/v1/`

## API Endpoints

### Passages
- `GET /api/v1/passages` - List all passages
- `GET /api/v1/passages/:id` - Get passage detail
- `GET /api/v1/passages/:id/questions` - Get questions for a passage

### Questions
- `GET /api/v1/questions/:id` - Get a specific question

### Progress
- `GET /api/v1/progress` - Get user's progress across all passages
- `GET /api/v1/progress/passages/:passage_id` - Get progress for a specific passage
- `POST /api/v1/progress/passages/:passage_id/start` - Start a session
- `POST /api/v1/progress/passages/:passage_id/submit` - Submit answers
- `GET /api/v1/progress/passages/:passage_id/review` - Get review data

### Answers
- `POST /api/v1/answers` - Submit an answer
- `GET /api/v1/answers/passage/:passage_id` - Get all answers for a passage

### Admin
- `POST /api/v1/admin/passages` - Create a passage
- `PUT /api/v1/admin/passages/:id` - Update a passage
- `DELETE /api/v1/admin/passages/:id` - Delete a passage

## Database Models

- **Passage**: Reading passages with title, content, and difficulty
- **Question**: Questions associated with passages
- **QuestionOption**: Multiple choice options for questions
- **User**: Custom user model (extends Django's AbstractUser)
- **UserSession**: User session management
- **UserProgress**: Tracks user progress on passages
- **UserAnswer**: Stores user answers to questions

## Development

The project uses:
- Django 4.2+
- Django REST Framework
- SQLite (default, can be changed in settings.py)

## Notes

- All IDs are UUIDs
- Timestamps are in ISO 8601 format (UTC)
- The API supports anonymous users (user_id can be null)
- Authentication can be added by implementing token-based auth or session auth


