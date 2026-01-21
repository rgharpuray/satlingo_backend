# Keuvi iOS App Specification

## Overview
Keuvi is an SAT tutoring app featuring lessons, practice passages, and diagnostic tests across three categories: Reading, Writing, and Math. The app tracks user progress, identifies strengths and weaknesses, and provides personalized study recommendations.

**Backend API Base URL:** `https://keuvi.app/api/v1`

### API Endpoints by Environment

| Environment | Base URL | Notes |
|-------------|----------|-------|
| **Production** | `https://keuvi.app/api/v1` | Live server on Heroku |
| **Local (Simulator)** | `http://localhost:8000/api/v1` | Default Django dev server |
| **Local (Physical Device)** | `http://<your-mac-ip>:8000/api/v1` | Run server with `python manage.py runserver 0.0.0.0:8000` |

**Notes:**
- CORS is configured to allow all origins in development mode
- Native iOS apps bypass CORS restrictions, so production API works without additional configuration
- For physical device testing, find your Mac's IP via `ifconfig | grep "inet "` and use that IP

---

## 1. Authentication System

### 1.1 Storage
- Store JWT access token in Keychain (secure storage)
- Store refresh token in Keychain
- Store user email in UserDefaults for display

### 1.2 API Endpoints

#### Register
```
POST /auth/register
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "password123"  // min 8 characters
}

Response (200):
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_premium": false,
    "has_active_subscription": false
  },
  "tokens": {
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
  }
}

Error Response (400):
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Email already exists"
  }
}
```

#### Login
```
POST /auth/login
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "password123"
}

Response (200):
{
  "user": { ... },
  "tokens": {
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
  }
}
```

#### Google OAuth

**iOS Client ID:** `412415832820-s8dqgts2es0mtbc7efkqjui5l5ed2sgk.apps.googleusercontent.com`

**Option 1: Google Sign-In SDK (Recommended for iOS)**

Use Google Sign-In SDK to get an ID token, then send it to the backend:

```
POST /auth/google/token
Content-Type: application/json

{
  "id_token": "<google_id_token_from_sdk>"
}

Response (200):
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "user",
    "is_premium": false
  },
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

Swift example with Google Sign-In SDK:
```swift
import GoogleSignIn

func signInWithGoogle() {
    guard let presentingVC = UIApplication.shared.windows.first?.rootViewController else { return }
    
    GIDSignIn.sharedInstance.signIn(withPresenting: presentingVC) { result, error in
        guard let user = result?.user, let idToken = user.idToken?.tokenString else {
            print("Google Sign-In failed: \(error?.localizedDescription ?? "Unknown")")
            return
        }
        
        // Send ID token to backend
        Task {
            do {
                let tokens = try await APIService.shared.verifyGoogleToken(idToken: idToken)
                // Store tokens and update auth state
            } catch {
                print("Backend verification failed: \(error)")
            }
        }
    }
}

// In APIService:
func verifyGoogleToken(idToken: String) async throws -> AuthResponse {
    var request = URLRequest(url: baseURL.appendingPathComponent("auth/google/token"))
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONEncoder().encode(["id_token": idToken])
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(AuthResponse.self, from: data)
}
```

**Option 2: Web OAuth Flow (ASWebAuthenticationSession)**

For web-style OAuth flow:

```
GET /auth/google/url

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```
Open this URL in ASWebAuthenticationSession. After OAuth completes, the callback will contain tokens.

```
GET /auth/google/callback?code=<authorization_code>

Response (200):
{
  "user": { ... },
  "tokens": {
    "access": "...",
    "refresh": "..."
  }
}
```

#### Get Current User
```
GET /auth/me
Authorization: Bearer <access_token>

Response (200):
{
  "id": "uuid",
  "email": "user@example.com",
  "is_premium": false,
  "has_active_subscription": false
}
```

#### Refresh Token
```
POST /auth/refresh
Content-Type: application/json

Request:
{
  "refresh": "jwt_refresh_token"
}

Response (200):
{
  "access": "new_jwt_access_token"
}
```

### 1.3 Auth Flow
1. On app launch, check for stored access token
2. If token exists, call `/auth/me` to validate
3. If 401 response, try token refresh with stored refresh token
4. If refresh fails, clear tokens and show login screen
5. Include `Authorization: Bearer <token>` header on all authenticated requests

---

## 2. Content Structure

### 2.1 Categories
The app has three main categories:
- **Reading** - Lessons + Passages (practice questions)
- **Writing** - Lessons only
- **Math** - Lessons only

### 2.2 Content Types

#### Lessons
Educational content with optional practice questions. Each lesson belongs to a category (reading/writing/math) and optionally a header/section.

#### Passages (Reading only)
Practice passages with multiple-choice questions. Include annotations that appear after answering.

### 2.3 Tier System
- **Free tier**: Limited content (intro lessons only for non-logged-in users)
- **Premium tier**: Full access ($5/month via Stripe)

---

## 3. API Endpoints - Content

### 3.1 Lessons

#### List Lessons (by type)
```
GET /lessons/?lesson_type=reading|writing|math
Authorization: Bearer <token> (optional)

Response (200):
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Subject-Verb Agreement",
      "lesson_type": "writing",
      "tier": "free",
      "is_diagnostic": false,
      "header": {
        "id": "uuid",
        "title": "Grammar Basics",
        "category": "writing",
        "display_order": 10
      },
      "order_within_header": 5,
      "question_count": 3,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### Get Lesson Detail
```
GET /lessons/<lesson_id>/
Authorization: Bearer <token> (required for premium)

Response (200):
{
  "id": "uuid",
  "title": "Subject-Verb Agreement",
  "content": [
    {
      "type": "text",
      "content": "A subject and verb must agree in number..."
    },
    {
      "type": "example",
      "content": "The dog runs. (singular)"
    },
    {
      "type": "diagram",
      "diagram_id": "diagram-1"
    }
  ],
  "lesson_type": "writing",
  "tier": "free",
  "is_diagnostic": false,
  "questions": [
    {
      "id": "uuid",
      "text": [
        {"type": "text", "content": "Which sentence is correct?"}
      ],
      "options": [
        {"id": "uuid", "text": "The dogs runs.", "order": 0},
        {"id": "uuid", "text": "The dogs run.", "order": 1}
      ],
      "correct_answer_index": 1,
      "explanation": [
        {"type": "text", "content": "\"Dogs\" is plural..."}
      ],
      "order": 0,
      "chunk_index": 0,
      "assets": []
    }
  ],
  "assets": [
    {
      "id": "uuid",
      "asset_id": "diagram-1",
      "type": "diagram",
      "s3_url": "https://keuvi.s3.amazonaws.com/..."
    }
  ]
}

Error Response (403 - Premium Required):
{
  "error": {
    "code": "PREMIUM_REQUIRED",
    "message": "This lesson requires a premium subscription",
    "upgrade_url": "/web/subscription"
  }
}
```

### 3.2 Passages (Reading)

#### List Passages
```
GET /passages/
Authorization: Bearer <token> (optional)

Response (200):
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "title": "The Science of Sleep",
      "content": "Sleep is essential...",
      "difficulty": "Medium",
      "tier": "free",
      "is_diagnostic": false,
      "header": {
        "id": "uuid",
        "title": "Science Passages",
        "display_order": 5
      },
      "order_within_header": 3,
      "question_count": 5,
      "attempt_count": 2,
      "attempt_summary": {
        "total_attempts": 2,
        "best_score": 80,
        "latest_score": 60,
        "recent_attempts": [
          {
            "id": "uuid",
            "score": 60,
            "correct_count": 3,
            "total_questions": 5,
            "completed_at": "2025-01-15T10:30:00Z"
          }
        ]
      }
    }
  ]
}
```

#### Get Passage Detail
```
GET /passages/<passage_id>/
Authorization: Bearer <token> (required for premium)

Response (200):
{
  "id": "uuid",
  "title": "The Science of Sleep",
  "content": "Sleep is essential for human health...\n\n[Line 5] Research shows...",
  "difficulty": "Medium",
  "tier": "free",
  "questions": [
    {
      "id": "uuid",
      "text": "What is the main idea of the passage?",
      "options": ["A. Sleep is optional", "B. Sleep is essential", ...],
      "correct_answer_index": 1,
      "explanation": "The passage states...",
      "order": 0
    }
  ],
  "annotations": [
    {
      "id": "uuid",
      "question_id": "uuid",
      "start_char": 45,
      "end_char": 89,
      "selected_text": "essential for human health",
      "explanation": "This phrase directly supports answer B",
      "order": 0
    }
  ]
}
```

#### Get Passage Questions (without answers)
```
GET /passages/<passage_id>/questions/
Authorization: Bearer <token>

Response (200):
{
  "questions": [
    {
      "id": "uuid",
      "text": "What is the main idea?",
      "options": ["A", "B", "C", "D"],
      "explanation": null,  // Hidden until answered
      "order": 0
    }
  ]
}
```

---

## 4. Progress & Submissions

### 4.1 Submit Passage Answers
```
POST /progress/passages/<passage_id>/submit
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "answers": [
    {
      "question_id": "uuid",
      "selected_option_index": 1
    }
  ],
  "time_spent_seconds": 300
}

Response (200):
{
  "passage_id": "uuid",
  "score": 80,
  "total_questions": 5,
  "correct_count": 4,
  "is_completed": true,
  "answers": [
    {
      "question_id": "uuid",
      "selected_option_index": 1,
      "correct_answer_index": 1,
      "is_correct": true,
      "explanation": "The correct answer is B because...",
      "annotations": [
        {
          "id": "uuid",
          "start_char": 45,
          "end_char": 89,
          "selected_text": "...",
          "explanation": "..."
        }
      ]
    }
  ],
  "completed_at": "2025-01-15T10:30:00Z",
  "attempt_id": "uuid"
}
```

### 4.2 Submit Lesson Answers
```
POST /progress/lessons/<lesson_id>/submit
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "answers": [
    {
      "question_id": "uuid",
      "selected_option_index": 0
    }
  ],
  "time_spent_seconds": 120
}

Response (200):
{
  "lesson_id": "uuid",
  "score": 100,
  "total_questions": 3,
  "correct_count": 3,
  "is_completed": true,
  "is_diagnostic": false,
  "answers": [...],
  "completed_at": "...",
  "attempt_id": "uuid"
}
```

### 4.3 Get Passage Attempts History
```
GET /progress/passages/<passage_id>/attempts
Authorization: Bearer <token>

Response (200):
[
  {
    "id": "uuid",
    "passage_id": "uuid",
    "score": 80,
    "correct_count": 4,
    "total_questions": 5,
    "time_spent_seconds": 300,
    "completed_at": "2025-01-15T10:30:00Z",
    "answers": [...]
  }
]
```

### 4.4 Get Lesson Attempts History
```
GET /progress/lessons/<lesson_id>/attempts
Authorization: Bearer <token>

Response (200):
[
  {
    "id": "uuid",
    "lesson_id": "uuid",
    "score": 100,
    "correct_count": 3,
    "total_questions": 3,
    "time_spent_seconds": 120,
    "completed_at": "...",
    "answers": [...]
  }
]
```

### 4.5 Review Passage (get last attempt results)
```
GET /progress/passages/<passage_id>/review
Authorization: Bearer <token>

Response (200):
{
  "passage_id": "uuid",
  "score": 80,
  "correct_count": 4,
  "total_questions": 5,
  "answers": [
    {
      "question_id": "uuid",
      "question_text": "What is the main idea?",
      "options": ["A", "B", "C", "D"],
      "selected_option_index": 1,
      "correct_answer_index": 1,
      "is_correct": true,
      "explanation": "...",
      "annotations": [...]
    }
  ]
}
```

---

## 5. User Profile & Study Plan

### 5.1 Get User Profile
```
GET /profile
Authorization: Bearer <token>

Response (200):
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_premium": false,
    "has_active_subscription": false
  },
  "study_plan": {
    "reading": {
      "diagnostic_completed": true,
      "diagnostic_passage_id": "uuid",
      "strengths": [
        {
          "name": "Main Idea",
          "correct": 3,
          "total": 3,
          "percentage": 100
        }
      ],
      "weaknesses": [
        {
          "name": "Inference",
          "correct": 1,
          "total": 4,
          "percentage": 25
        }
      ]
    },
    "writing": {
      "diagnostic_completed": false,
      "diagnostic_lesson_id": "uuid",
      "strengths": [],
      "weaknesses": []
    },
    "math": {
      "diagnostic_completed": false,
      "diagnostic_lesson_id": "uuid",
      "strengths": [],
      "weaknesses": []
    },
    "recommended_lessons": [
      {
        "id": "uuid",
        "title": "Inference Practice",
        "lesson_type": "reading"
      }
    ]
  },
  "strengths": [...],  // Aggregated across all categories
  "weaknesses": [...]  // Aggregated across all categories
}
```

### 5.2 Submit Diagnostic Test
After completing a diagnostic lesson/passage, the backend automatically updates the study plan. The normal submit endpoints handle this when `is_diagnostic: true` on the content.

---

## 6. Payments (Stripe)

### 6.1 Create Checkout Session
```
POST /payments/checkout
Authorization: Bearer <token>

Response (200):
{
  "url": "https://checkout.stripe.com/..."
}
```
Open this URL in SFSafariViewController or ASWebAuthenticationSession.

### 6.2 Create Customer Portal Session
```
POST /payments/portal
Authorization: Bearer <token>

Response (200):
{
  "url": "https://billing.stripe.com/..."
}
```

### 6.3 Get Subscription Status
```
GET /payments/subscription
Authorization: Bearer <token>

Response (200):
{
  "has_subscription": true,
  "status": "active",
  "current_period_end": "2025-02-15T00:00:00Z"
}
```

### 6.4 Sync Subscription (force refresh from Stripe)
```
POST /payments/sync
Authorization: Bearer <token>

Response (200):
{
  "synced": true,
  "status": "active"
}
```

---

## 7. Word of the Day

```
GET /word-of-the-day

Response (200):
{
  "id": "uuid",
  "word": "Eloquent",
  "definition": "Fluent or persuasive in speaking or writing.",
  "synonyms": ["Articulate", "Fluent", "Expressive"],
  "example_sentence": "The eloquent speaker captivated the audience.",
  "date": "2025-01-15"
}
```

---

## 8. UI/UX Specifications

### 8.1 Color Scheme
```swift
// Light Mode
let bgPrimary = Color(hex: "#f5f5f5")
let bgSecondary = Color(hex: "#ffffff")
let bgTertiary = Color(hex: "#e0e0e0")
let textPrimary = Color(hex: "#000000")
let textSecondary = Color(hex: "#666666")
let borderColor = Color(hex: "#e0e0e0")
let accentColor = Color(hex: "#3498DB")
let accentHover = Color(hex: "#2980B9")

// Dark Mode
let bgPrimaryDark = Color(hex: "#1a1a1a")
let bgSecondaryDark = Color(hex: "#2d2d2d")
let bgTertiaryDark = Color(hex: "#3d3d3d")
let textPrimaryDark = Color(hex: "#ffffff")
let textSecondaryDark = Color(hex: "#b0b0b0")
let borderColorDark = Color(hex: "#404040")
let accentColorDark = Color(hex: "#5dade2")

// Brand Colors
let navy = Color(hex: "#1B2A4A")
let gold = Color(hex: "#F4C441")
let blue = Color(hex: "#3498DB")
```

### 8.2 Typography
- System font (-apple-system / SF Pro)
- Passage content: Serif font (Times New Roman / Georgia)
- Questions: Sans-serif (SF Pro)

### 8.3 App Structure

#### Tab Bar (Main Navigation)
1. **Home** - Landing/category selection
2. **Reading** - Reading lessons + passages
3. **Writing** - Writing lessons
4. **Math** - Math lessons
5. **Profile** - User profile, study plan, settings

### 8.4 Screen Flows

#### Landing Screen (Not Logged In)
- Keuvi penguin logo (large, centered)
- Tagline: "An SAT tutor in your pocket"
- Feature bullets:
  - "Lessons covering everything on the test"
  - "Hundreds of practice questions"
  - "All of it written by people"
- "Get Started" button → Shows category tabs
- Premium upsell: "Sign up for premium... $5/month"

#### Category List Screen (Reading/Writing/Math)
- Section headers (grouped by `header`)
- Lesson/Passage cards showing:
  - Title
  - Premium badge (🔒) if applicable
  - Attempt count (if logged in)
  - Attempt summary (best score, latest score)
- Pull-to-refresh
- For non-logged-in users: Show only intro lessons + CTA banner

#### Lesson Detail Screen
- Back button
- Title
- Content blocks (render based on type):
  - `text` → Paragraph
  - `example` → Styled example box (light blue bg)
  - `rule` → Rule box (light yellow bg)
  - `diagram` → Image from S3 URL
  - `correct_example` → Green-tinted box
  - `incorrect_example` → Red-tinted box
- Questions (if any):
  - Question text
  - Options A, B, C, D
  - Select option → Show correct/incorrect + explanation
- Submit button (if has questions)
- Results summary after submission

#### Passage Detail Screen
- Back button
- Passage title
- Passage content (with line numbers if present)
- Questions section:
  - Question cards with options
  - Radio button selection
- Submit Answers button
- Results view:
  - Score display
  - Per-question results with:
    - Correct/incorrect indicator
    - User's answer
    - Correct answer
    - Explanation
    - Text annotations (highlighted in passage)

#### Profile Screen
- User email
- Subscription status (Free/Premium)
- Upgrade button (if free) / Manage Subscription (if premium)
- **Diagnostic Progress Section:**
  - Reading diagnostic status (Complete/Not started)
  - Writing diagnostic status
  - Math diagnostic status
  - "Start" buttons for incomplete diagnostics
- **Strengths Section:**
  - List of strong areas with percentages
- **Areas to Improve Section:**
  - List of weak areas with percentages
- **Recommended Lessons:**
  - Lesson chips/buttons to navigate
- Logout button

#### Login Modal
- Email input
- Password input
- Login button
- "Sign in with Google" button
- Cancel button
- Link to Register

#### Register Modal
- Email input
- Password input (min 8 chars)
- Register button
- "Sign in with Google" button
- Cancel button

### 8.5 Special UI Components

#### Question Option States
```swift
enum OptionState {
    case unselected  // Default border
    case selected    // Blue border, light blue bg
    case correct     // Green border, light green bg
    case incorrect   // Red border, light red bg
}
```

#### Premium Content Handling
- Show preview with fade overlay
- Lock icon on premium content
- "Upgrade to Premium" modal with benefits

#### Explanation Box
- Light blue background
- Left blue border (4px)
- Appears after answering

#### Annotations (Passages)
- Highlight text in passage after answering
- Tap highlight → Show annotation explanation

### 8.6 Intro Lessons (Free Access)
These lessons are accessible without login:
- Titles containing "Intro" (exact match or "Intro ")
- Titles containing "Waves" (Writing intro)
- Titles containing "Guided Tour" (Reading intro)

---

## 9. Data Models (Swift)

```swift
// MARK: - User
struct User: Codable, Identifiable {
    let id: UUID
    let email: String
    let isPremium: Bool
    let hasActiveSubscription: Bool
    
    enum CodingKeys: String, CodingKey {
        case id, email
        case isPremium = "is_premium"
        case hasActiveSubscription = "has_active_subscription"
    }
}

// MARK: - Auth
struct AuthResponse: Codable {
    let user: User
    let tokens: Tokens
}

struct Tokens: Codable {
    let access: String
    let refresh: String
}

// MARK: - Header
struct Header: Codable, Identifiable {
    let id: UUID
    let title: String
    let category: String
    let displayOrder: Int
    
    enum CodingKeys: String, CodingKey {
        case id, title, category
        case displayOrder = "display_order"
    }
}

// MARK: - Lesson
struct LessonListItem: Codable, Identifiable {
    let id: UUID
    let title: String
    let lessonType: String
    let tier: String
    let isDiagnostic: Bool
    let header: Header?
    let orderWithinHeader: Int
    let questionCount: Int
    let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, title, tier, header
        case lessonType = "lesson_type"
        case isDiagnostic = "is_diagnostic"
        case orderWithinHeader = "order_within_header"
        case questionCount = "question_count"
        case createdAt = "created_at"
    }
}

struct LessonDetail: Codable, Identifiable {
    let id: UUID
    let title: String
    let content: [ContentBlock]
    let lessonType: String
    let tier: String
    let isDiagnostic: Bool
    let questions: [LessonQuestion]
    let assets: [LessonAsset]
    
    enum CodingKeys: String, CodingKey {
        case id, title, content, questions, assets, tier
        case lessonType = "lesson_type"
        case isDiagnostic = "is_diagnostic"
    }
}

struct ContentBlock: Codable {
    let type: String  // "paragraph", "text", "example", "diagram", "rule", "side_by_side"
    let content: String?
    let diagramId: String?
    let left: String?      // For side_by_side blocks
    let right: String?     // For side_by_side blocks
    
    enum CodingKeys: String, CodingKey {
        case type, content, left, right
        case diagramId = "diagram_id"
    }
}

struct LessonAsset: Codable, Identifiable {
    let id: UUID
    let assetId: String
    let type: String
    let s3Url: String
    
    enum CodingKeys: String, CodingKey {
        case id, type
        case assetId = "asset_id"
        case s3Url = "s3_url"
    }
}

struct LessonQuestion: Codable, Identifiable {
    let id: UUID
    let text: [ContentBlock]  // Can be array of blocks
    let options: [QuestionOption]
    let correctAnswerIndex: Int
    let explanation: [ContentBlock]?  // Can be array of blocks
    let order: Int
    let chunkIndex: Int?
    let assets: [LessonAsset]
    
    enum CodingKeys: String, CodingKey {
        case id, text, options, explanation, order, assets
        case correctAnswerIndex = "correct_answer_index"
        case chunkIndex = "chunk_index"
    }
}

// MARK: - Passage
struct PassageListItem: Codable, Identifiable {
    let id: UUID
    let title: String
    let content: String
    let difficulty: String
    let tier: String
    let isDiagnostic: Bool
    let header: Header?
    let orderWithinHeader: Int
    let questionCount: Int
    let attemptCount: Int
    let attemptSummary: AttemptSummary?
    
    enum CodingKeys: String, CodingKey {
        case id, title, content, difficulty, tier, header
        case isDiagnostic = "is_diagnostic"
        case orderWithinHeader = "order_within_header"
        case questionCount = "question_count"
        case attemptCount = "attempt_count"
        case attemptSummary = "attempt_summary"
    }
}

struct AttemptSummary: Codable {
    let totalAttempts: Int
    let bestScore: Int?
    let latestScore: Int?
    let recentAttempts: [RecentAttempt]
    
    enum CodingKeys: String, CodingKey {
        case totalAttempts = "total_attempts"
        case bestScore = "best_score"
        case latestScore = "latest_score"
        case recentAttempts = "recent_attempts"
    }
}

struct RecentAttempt: Codable, Identifiable {
    let id: UUID
    let score: Int
    let correctCount: Int
    let totalQuestions: Int
    let completedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, score
        case correctCount = "correct_count"
        case totalQuestions = "total_questions"
        case completedAt = "completed_at"
    }
}

struct PassageDetail: Codable, Identifiable {
    let id: UUID
    let title: String
    let content: String
    let difficulty: String
    let tier: String
    let questions: [PassageQuestion]
    let annotations: [PassageAnnotation]
}

struct PassageQuestion: Codable, Identifiable {
    let id: UUID
    let text: String
    let options: [String]  // Simple string array
    let correctAnswerIndex: Int
    let explanation: String?
    let order: Int
    
    enum CodingKeys: String, CodingKey {
        case id, text, options, explanation, order
        case correctAnswerIndex = "correct_answer_index"
    }
}

struct PassageAnnotation: Codable, Identifiable {
    let id: UUID
    let questionId: UUID?
    let startChar: Int
    let endChar: Int
    let selectedText: String
    let explanation: String
    let order: Int
    
    enum CodingKeys: String, CodingKey {
        case id, explanation, order
        case questionId = "question_id"
        case startChar = "start_char"
        case endChar = "end_char"
        case selectedText = "selected_text"
    }
}

// MARK: - Question Option
struct QuestionOption: Codable, Identifiable {
    let id: UUID
    let text: String
    let order: Int
}

// MARK: - Submission
struct SubmitAnswer: Codable {
    let questionId: UUID
    let selectedOptionIndex: Int
    
    enum CodingKeys: String, CodingKey {
        case questionId = "question_id"
        case selectedOptionIndex = "selected_option_index"
    }
}

struct SubmitRequest: Codable {
    let answers: [SubmitAnswer]
    let timeSpentSeconds: Int?
    
    enum CodingKeys: String, CodingKey {
        case answers
        case timeSpentSeconds = "time_spent_seconds"
    }
}

struct SubmitResponse: Codable {
    let passageId: UUID?
    let lessonId: UUID?
    let score: Int
    let totalQuestions: Int
    let correctCount: Int
    let isCompleted: Bool
    let isDiagnostic: Bool?
    let answers: [AnswerResult]
    let completedAt: Date
    let attemptId: UUID?
    
    enum CodingKeys: String, CodingKey {
        case score, answers
        case passageId = "passage_id"
        case lessonId = "lesson_id"
        case totalQuestions = "total_questions"
        case correctCount = "correct_count"
        case isCompleted = "is_completed"
        case isDiagnostic = "is_diagnostic"
        case completedAt = "completed_at"
        case attemptId = "attempt_id"
    }
}

struct AnswerResult: Codable {
    let questionId: UUID
    let selectedOptionIndex: Int
    let correctAnswerIndex: Int
    let isCorrect: Bool
    let explanation: String?
    let annotations: [PassageAnnotation]?
    
    enum CodingKeys: String, CodingKey {
        case explanation, annotations
        case questionId = "question_id"
        case selectedOptionIndex = "selected_option_index"
        case correctAnswerIndex = "correct_answer_index"
        case isCorrect = "is_correct"
    }
}

// MARK: - Study Plan
struct ProfileResponse: Codable {
    let user: User
    let studyPlan: StudyPlan?
    let strengths: [SkillPerformance]
    let weaknesses: [SkillPerformance]
    
    enum CodingKeys: String, CodingKey {
        case user, strengths, weaknesses
        case studyPlan = "study_plan"
    }
}

struct StudyPlan: Codable {
    let reading: CategoryPlan?
    let writing: CategoryPlan?
    let math: CategoryPlan?
    let recommendedLessons: [RecommendedLesson]?
    
    enum CodingKeys: String, CodingKey {
        case reading, writing, math
        case recommendedLessons = "recommended_lessons"
    }
}

struct CategoryPlan: Codable {
    let diagnosticCompleted: Bool
    let diagnosticPassageId: UUID?  // For reading
    let diagnosticLessonId: UUID?   // For writing/math
    let strengths: [SkillPerformance]
    let weaknesses: [SkillPerformance]
    
    enum CodingKeys: String, CodingKey {
        case strengths, weaknesses
        case diagnosticCompleted = "diagnostic_completed"
        case diagnosticPassageId = "diagnostic_passage_id"
        case diagnosticLessonId = "diagnostic_lesson_id"
    }
}

struct SkillPerformance: Codable, Identifiable {
    var id: String { name }
    let name: String
    let correct: Int
    let total: Int
    let percentage: Int
    var category: String?
}

struct RecommendedLesson: Codable, Identifiable {
    let id: UUID
    let title: String
    let lessonType: String
    
    enum CodingKeys: String, CodingKey {
        case id, title
        case lessonType = "lesson_type"
    }
}

// MARK: - Word of the Day
struct WordOfTheDay: Codable, Identifiable {
    let id: UUID
    let word: String
    let definition: String
    let synonyms: [String]
    let exampleSentence: String
    let date: String
    
    enum CodingKeys: String, CodingKey {
        case id, word, definition, synonyms, date
        case exampleSentence = "example_sentence"
    }
}
```

---

## 10. API Service Layer

```swift
class APIService {
    static let shared = APIService()
    
    // MARK: - Environment Configuration
    enum Environment {
        case production
        case development
        case localDevice(ip: String)
        
        var baseURL: String {
            switch self {
            case .production:
                return "https://keuvi.app/api/v1"
            case .development:
                return "http://localhost:8000/api/v1"
            case .localDevice(let ip):
                return "http://\(ip):8000/api/v1"
            }
        }
    }
    
    // Change this for testing
    #if DEBUG
    private let environment: Environment = .development
    #else
    private let environment: Environment = .production
    #endif
    
    private var baseURL: String { environment.baseURL }
    
    private var accessToken: String? {
        KeychainHelper.shared.read(key: "accessToken")
    }
    
    // MARK: - Generic Request
    func request<T: Decodable>(
        endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        requiresAuth: Bool = false
    ) async throws -> T {
        // Build URL, headers, body
        // Handle 401 → refresh token
        // Decode response
    }
    
    // MARK: - Auth
    func login(email: String, password: String) async throws -> AuthResponse
    func register(email: String, password: String) async throws -> AuthResponse
    func refreshToken() async throws -> String
    func getCurrentUser() async throws -> User
    
    // MARK: - Content
    func getLessons(type: String) async throws -> [LessonListItem]
    func getLessonDetail(id: UUID) async throws -> LessonDetail
    func getPassages() async throws -> [PassageListItem]
    func getPassageDetail(id: UUID) async throws -> PassageDetail
    
    // MARK: - Progress
    func submitPassage(id: UUID, answers: [SubmitAnswer], timeSpent: Int?) async throws -> SubmitResponse
    func submitLesson(id: UUID, answers: [SubmitAnswer], timeSpent: Int?) async throws -> SubmitResponse
    func getPassageAttempts(id: UUID) async throws -> [Attempt]
    func getLessonAttempts(id: UUID) async throws -> [Attempt]
    
    // MARK: - Profile
    func getProfile() async throws -> ProfileResponse
    
    // MARK: - Payments
    func createCheckoutSession() async throws -> URL
    func createPortalSession() async throws -> URL
    
    // MARK: - Word of the Day
    func getWordOfTheDay() async throws -> WordOfTheDay
}
```

---

## 11. State Management

Use `@Observable` (iOS 17+) or `ObservableObject` for:

```swift
@Observable
class AuthManager {
    var isLoggedIn: Bool = false
    var currentUser: User?
    var isLoading: Bool = false
    
    func login(email: String, password: String) async
    func register(email: String, password: String) async
    func logout()
    func checkAuthStatus() async
}

@Observable
class ContentManager {
    var readingLessons: [LessonListItem] = []
    var writingLessons: [LessonListItem] = []
    var mathLessons: [LessonListItem] = []
    var passages: [PassageListItem] = []
    var isLoading: Bool = false
    
    func loadLessons(type: String) async
    func loadPassages() async
}

@Observable
class ProfileManager {
    var profile: ProfileResponse?
    var isLoading: Bool = false
    
    func loadProfile() async
}
```

---

## 12. Key Implementation Notes

### 12.1 Content Rendering

Lesson content uses structured JSON blocks. The `text` and `explanation` fields on `LessonQuestion` are **arrays of ContentBlock objects**, not plain strings.

#### Block Types
| Type | Description | Content Field |
|------|-------------|---------------|
| `paragraph` | Regular paragraph text | `content: String` |
| `text` | Plain text block | `content: String` |
| `example` | Example text (styled differently) | `content: String` |
| `rule` | Grammar/math rule | `content: String` |
| `diagram` | Diagram placeholder | `diagram_id: String` (resolve from assets) |
| `side_by_side` | Two columns | `left: String`, `right: String` |

#### Swift Helper: Convert Blocks to Display String

```swift
extension LessonQuestion {
    /// Extracts plain text from question blocks for display
    var displayText: String {
        return text.compactMap { block -> String? in
            switch block.type {
            case "paragraph", "text", "example", "rule":
                return block.content
            case "side_by_side":
                // Combine left and right
                let left = block.left ?? ""
                let right = block.right ?? ""
                return "\(left) | \(right)"
            case "diagram":
                return nil  // Handle separately with image
            default:
                return block.content
            }
        }.joined(separator: "\n\n")
    }
    
    /// Checks if question has any displayable text
    var hasDisplayText: Bool {
        return !displayText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
    
    /// Get diagram asset IDs for this question
    var diagramIds: [String] {
        return text.compactMap { block in
            block.type == "diagram" ? block.diagramId : nil
        }
    }
}
```

#### Updated ContentBlock Model

```swift
struct ContentBlock: Codable {
    let type: String  // "paragraph", "text", "example", "diagram", "rule", "side_by_side"
    let content: String?
    let diagramId: String?
    let left: String?      // For side_by_side blocks
    let right: String?     // For side_by_side blocks
    
    enum CodingKeys: String, CodingKey {
        case type, content, left, right
        case diagramId = "diagram_id"
    }
}
```

#### Rendering Diagrams

```swift
func renderDiagram(diagramId: String, from assets: [LessonAsset]) -> some View {
    if let asset = assets.first(where: { $0.assetId == diagramId }) {
        AsyncImage(url: URL(string: asset.s3Url)) { image in
            image.resizable().aspectRatio(contentMode: .fit)
        } placeholder: {
            ProgressView()
        }
    } else {
        Text("[Diagram not found: \(diagramId)]")
    }
}
```

#### Sentinel Replacements
- Diagrams: Replace `[[Diagram:diagram-id]]` sentinels in text with actual images from assets array
- Underlines: Replace `[[u]]text[[/u]]` with underlined text using AttributedString

```swift
func replaceUnderlines(in text: String) -> AttributedString {
    var result = AttributedString(text)
    let pattern = #"\[\[u\]\](.*?)\[\[/u\]\]"#
    
    // Use regex to find and style underlined text
    guard let regex = try? NSRegularExpression(pattern: pattern) else { return result }
    let nsString = text as NSString
    let matches = regex.matches(in: text, range: NSRange(location: 0, length: nsString.length))
    
    // Process matches in reverse to preserve indices
    for match in matches.reversed() {
        if let range = Range(match.range, in: text),
           let contentRange = Range(match.range(at: 1), in: text) {
            let content = String(text[contentRange])
            var underlined = AttributedString(content)
            underlined.underlineStyle = .single
            if let attrRange = result.range(of: String(text[range])) {
                result.replaceSubrange(attrRange, with: underlined)
            }
        }
    }
    return result
}
```

### 12.2 Question Text Handling

**IMPORTANT**: `LessonQuestion.text` is always an **array of ContentBlock objects**, never a plain string.

If your app logs `Question text: '' (empty: true)`, you're trying to use the array as a string. Use the `displayText` computed property above.

| Content Type | `text` field type | Handling |
|--------------|-------------------|----------|
| `LessonQuestion` | `[ContentBlock]` (JSON array) | Use `displayText` helper |
| `PassageQuestion` | `String` | Direct display |
| `WritingSectionQuestion` | `String` | Direct display |
| `MathQuestion` | `String` | Direct display |

**Example API Response for LessonQuestion:**
```json
{
  "id": "8DC82306-A36D-4781-8D8C-825105B5472D",
  "text": [
    {"type": "paragraph", "content": "What is 2 + 2?"}
  ],
  "options": [
    {"id": "...", "text": "3", "order": 0},
    {"id": "...", "text": "4", "order": 1}
  ],
  "correct_answer_index": 1,
  "explanation": [
    {"type": "paragraph", "content": "2 + 2 = 4 by basic arithmetic."}
  ]
}
```

### 12.3 Pagination
- API returns paginated results with `count`, `next`, `previous`, `results`
- Implement infinite scroll or "Load More" for large lists

### 12.4 Offline Support (Optional)
- Cache lessons/passages in Core Data or Realm
- Queue submissions when offline
- Sync when back online

### 12.5 Error Handling
- Show user-friendly error messages
- Handle network errors gracefully
- Implement retry logic for transient failures

### 12.6 Dark Mode
- Support system appearance
- Use semantic colors from Color Scheme section
- Store user preference if manual toggle desired

---

## 13. Testing Checklist

- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] Google OAuth flow works
- [ ] Token refresh works when access token expires
- [ ] Reading lessons load and display correctly
- [ ] Writing lessons load and display correctly
- [ ] Math lessons load and display correctly
- [ ] Passages load and display correctly
- [ ] Questions can be answered
- [ ] Submission saves and shows results
- [ ] Explanations appear after answering
- [ ] Annotations highlight in passage text
- [ ] Attempt history displays correctly
- [ ] Profile shows study plan data
- [ ] Diagnostic tests update study plan
- [ ] Premium content is gated correctly
- [ ] Stripe checkout flow works
- [ ] Word of the Day displays
- [ ] Dark mode works correctly
- [ ] Intro lessons accessible without login

---

## 14. App Store Requirements

- Privacy Policy URL (required)
- Terms of Service URL (required)
- Support email: admin@argosventures.pro
- App icon (penguin mascot)
- Screenshots for all device sizes
- App description highlighting SAT prep features
