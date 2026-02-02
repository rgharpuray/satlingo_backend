# Penguin Onboarding Research - Keuvi SAT Prep App

**Prepared**: 2026-02-02
**Phase**: PREPARE (PACT Framework)
**Status**: Complete

---

## Executive Summary

Research findings on the current state of the Keuvi codebase across backend, iOS, and Android platforms to inform the design of a guided penguin onboarding experience.

**Key Findings**:
1. The backend has a robust `StudyPlan` model that tracks diagnostic completion - ideal hook for onboarding state
2. The penguin mascot already exists in the web UI with context-aware messaging based on quiz scores
3. No formal onboarding state machine exists - opportunity to build a rule-based guidance system
4. The user journey from first login to profile creation to diagnostic test is well-defined in the API but lacks explicit guided prompts

**Recommendation**: Extend `StudyPlan` with onboarding milestone fields, enabling rule-based penguin prompts without requiring LLM inference.

---

## 1. Backend Analysis

### 1.1 User Model and Authentication

**Location**: `/api/models.py`

- `User` extends Django's `AbstractUser` with UUID, email, premium status
- OAuth support: Google (`google_id`) and Apple (`apple_id`)
- No existing "onboarding_completed" or "first_run" flags

**Auth Endpoints** (`/api/auth_views.py`):
- `POST /auth/register` - Email/password registration
- `POST /auth/login` - Email/password login
- `POST /auth/google/token` - Google OAuth
- `POST /auth/apple/token` - Apple Sign In
- `GET /auth/me` - Get current user
- `DELETE /auth/delete-account` - Account deletion

### 1.2 StudyPlan Model - Primary Hook for Onboarding

**Location**: `/api/models.py` (lines 1160-1241)

```python
class StudyPlan(models.Model):
    user = models.OneToOneField(User, ...)

    # Performance data by classification (JSON)
    reading_performance = models.JSONField(default=dict)
    writing_performance = models.JSONField(default=dict)
    math_performance = models.JSONField(default=dict)

    # Diagnostic completion flags - IDEAL FOR ONBOARDING
    reading_diagnostic_completed = models.BooleanField(default=False)
    writing_diagnostic_completed = models.BooleanField(default=False)
    math_diagnostic_completed = models.BooleanField(default=False)
```

**Methods**: `get_strengths()`, `get_weaknesses()`, `get_improving()`

### 1.3 Diagnostic Flow

**Location**: `/api/views.py` (lines 1828-1987)

- Reading diagnostic uses Passage model
- Writing/Math diagnostics use Lesson model
- `POST /diagnostic/submit` calculates performance by QuestionClassification
- Updates StudyPlan with results and recommendations

### 1.4 Profile Endpoint

`GET /api/v1/profile` returns:
- User info (id, email, is_premium)
- Performance data by classification
- Study plan with diagnostic status for each category

---

## 2. Existing Penguin Implementation

### 2.1 Web Template - Penguin Messages

**Location**: `/templates/web/index.html`

```javascript
function getPenguinMessage(score, totalQuestions, isPractice = false) {
    const percentage = Math.round((score / totalQuestions) * 100);

    // Perfect score (practice)
    if (isPractice && score === totalQuestions) {
        return ["Perfectamundo!", "Perfect! We'll find harder ones next time."];
    }

    // 70%+
    if (percentage >= 70) {
        return ["Good stuff!", "Nice, nice.", "Very cool."];
    }

    // Below 70%
    return ["The hardest work is the most important work",
            "The only way through it is through it.",
            "Getting there."];
}
```

### 2.2 Penguin Personality (from project docs)

> "Keuvi doesn't feel like studying. It feels like a calm, slightly sarcastic tutor who's always on your side."

- Coach - guides learning
- Navigator - helps find content
- Motivator - encourages progress
- Friction remover - makes studying feel easy

---

## 3. Current User Journey Gaps

### First Open to Profile Creation
- **Gap**: No welcome screen or guided introduction

### Profile Creation to Diagnostic
- **Gap**: No guidance on WHY or WHEN to take diagnostics

### Post-Diagnostic
- **Gap**: No progressive disclosure or milestone celebrations

---

## 4. Recommendations for Architecture Phase

### 4.1 Extend StudyPlan Model

```python
# Add to StudyPlan
onboarding_completed = models.BooleanField(default=False)
has_seen_welcome = models.BooleanField(default=False)
first_practice_completed_at = models.DateTimeField(null=True)
last_prompt_dismissed = models.CharField(max_length=50, null=True)
```

### 4.2 Rule-Based Prompt Engine (No LLM)

State machine:
```
WELCOME → PROFILE_SETUP → DIAGNOSTIC_NUDGE →
DIAGNOSTIC_IN_PROGRESS → POST_DIAGNOSTIC → ENGAGED
```

### 4.3 New API Endpoint

`GET /api/v1/onboarding/status` returns:
```json
{
  "current_prompt": {
    "id": "diagnostic_nudge",
    "message": "First things first: let's see what you're good at and what you need to practice",
    "action": "start_diagnostic",
    "dismissible": true
  },
  "milestones": {
    "welcome_seen": true,
    "profile_complete": true,
    "first_diagnostic": false,
    "first_practice": false
  }
}
```

### 4.4 Mobile Components Needed

1. **PenguinCoach Component**: Avatar + speech bubble, dismissible
2. **Welcome Screen**: First launch intro (3-4 screens, skippable)
3. **Contextual Prompts**: Overlay system for guidance

---

## 5. Suggested Penguin Messages

**Welcome**:
- "Hey! I'm the Keuvi penguin. Let's get you ready for the SAT."

**Profile Nudge**:
- "Let's get started by making a profile, so we can track your performance and make your personalized study plan."

**Diagnostic Nudge**:
- "First things first: let's see what you're good at and what you need to practice."

**Post-Diagnostic**:
- "Nice work! I found some areas we can work on together."

**Return Visit**:
- "Good to see you again! Ready to pick up where we left off?"

---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `/api/models.py` | User, StudyPlan, Attempt models |
| `/api/views.py` | Profile, Diagnostic endpoints |
| `/api/auth_views.py` | Authentication endpoints |
| `/templates/web/index.html` | Web app with penguin messages |
| `/IOS_APP_SPEC.md` | iOS implementation guide |
| `/ANDROID_APP_SPEC.md` | Android implementation guide |
