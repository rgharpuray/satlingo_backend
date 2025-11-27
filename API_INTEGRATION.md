# SAT Prep Reading Comprehension API - Integration Guide

This document provides complete integration documentation for the SAT Prep Reading Comprehension Backend API.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

The API supports both **anonymous users** and **authenticated users** with JWT tokens.

### Anonymous Users
- No authentication headers required
- User progress and answers are tracked per session (if implemented)
- Can only access free content

### Authenticated Users
- Include JWT token in requests: `Authorization: Bearer <access_token>`
- Progress and answers are saved to user account
- Premium users can access premium content
- See `AUTHENTICATION_SPEC.md` for complete authentication guide

## Content Type

All requests and responses use JSON:
- **Content-Type**: `application/json`
- **Accept**: `application/json`

## Response Format

### Success Response
All successful responses return JSON with the requested data.

### Error Response
All errors follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes
- `NOT_FOUND` (404): Resource not found
- `BAD_REQUEST` (400): Invalid request data
- `UNAUTHORIZED` (401): Authentication required
- `FORBIDDEN` (403): Insufficient permissions
- `INTERNAL_ERROR` (500): Server error

---

## Endpoints

### 1. Passages

#### 1.1 List All Passages
Get all passages with optional filtering.

**Endpoint:** `GET /passages`

**Query Parameters:**
- `difficulty` (optional): Filter by difficulty (`Easy`, `Medium`, `Hard`)
- `tier` (optional): Filter by tier (`free`, `premium`)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example Request:**
```bash
GET /api/v1/passages?difficulty=Medium&limit=10
```

**Example Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Phrenology",
      "content": "Full passage text...",
      "difficulty": "Medium",
      "tier": "free",
      "question_count": 6,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 1.2 Get Passage Detail
Get a specific passage with all questions and options (includes correct answers - use with caution).

**Endpoint:** `GET /passages/{passage_id}`

**Example Request:**
```bash
GET /api/v1/passages/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Phrenology",
  "content": "Full passage text...",
  "difficulty": "Medium",
  "tier": "free",
  "questions": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "text": "The author's view of phrenology can be best described as:",
      "options": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440002",
          "text": "utterly scornful",
          "order": 0
        },
        {
          "id": "770e8400-e29b-41d4-a716-446655440003",
          "text": "hopeful",
          "order": 1
        },
        {
          "id": "770e8400-e29b-41d4-a716-446655440004",
          "text": "mixed",
          "order": 2
        },
        {
          "id": "770e8400-e29b-41d4-a716-446655440005",
          "text": "indifferent",
          "order": 3
        }
      ],
      "options_list": [
        "utterly scornful",
        "hopeful",
        "mixed",
        "indifferent"
      ],
      "correct_answer_index": 2,
      "explanation": "The author acknowledges both phrenology's flaws...",
      "order": 0
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Note:** This endpoint includes correct answers. For active sessions, use `/passages/{id}/questions` instead.

#### 1.3 Get Passage Questions (Without Answers)
Get questions for a passage without correct answers/explanations (for active sessions).

**Endpoint:** `GET /passages/{passage_id}/questions`

**Example Request:**
```bash
GET /api/v1/passages/550e8400-e29b-41d4-a716-446655440000/questions
```

**Example Response:**
```json
{
  "questions": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "text": "The author's view of phrenology can be best described as:",
      "options": [
        "utterly scornful",
        "hopeful",
        "mixed",
        "indifferent"
      ],
      "order": 0
    }
  ]
}
```

---

### 2. Questions

#### 2.1 Get Question Detail
Get a specific question with options (without correct answer for active sessions).

**Endpoint:** `GET /questions/{question_id}`

**Example Request:**
```bash
GET /api/v1/questions/660e8400-e29b-41d4-a716-446655440001
```

**Example Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "text": "The author's view of phrenology can be best described as:",
  "options": [
    "utterly scornful",
    "hopeful",
    "mixed",
    "indifferent"
  ],
  "order": 0
}
```

---

### 3. User Progress

#### 3.1 Get User Progress Summary
Get user's progress across all passages.

**Endpoint:** `GET /progress`

**Example Request:**
```bash
GET /api/v1/progress
```

**Example Response:**
```json
{
  "completed_passages": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "scores": {
    "550e8400-e29b-41d4-a716-446655440000": 85,
    "550e8400-e29b-41d4-a716-446655440001": 92
  },
  "total_passages": 10,
  "completed_count": 2
}
```

#### 3.2 Get Passage Progress
Get user's progress for a specific passage.

**Endpoint:** `GET /progress/passages/{passage_id}`

**Example Request:**
```bash
GET /api/v1/progress/passages/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440006",
  "passage_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_completed": true,
  "score": 85,
  "time_spent_seconds": 245,
  "completed_at": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T11:55:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

#### 3.3 Start Passage Session
Start a new session for a passage (for tracking time).

**Endpoint:** `POST /progress/passages/{passage_id}/start`

**Example Request:**
```bash
POST /api/v1/progress/passages/550e8400-e29b-41d4-a716-446655440000/start
Content-Type: application/json

{
  "started_at": "2024-01-01T11:55:00Z"
}
```

**Example Response:**
```json
{
  "session_id": "990e8400-e29b-41d4-a716-446655440007",
  "passage_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2024-01-01T11:55:00Z"
}
```

#### 3.4 Submit Passage Answers
Submit answers for a passage and get results.

**Endpoint:** `POST /progress/passages/{passage_id}/submit`

**Example Request:**
```bash
POST /api/v1/progress/passages/550e8400-e29b-41d4-a716-446655440000/submit
Content-Type: application/json

{
  "answers": [
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "selected_option_index": 2
    },
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440002",
      "selected_option_index": 1
    }
  ],
  "time_spent_seconds": 245
}
```

**Example Response:**
```json
{
  "passage_id": "550e8400-e29b-41d4-a716-446655440000",
  "score": 85,
  "total_questions": 6,
  "correct_count": 5,
  "is_completed": true,
  "answers": [
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "selected_option_index": 2,
      "correct_answer_index": 2,
      "is_correct": true,
      "explanation": "The author acknowledges both phrenology's flaws..."
    },
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440002",
      "selected_option_index": 1,
      "correct_answer_index": 2,
      "is_correct": false,
      "explanation": "The correct answer is option C..."
    }
  ],
  "completed_at": "2024-01-01T12:00:00Z"
}
```

#### 3.5 Get Passage Review
Get review data for a completed passage (includes correct answers and explanations).

**Endpoint:** `GET /progress/passages/{passage_id}/review`

**Example Request:**
```bash
GET /api/v1/progress/passages/550e8400-e29b-41d4-a716-446655440000/review
```

**Example Response:**
```json
{
  "passage_id": "550e8400-e29b-41d4-a716-446655440000",
  "score": 85,
  "answers": [
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "question_text": "The author's view of phrenology can be best described as:",
      "options": [
        "utterly scornful",
        "hopeful",
        "mixed",
        "indifferent"
      ],
      "selected_option_index": 2,
      "correct_answer_index": 2,
      "is_correct": true,
      "explanation": "The author acknowledges both phrenology's flaws..."
    }
  ]
}
```

---

### 4. User Answers

#### 4.1 Submit Answer
Submit an answer for a question (for real-time tracking, optional).

**Endpoint:** `POST /answers`

**Example Request:**
```bash
POST /api/v1/answers
Content-Type: application/json

{
  "question_id": "660e8400-e29b-41d4-a716-446655440001",
  "selected_option_index": 2
}
```

**Example Response:**
```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440008",
  "question_id": "660e8400-e29b-41d4-a716-446655440001",
  "selected_option_index": 2,
  "is_correct": true,
  "answered_at": "2024-01-01T11:56:00Z",
  "created_at": "2024-01-01T11:56:00Z",
  "updated_at": "2024-01-01T11:56:00Z"
}
```

#### 4.2 Get Answers for Passage
Get all user's answers for a passage.

**Endpoint:** `GET /answers/passage/{passage_id}`

**Example Request:**
```bash
GET /api/v1/answers/passage/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "answers": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440008",
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "selected_option_index": 2,
      "is_correct": true,
      "answered_at": "2024-01-01T11:56:00Z",
      "created_at": "2024-01-01T11:56:00Z",
      "updated_at": "2024-01-01T11:56:00Z"
    }
  ]
}
```

---

### 5. Admin Endpoints

#### 5.1 Create Passage
Create a new passage with questions and options.

**Endpoint:** `POST /admin/passages`

**Example Request:**
```bash
POST /api/v1/admin/passages
Content-Type: application/json

{
  "title": "New Passage Title",
  "content": "Full passage text...",
  "difficulty": "Medium",
  "questions": [
    {
      "text": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 2,
      "explanation": "Explanation text...",
      "order": 0
    }
  ]
}
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "New Passage Title",
  "content": "Full passage text...",
  "difficulty": "Medium",
  "questions": [...],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 5.2 Update Passage
Update an existing passage.

**Endpoint:** `PUT /admin/passages/{passage_id}`

**Example Request:**
```bash
PUT /api/v1/admin/passages/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "title": "Updated Passage Title",
  "content": "Updated passage text...",
  "difficulty": "Hard",
  "questions": [...]
}
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Updated Passage Title",
  "content": "Updated passage text...",
  "difficulty": "Hard",
  "questions": [...],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T01:00:00Z"
}
```

#### 5.3 Delete Passage
Delete a passage.

**Endpoint:** `DELETE /admin/passages/{passage_id}`

**Example Request:**
```bash
DELETE /api/v1/admin/passages/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```
204 No Content
```

---

## Data Models

### Passage
```typescript
interface Passage {
  id: string; // UUID
  title: string;
  content: string;
  difficulty: "Easy" | "Medium" | "Hard";
  tier: "free" | "premium";
  question_count?: number; // Only in list view
  questions?: Question[]; // Only in detail view
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

### Question
```typescript
interface Question {
  id: string; // UUID
  passage_id?: string; // UUID (optional, depends on context)
  text: string;
  options: string[]; // Array of option texts (for active sessions)
  // OR
  options?: Option[]; // Full option objects (in detail view)
  correct_answer_index?: number; // Only in detail/review views
  explanation?: string | null; // Only in detail/review views
  order: number;
  created_at?: string;
  updated_at?: string;
}

interface Option {
  id: string; // UUID
  text: string;
  order: number;
}
```

### UserProgress
```typescript
interface UserProgress {
  id: string; // UUID
  passage_id: string; // UUID
  is_completed: boolean;
  score: number | null; // 0-100
  time_spent_seconds: number | null;
  completed_at: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

### UserAnswer
```typescript
interface UserAnswer {
  id: string; // UUID
  question_id: string; // UUID
  selected_option_index: number | null;
  is_correct: boolean | null;
  answered_at: string; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

### Submit Answer Request
```typescript
interface SubmitAnswerRequest {
  question_id: string; // UUID
  selected_option_index: number; // 0-based index
}
```

### Submit Passage Request
```typescript
interface SubmitPassageRequest {
  answers: Array<{
    question_id: string; // UUID
    selected_option_index: number; // 0-based index
  }>;
  time_spent_seconds?: number;
}
```

### Submit Passage Response
```typescript
interface SubmitPassageResponse {
  passage_id: string; // UUID
  score: number; // 0-100
  total_questions: number;
  correct_count: number;
  is_completed: boolean;
  answers: Array<{
    question_id: string; // UUID
    selected_option_index: number;
    correct_answer_index: number;
    is_correct: boolean;
    explanation: string | null;
  }>;
  completed_at: string; // ISO 8601
}
```

---

## Example Integration Flow

### Complete Passage Flow

#### 1. Get all passages
```javascript
const response = await fetch('http://localhost:8000/api/v1/passages');
const data = await response.json();
// data.results contains array of passages
```

#### 2. Start a passage session (optional)
```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/progress/passages/${passageId}/start`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      started_at: new Date().toISOString()
    })
  }
);
const session = await response.json();
// session.session_id can be used for tracking
```

#### 3. Get passage with questions (without answers)
```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/passages/${passageId}/questions`
);
const data = await response.json();
// data.questions contains questions with options (no correct answers)
```

#### 4. Submit answers as user progresses (optional)
```javascript
await fetch('http://localhost:8000/api/v1/answers', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question_id: questionId,
    selected_option_index: selectedIndex
  })
});
```

#### 5. Submit final attempt
```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/progress/passages/${passageId}/submit`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      answers: [
        { question_id: 'q1', selected_option_index: 2 },
        { question_id: 'q2', selected_option_index: 1 }
      ],
      time_spent_seconds: 245
    })
  }
);
const results = await response.json();
// results contains score, correct_count, and answer feedback
```

#### 6. Get review with explanations
```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/progress/passages/${passageId}/review`
);
const review = await response.json();
// review contains all questions with correct answers and explanations
```

---

## Important Notes

### Answer Indexing
- All answer indices are **0-based** (0 = first option, 1 = second option, etc.)
- Questions typically have 4 options (A, B, C, D), but the schema supports any number

### UUID Format
- All IDs are UUIDs in standard UUID v4 format
- Example: `550e8400-e29b-41d4-a716-446655440000`

### Timestamps
- All timestamps are in **ISO 8601 format (UTC)**
- Example: `2024-01-01T00:00:00Z`

### Security Considerations
1. **Answer Validation**: Correct answers are not exposed until the user submits their attempt
2. **Rate Limiting**: Consider implementing rate limiting on the client side
3. **Input Validation**: Validate all inputs before sending requests
4. **Error Handling**: Always handle error responses gracefully

### Pagination
- List endpoints support pagination via `limit` and `offset` query parameters
- Response includes `count`, `next`, and `previous` fields for navigation

### Anonymous Users
- The API currently supports anonymous users
- Progress and answers may not persist across sessions for anonymous users
- Consider implementing session tracking or requiring authentication for persistent data

---

## Testing

### Using cURL

```bash
# Get all passages
curl http://localhost:8000/api/v1/passages

# Get passage questions
curl http://localhost:8000/api/v1/passages/{passage_id}/questions

# Submit answers
curl -X POST http://localhost:8000/api/v1/progress/passages/{passage_id}/submit \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "q1", "selected_option_index": 2}
    ],
    "time_spent_seconds": 120
  }'
```

### Using JavaScript/TypeScript

```typescript
// Example API client
class SATPrepAPI {
  constructor(private baseURL: string = 'http://localhost:8000/api/v1') {}

  async getPassages(difficulty?: string) {
    const url = new URL(`${this.baseURL}/passages`);
    if (difficulty) url.searchParams.set('difficulty', difficulty);
    const response = await fetch(url.toString());
    return response.json();
  }

  async getPassageQuestions(passageId: string) {
    const response = await fetch(
      `${this.baseURL}/passages/${passageId}/questions`
    );
    return response.json();
  }

  async submitPassage(passageId: string, answers: any[], timeSpent: number) {
    const response = await fetch(
      `${this.baseURL}/progress/passages/${passageId}/submit`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answers,
          time_spent_seconds: timeSpent
        })
      }
    );
    return response.json();
  }
}
```

---

## Support

For issues or questions:
1. Check the error response for detailed error messages
2. Verify request format matches the examples
3. Ensure all required fields are included
4. Check that UUIDs are in correct format

---

## Changelog

### Version 1.0.0
- Initial API release
- Support for passages, questions, progress tracking
- Anonymous user support
- Admin endpoints for content management

