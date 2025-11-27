# API Quick Reference

Quick reference guide for common API operations.

## Base URL
```
http://localhost:8000/api/v1
```

## Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/passages` | GET | List all passages |
| `/passages/{id}` | GET | Get passage detail |
| `/passages/{id}/questions` | GET | Get questions (no answers) |
| `/questions/{id}` | GET | Get question detail |
| `/progress` | GET | Get user progress summary |
| `/progress/passages/{id}` | GET | Get passage progress |
| `/progress/passages/{id}/start` | POST | Start session |
| `/progress/passages/{id}/submit` | POST | Submit answers |
| `/progress/passages/{id}/review` | GET | Get review data |
| `/answers` | POST | Submit single answer |
| `/answers/passage/{id}` | GET | Get answers for passage |

## Request Examples

### Get Passages
```bash
GET /api/v1/passages?difficulty=Medium
```

### Get Questions (No Answers)
```bash
GET /api/v1/passages/{passage_id}/questions
```

### Submit Answers
```bash
POST /api/v1/progress/passages/{passage_id}/submit
{
  "answers": [
    {"question_id": "uuid", "selected_option_index": 2}
  ],
  "time_spent_seconds": 245
}
```

### Get Review
```bash
GET /api/v1/progress/passages/{passage_id}/review
```

## Response Codes

- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Server Error

## Data Types

- **IDs**: UUID v4 strings
- **Timestamps**: ISO 8601 (UTC)
- **Indices**: 0-based integers
- **Difficulty**: "Easy" | "Medium" | "Hard"

## Notes

- Answer indices are 0-based (0 = first option)
- All timestamps in UTC
- No authentication required (for now)
- Use `/passages/{id}/questions` for active sessions (no correct answers)


