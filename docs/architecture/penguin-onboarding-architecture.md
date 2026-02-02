# Penguin-Guided Onboarding Architecture

**Version**: 1.0
**Phase**: ARCHITECT (PACT Framework)
**Date**: 2026-02-02
**Status**: Ready for Implementation

---

## Executive Summary

This document defines the architecture for a penguin-guided onboarding system in the Keuvi SAT prep app. The system uses rule-based logic (no LLM calls) to guide users through key milestones from first app open through completing their first diagnostic test.

**Key Design Decisions**:
1. Extend existing `StudyPlan` model with onboarding fields (no new tables)
2. Extend existing `/profile` endpoint with onboarding data (minimal API surface)
3. Finite state machine for onboarding transitions
4. Backend as source of truth; clients cache state locally
5. All prompts dismissible with persistence

---

## 1. System Context

```
+------------------+     +-----------------+     +------------------+
|                  |     |                 |     |                  |
|   iOS App        |<--->|   Backend API   |<--->|   PostgreSQL     |
|   (SwiftUI)      |     |   (Django)      |     |   (StudyPlan)    |
|                  |     |                 |     |                  |
+------------------+     +-----------------+     +------------------+
        ^                        ^
        |                        |
        v                        v
+------------------+     +-----------------+
|                  |     |                 |
|   Android App    |     |   Web App       |
|   (Compose)      |     |   (React)       |
|                  |     |                 |
+------------------+     +-----------------+
```

**Data Flow**:
1. Client requests `/profile` on app launch
2. Backend evaluates onboarding state and returns current prompt
3. Client displays penguin prompt (if any)
4. User takes action or dismisses
5. Client reports action via existing endpoints or new `/onboarding/dismiss`
6. Backend updates state, returns updated onboarding data

---

## 2. Data Model Changes

### 2.1 Extend StudyPlan Model

Add these fields to the existing `StudyPlan` model:

```python
# New fields on StudyPlan model
onboarding_state = models.CharField(
    max_length=30,
    default='WELCOME',
    choices=[
        ('WELCOME', 'Welcome'),
        ('PROFILE_SETUP', 'Profile Setup'),
        ('DIAGNOSTIC_NUDGE', 'Diagnostic Nudge'),
        ('DIAGNOSTIC_IN_PROGRESS', 'Diagnostic In Progress'),
        ('POST_DIAGNOSTIC', 'Post Diagnostic'),
        ('ENGAGED', 'Engaged'),
    ],
    help_text="Current onboarding state"
)

# Track what prompts user has seen/dismissed
welcome_seen_at = models.DateTimeField(null=True, blank=True)
profile_prompt_dismissed_at = models.DateTimeField(null=True, blank=True)
diagnostic_prompt_dismissed_at = models.DateTimeField(null=True, blank=True)
post_diagnostic_seen_at = models.DateTimeField(null=True, blank=True)

# Track first practice for "engaged" state
first_practice_completed_at = models.DateTimeField(null=True, blank=True)

# Quick access flags (computed from above but stored for performance)
onboarding_completed = models.BooleanField(default=False)
```

**Migration Strategy**:
- Add fields with `null=True` defaults initially
- Set `onboarding_state='ENGAGED'` for existing users who have completed diagnostics
- Set `onboarding_completed=True` for existing users with any diagnostic completed

### 2.2 Entity Relationship

```
+------------------+
|      User        |
+------------------+
| id (UUID)        |
| email            |
| is_premium       |
+------------------+
        |
        | 1:1
        v
+----------------------+
|     StudyPlan        |
+----------------------+
| id (UUID)            |
| user_id (FK)         |
|----------------------|
| # Existing fields    |
| reading_performance  |
| writing_performance  |
| math_performance     |
| reading_diagnostic_  |
|   completed          |
| writing_diagnostic_  |
|   completed          |
| math_diagnostic_     |
|   completed          |
|----------------------|
| # NEW: Onboarding    |
| onboarding_state     |
| welcome_seen_at      |
| profile_prompt_      |
|   dismissed_at       |
| diagnostic_prompt_   |
|   dismissed_at       |
| post_diagnostic_     |
|   seen_at            |
| first_practice_      |
|   completed_at       |
| onboarding_completed |
+----------------------+
```

---

## 3. Onboarding State Machine

### 3.1 States

| State | Description | Entry Condition |
|-------|-------------|-----------------|
| `WELCOME` | Initial state for new users | Account created |
| `PROFILE_SETUP` | User saw welcome, needs profile | `welcome_seen_at` is set |
| `DIAGNOSTIC_NUDGE` | Profile complete, needs diagnostic | User has profile, no diagnostic started |
| `DIAGNOSTIC_IN_PROGRESS` | User started a diagnostic | Diagnostic attempt exists (not completed) |
| `POST_DIAGNOSTIC` | First diagnostic completed | Any diagnostic completed flag is true |
| `ENGAGED` | User is active | First practice OR all dismissed OR 7 days |

### 3.2 State Transition Diagram

```
                    +----------+
                    | WELCOME  |
                    +----+-----+
                         |
                         | User sees welcome / dismisses
                         v
                 +---------------+
                 | PROFILE_SETUP |<--+
                 +-------+-------+   |
                         |           | (Profile incomplete
                         |           |  after dismiss)
                         | Profile   |
                         | complete  |
                         v           |
               +-----------------+   |
            +->| DIAGNOSTIC_NUDGE|---+
            |  +--------+--------+
            |           |
            |           | User starts diagnostic
            |           v
            |  +---------------------+
            |  | DIAGNOSTIC_IN_      |
            |  | PROGRESS            |
            |  +---------+-----------+
            |            |
            |            | Diagnostic submitted
   User     |            v
   exits    |  +-----------------+
   early    +--| POST_DIAGNOSTIC |
               +--------+--------+
                        |
                        | User starts practice OR
                        | dismisses OR 7 days
                        v
                  +-----------+
                  |  ENGAGED  |
                  +-----------+
```

### 3.3 Transition Rules (Rule Engine)

```python
def compute_onboarding_state(study_plan: StudyPlan) -> str:
    """
    Rule-based state computation. No LLM calls.
    Called on profile endpoint or after relevant actions.
    """
    from django.utils import timezone
    from datetime import timedelta

    # Rule 1: Already marked engaged
    if study_plan.onboarding_completed:
        return 'ENGAGED'

    # Rule 2: Any diagnostic completed -> POST_DIAGNOSTIC or ENGAGED
    has_diagnostic = (
        study_plan.reading_diagnostic_completed or
        study_plan.writing_diagnostic_completed or
        study_plan.math_diagnostic_completed
    )

    if has_diagnostic:
        # Check if user has done first practice
        if study_plan.first_practice_completed_at:
            return 'ENGAGED'
        # Check if 7 days since post-diagnostic shown
        if study_plan.post_diagnostic_seen_at:
            if timezone.now() - study_plan.post_diagnostic_seen_at > timedelta(days=7):
                return 'ENGAGED'
        return 'POST_DIAGNOSTIC'

    # Rule 3: Diagnostic in progress (started but not completed)
    # Check for unfinished diagnostic attempts
    if has_diagnostic_in_progress(study_plan.user):
        return 'DIAGNOSTIC_IN_PROGRESS'

    # Rule 4: Welcome seen but no diagnostic started
    if study_plan.welcome_seen_at:
        # Profile is always "complete" after auth for now
        # Could add profile fields check here if needed
        return 'DIAGNOSTIC_NUDGE'

    # Rule 5: Fresh user
    return 'WELCOME'


def has_diagnostic_in_progress(user) -> bool:
    """Check if user has started but not completed a diagnostic."""
    # This is a placeholder - actual implementation depends on
    # how we track "started" state (could use session or partial attempt)
    return False  # Conservative default
```

---

## 4. API Contract

### 4.1 Extended Profile Response

**Endpoint**: `GET /api/v1/profile`

The existing profile endpoint is extended with an `onboarding` object:

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_premium": false
  },
  "performance": [...],
  "strengths": [...],
  "weaknesses": [...],
  "study_plan": {...},

  "onboarding": {
    "state": "DIAGNOSTIC_NUDGE",
    "prompt": {
      "id": "diagnostic_nudge",
      "message": "First things first: let's see what you're good at.",
      "secondary_message": "It takes about 15 minutes and helps me build your study plan.",
      "action": {
        "type": "navigate",
        "target": "diagnostic_selection",
        "label": "Start Diagnostic"
      },
      "dismissible": true
    },
    "milestones": {
      "welcome_seen": true,
      "profile_complete": true,
      "first_diagnostic_completed": false,
      "first_practice_completed": false,
      "onboarding_completed": false
    },
    "diagnostic_status": {
      "reading": {"available": true, "completed": false},
      "writing": {"available": true, "completed": false},
      "math": {"available": true, "completed": false}
    }
  }
}
```

### 4.2 Dismiss Endpoint

**Endpoint**: `POST /api/v1/onboarding/dismiss`

```json
// Request
{
  "prompt_id": "diagnostic_nudge"
}

// Response
{
  "success": true,
  "onboarding": {
    "state": "DIAGNOSTIC_NUDGE",
    "prompt": null,
    "milestones": {...}
  }
}
```

**Valid prompt_ids**: `welcome`, `profile_setup`, `diagnostic_nudge`, `post_diagnostic`

### 4.3 Mark Welcome Seen

**Endpoint**: `POST /api/v1/onboarding/welcome-seen`

```json
// Request
{}

// Response
{
  "success": true,
  "onboarding": {
    "state": "DIAGNOSTIC_NUDGE",
    "prompt": {...}
  }
}
```

---

## 5. Message Catalog

### 5.1 Prompt Definitions

| ID | State | Message | Secondary | Action | Dismissible |
|----|-------|---------|-----------|--------|-------------|
| `welcome` | WELCOME | "Hey! I'm the Keuvi penguin. Let's get you ready for the SAT." | "I'll help you find what to practice and track your progress." | { type: "continue", label: "Let's go" } | false |
| `profile_setup` | PROFILE_SETUP | "Let's set up your profile so I can track your progress." | null | { type: "navigate", target: "profile_edit", label: "Set Up Profile" } | true |
| `diagnostic_nudge` | DIAGNOSTIC_NUDGE | "First things first: let's see what you're good at." | "Takes about 15 minutes. I'll build your study plan from the results." | { type: "navigate", target: "diagnostic_selection", label: "Start Diagnostic" } | true |
| `diagnostic_progress` | DIAGNOSTIC_IN_PROGRESS | "You started a diagnostic. Want to finish it?" | null | { type: "navigate", target: "diagnostic_resume", label: "Continue" } | true |
| `post_diagnostic` | POST_DIAGNOSTIC | "Nice work! I found some areas we can work on together." | "Ready to start practicing?" | { type: "navigate", target: "practice", label: "Start Practice" } | true |

### 5.2 Prompt Selection Logic

```python
PROMPTS = {
    'WELCOME': {
        'id': 'welcome',
        'message': "Hey! I'm the Keuvi penguin. Let's get you ready for the SAT.",
        'secondary_message': "I'll help you find what to practice and track your progress.",
        'action': {'type': 'continue', 'label': "Let's go"},
        'dismissible': False,
    },
    'PROFILE_SETUP': {
        'id': 'profile_setup',
        'message': "Let's set up your profile so I can track your progress.",
        'secondary_message': None,
        'action': {'type': 'navigate', 'target': 'profile_edit', 'label': 'Set Up Profile'},
        'dismissible': True,
    },
    'DIAGNOSTIC_NUDGE': {
        'id': 'diagnostic_nudge',
        'message': "First things first: let's see what you're good at.",
        'secondary_message': "Takes about 15 minutes. I'll build your study plan from the results.",
        'action': {'type': 'navigate', 'target': 'diagnostic_selection', 'label': 'Start Diagnostic'},
        'dismissible': True,
    },
    'DIAGNOSTIC_IN_PROGRESS': {
        'id': 'diagnostic_progress',
        'message': "You started a diagnostic. Want to finish it?",
        'secondary_message': None,
        'action': {'type': 'navigate', 'target': 'diagnostic_resume', 'label': 'Continue'},
        'dismissible': True,
    },
    'POST_DIAGNOSTIC': {
        'id': 'post_diagnostic',
        'message': "Nice work! I found some areas we can work on together.",
        'secondary_message': "Ready to start practicing?",
        'action': {'type': 'navigate', 'target': 'practice', 'label': 'Start Practice'},
        'dismissible': True,
    },
    'ENGAGED': None,  # No prompt for engaged users
}

def get_current_prompt(study_plan: StudyPlan) -> dict | None:
    """Get the current prompt based on state and dismissal status."""
    state = study_plan.onboarding_state
    prompt_def = PROMPTS.get(state)

    if not prompt_def:
        return None

    # Check if this prompt was dismissed
    prompt_id = prompt_def['id']
    dismissed_field = f"{prompt_id.replace('_', '_prompt_')}_dismissed_at"

    if hasattr(study_plan, dismissed_field):
        if getattr(study_plan, dismissed_field):
            return None  # Prompt was dismissed

    return prompt_def
```

---

## 6. Mobile Component Specifications

### 6.1 Shared Component: PenguinCoach

A reusable component displaying the penguin avatar with a speech bubble.

```
+------------------------------------------+
|  +------+                                |
|  |      |  "Message text here"           |
|  | PENG |  Secondary text (optional)     |
|  | UIN  |                                |
|  |      |  [  Primary Action  ]          |
|  +------+                                |
|                              [ Dismiss ] |
+------------------------------------------+
```

**Props/Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `message` | String | Yes | Primary message text |
| `secondaryMessage` | String? | No | Optional secondary text |
| `action` | Action? | No | Primary action button |
| `dismissible` | Boolean | Yes | Show dismiss button |
| `onAction` | Callback | No | Called when action tapped |
| `onDismiss` | Callback | No | Called when dismissed |

### 6.2 iOS Implementation (SwiftUI)

```swift
// File: Keuvi/Components/PenguinCoachView.swift

struct PenguinCoachAction {
    let type: String  // "continue", "navigate"
    let target: String?
    let label: String
}

struct PenguinCoachView: View {
    let message: String
    let secondaryMessage: String?
    let action: PenguinCoachAction?
    let dismissible: Bool
    let onAction: (() -> Void)?
    let onDismiss: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Penguin avatar
            Image("penguin_avatar")
                .resizable()
                .frame(width: 60, height: 60)

            VStack(alignment: .leading, spacing: 8) {
                // Speech bubble
                VStack(alignment: .leading, spacing: 4) {
                    Text(message)
                        .font(.body)
                        .fontWeight(.medium)

                    if let secondary = secondaryMessage {
                        Text(secondary)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)

                // Actions
                HStack {
                    if let action = action {
                        Button(action.label) {
                            onAction?()
                        }
                        .buttonStyle(.borderedProminent)
                    }

                    Spacer()

                    if dismissible {
                        Button("Not now") {
                            onDismiss?()
                        }
                        .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding()
    }
}
```

**Integration Point**:
```swift
// File: Keuvi/Views/HomeView.swift

struct HomeView: View {
    @StateObject var viewModel = HomeViewModel()

    var body: some View {
        VStack {
            // Show penguin prompt if available
            if let prompt = viewModel.onboardingPrompt {
                PenguinCoachView(
                    message: prompt.message,
                    secondaryMessage: prompt.secondaryMessage,
                    action: prompt.action,
                    dismissible: prompt.dismissible,
                    onAction: { viewModel.handlePromptAction(prompt) },
                    onDismiss: { viewModel.dismissPrompt(prompt) }
                )
                .transition(.move(edge: .top).combined(with: .opacity))
            }

            // Rest of home content...
        }
    }
}
```

### 6.3 Android Implementation (Jetpack Compose)

```kotlin
// File: app/src/main/java/com/keuvi/ui/components/PenguinCoach.kt

data class PenguinCoachAction(
    val type: String,
    val target: String?,
    val label: String
)

@Composable
fun PenguinCoach(
    message: String,
    secondaryMessage: String?,
    action: PenguinCoachAction?,
    dismissible: Boolean,
    onAction: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Penguin avatar
        Image(
            painter = painterResource(R.drawable.penguin_avatar),
            contentDescription = "Keuvi Penguin",
            modifier = Modifier.size(60.dp)
        )

        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Speech bubble
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceVariant
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = message,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                    secondaryMessage?.let {
                        Text(
                            text = it,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Actions
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                action?.let {
                    Button(onClick = onAction) {
                        Text(it.label)
                    }
                }

                if (dismissible) {
                    TextButton(onClick = onDismiss) {
                        Text("Not now")
                    }
                }
            }
        }
    }
}
```

### 6.4 Client-Side State Management

```kotlin
// ViewModel pattern for Android (similar for iOS with ObservableObject)

class OnboardingState(
    val state: String,
    val prompt: OnboardingPrompt?,
    val milestones: Milestones
)

class HomeViewModel : ViewModel() {
    private val _onboardingState = MutableStateFlow<OnboardingState?>(null)
    val onboardingState: StateFlow<OnboardingState?> = _onboardingState

    init {
        loadProfile()
    }

    private fun loadProfile() {
        viewModelScope.launch {
            val profile = apiService.getProfile()
            _onboardingState.value = profile.onboarding
        }
    }

    fun handlePromptAction(prompt: OnboardingPrompt) {
        when (prompt.action?.type) {
            "continue" -> {
                // Mark welcome seen, refresh state
                viewModelScope.launch {
                    apiService.markWelcomeSeen()
                    loadProfile()
                }
            }
            "navigate" -> {
                // Navigate to target screen
                navigationManager.navigate(prompt.action.target)
            }
        }
    }

    fun dismissPrompt(prompt: OnboardingPrompt) {
        viewModelScope.launch {
            apiService.dismissPrompt(prompt.id)
            loadProfile()
        }
    }
}
```

---

## 7. Deployment Architecture

### 7.1 Backend Changes

1. **Migration**: Add new fields to `StudyPlan` model
2. **Data Migration**: Set existing users with diagnostics to `ENGAGED`
3. **Profile View**: Extend to include `onboarding` object
4. **New Views**: Add `/onboarding/dismiss` and `/onboarding/welcome-seen`

### 7.2 Rollout Strategy

| Phase | Action | Validation |
|-------|--------|------------|
| 1 | Deploy backend with migration | Verify no errors, existing users unaffected |
| 2 | Deploy iOS with feature flag OFF | Verify build, no crashes |
| 3 | Deploy Android with feature flag OFF | Verify build, no crashes |
| 4 | Enable flag for 10% of new users | Monitor completion rates |
| 5 | Enable for 100% of new users | Full rollout |

### 7.3 Feature Flag

```json
// Remote config
{
  "penguin_onboarding_enabled": true,
  "penguin_onboarding_rollout_percentage": 100
}
```

---

## 8. Implementation Roadmap

### Phase 1: Backend (Days 1-2)

1. **Migration**: Create and apply migration for new StudyPlan fields
2. **Rule Engine**: Implement `compute_onboarding_state()` function
3. **Profile Extension**: Add `onboarding` to `/profile` response
4. **New Endpoints**: Implement dismiss and welcome-seen endpoints
5. **Tests**: Unit tests for state machine logic

### Phase 2: iOS (Days 3-4)

1. **Component**: Build `PenguinCoachView` component
2. **Models**: Add onboarding DTOs and API client methods
3. **Integration**: Add to HomeView with state management
4. **Testing**: Manual QA of all onboarding states

### Phase 3: Android (Days 5-6)

1. **Component**: Build `PenguinCoach` composable
2. **Models**: Add onboarding data classes and API methods
3. **Integration**: Add to HomeScreen with ViewModel
4. **Testing**: Manual QA of all onboarding states

### Phase 4: QA & Polish (Day 7)

1. **End-to-end testing** across platforms
2. **Animation polish** for prompt appearance/dismissal
3. **Edge case handling** (offline, errors)
4. **Documentation update**

---

## 9. Security Considerations

### 9.1 Authorization

- All onboarding endpoints require authentication
- Users can only modify their own onboarding state
- State changes are idempotent and audit-logged

### 9.2 Rate Limiting

- Dismiss endpoint: 10 requests/minute per user
- Welcome-seen endpoint: 5 requests/minute per user

### 9.3 Data Privacy

- Onboarding timestamps are user data (included in GDPR export)
- Account deletion cascades to StudyPlan (existing behavior)

---

## 10. Non-Functional Requirements

### 10.1 Performance

| Metric | Target |
|--------|--------|
| Profile endpoint latency | < 200ms p95 |
| State computation | < 10ms |
| Client prompt render | < 100ms |

### 10.2 Reliability

- Onboarding state persisted in PostgreSQL (durable)
- Graceful degradation if state computation fails (show no prompt)
- Client caches last known state for offline resilience

### 10.3 Observability

Track these metrics:
- `onboarding.state.distribution` - Current state breakdown
- `onboarding.prompt.shown` - Prompt display count by type
- `onboarding.prompt.dismissed` - Dismissal count by type
- `onboarding.diagnostic.started` - Diagnostic start count from prompt
- `onboarding.completion.rate` - % reaching ENGAGED state

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# Backend state machine tests
def test_new_user_starts_in_welcome():
    study_plan = StudyPlan(user=user)
    assert compute_onboarding_state(study_plan) == 'WELCOME'

def test_welcome_seen_transitions_to_diagnostic_nudge():
    study_plan = StudyPlan(user=user, welcome_seen_at=now())
    assert compute_onboarding_state(study_plan) == 'DIAGNOSTIC_NUDGE'

def test_diagnostic_completed_transitions_to_post_diagnostic():
    study_plan = StudyPlan(user=user,
                           welcome_seen_at=now(),
                           reading_diagnostic_completed=True)
    assert compute_onboarding_state(study_plan) == 'POST_DIAGNOSTIC'

def test_dismissed_prompt_not_shown_again():
    study_plan = StudyPlan(user=user,
                           welcome_seen_at=now(),
                           diagnostic_prompt_dismissed_at=now())
    prompt = get_current_prompt(study_plan)
    assert prompt is None
```

### 11.2 Integration Tests

- Profile endpoint returns valid onboarding object
- Dismiss endpoint updates state correctly
- State transitions after diagnostic submission

### 11.3 End-to-End Tests

| Scenario | Steps | Expected |
|----------|-------|----------|
| New user onboarding | Register -> See welcome -> Continue -> See diagnostic prompt -> Start diagnostic | Diagnostic loads |
| Dismiss flow | Register -> See welcome -> Continue -> Dismiss diagnostic prompt | Prompt hidden, stays in DIAGNOSTIC_NUDGE state |
| Return visit | Complete diagnostic -> Close app -> Reopen | See POST_DIAGNOSTIC prompt |

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| State gets stuck | Low | Medium | Auto-transition after 7 days; manual reset in admin |
| Prompts too intrusive | Medium | Medium | All prompts dismissible; track dismiss rates |
| Performance regression | Low | Medium | Cache onboarding state; monitor latency |
| Migration breaks existing users | Low | High | Migration sets existing users to ENGAGED |

---

## Appendix A: File Locations

| File | Purpose |
|------|---------|
| `api/models.py` | StudyPlan model extension |
| `api/views.py` | UserProfileView extension + new onboarding views |
| `api/urls.py` | New endpoint routes |
| `api/onboarding_utils.py` | State machine and prompt catalog (NEW) |
| `Keuvi/Components/PenguinCoachView.swift` | iOS component (NEW) |
| `app/.../ui/components/PenguinCoach.kt` | Android component (NEW) |

---

## Appendix B: Message Tone Guidelines

The penguin personality is:
- **Calm**: Never urgent or pushy
- **Slightly sarcastic**: Light humor, never mean
- **Never shaming**: Encouraging even when user skips
- **Always optional**: User always has control

**Do**:
- "Hey! I'm the Keuvi penguin."
- "First things first: let's see what you're good at."
- "Nice work! I found some areas we can work on."

**Don't**:
- "You NEED to take the diagnostic!"
- "You haven't completed your profile yet!"
- "Don't skip this important step!"
