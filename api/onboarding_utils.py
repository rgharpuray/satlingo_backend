"""
Onboarding utilities for penguin-guided onboarding flow.

Location: /Users/rishi/argosventures/satlingo_backend/api/onboarding_utils.py

This module contains:
- compute_onboarding_state(): Rule engine for determining onboarding state
- get_current_prompt(): Returns the current prompt based on state and dismissal status
- PROMPTS: Message catalog for penguin prompts

Used by:
- api/views.py: UserProfileView (to include onboarding data in profile response)
- api/views.py: OnboardingDismissView (to dismiss prompts)
- api/views.py: OnboardingWelcomeSeenView (to mark welcome as seen)
"""

from django.utils import timezone
from datetime import timedelta


# Message catalog for penguin prompts
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

# Mapping from prompt_id to the dismissed_at field name on StudyPlan
PROMPT_DISMISSED_FIELDS = {
    'welcome': None,  # Welcome is not dismissible
    'profile_setup': 'profile_prompt_dismissed_at',
    'diagnostic_nudge': 'diagnostic_prompt_dismissed_at',
    'diagnostic_progress': 'diagnostic_prompt_dismissed_at',  # Same field as diagnostic_nudge
    'post_diagnostic': 'post_diagnostic_seen_at',  # Uses seen_at field for post-diagnostic
}


def has_diagnostic_in_progress(user) -> bool:
    """
    Check if user has started but not completed a diagnostic.

    This checks for any diagnostic lesson attempts that might be incomplete.
    For now, returns False as a conservative default since we don't track
    partial diagnostic progress separately.
    """
    # Future implementation could check for partial attempt state
    # For now, diagnostics are completed atomically
    return False


def compute_onboarding_state(study_plan) -> str:
    """
    Rule-based state computation for onboarding. No LLM calls.
    Called on profile endpoint or after relevant actions.

    State machine rules (in priority order):
    1. Already marked engaged -> ENGAGED
    2. Any diagnostic completed -> POST_DIAGNOSTIC or ENGAGED
    3. Diagnostic in progress -> DIAGNOSTIC_IN_PROGRESS
    4. Welcome seen but no diagnostic -> DIAGNOSTIC_NUDGE
    5. Fresh user -> WELCOME

    Args:
        study_plan: StudyPlan model instance

    Returns:
        str: The computed onboarding state
    """
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
    if has_diagnostic_in_progress(study_plan.user):
        return 'DIAGNOSTIC_IN_PROGRESS'

    # Rule 4: Welcome seen but no diagnostic started
    if study_plan.welcome_seen_at:
        # Profile is always "complete" after auth for now
        # Could add profile fields check here if needed
        return 'DIAGNOSTIC_NUDGE'

    # Rule 5: Fresh user
    return 'WELCOME'


def get_current_prompt(study_plan):
    """
    Get the current prompt based on state and dismissal status.

    Args:
        study_plan: StudyPlan model instance

    Returns:
        dict: The prompt definition, or None if no prompt should be shown
    """
    state = study_plan.onboarding_state
    prompt_def = PROMPTS.get(state)

    if not prompt_def:
        return None

    # Check if this prompt was dismissed
    prompt_id = prompt_def['id']
    dismissed_field = PROMPT_DISMISSED_FIELDS.get(prompt_id)

    if dismissed_field:
        dismissed_at = getattr(study_plan, dismissed_field, None)
        if dismissed_at:
            return None  # Prompt was dismissed

    return prompt_def.copy()


def get_onboarding_data(study_plan) -> dict:
    """
    Get the complete onboarding data object for API response.

    This function computes the current state, updates it on the model if changed,
    and returns the full onboarding data structure.

    Args:
        study_plan: StudyPlan model instance

    Returns:
        dict: Onboarding data for API response
    """
    # Compute current state
    computed_state = compute_onboarding_state(study_plan)

    # Update state if it changed
    if study_plan.onboarding_state != computed_state:
        study_plan.onboarding_state = computed_state
        study_plan.save(update_fields=['onboarding_state', 'updated_at'])

    # Get current prompt (may be None if dismissed)
    prompt = get_current_prompt(study_plan)

    # Build milestones
    milestones = {
        'welcome_seen': study_plan.welcome_seen_at is not None,
        'profile_complete': True,  # For now, profile is always complete after auth
        'first_diagnostic_completed': (
            study_plan.reading_diagnostic_completed or
            study_plan.writing_diagnostic_completed or
            study_plan.math_diagnostic_completed
        ),
        'first_practice_completed': study_plan.first_practice_completed_at is not None,
        'onboarding_completed': study_plan.onboarding_completed,
    }

    # Build diagnostic status
    diagnostic_status = {
        'reading': {
            'available': True,
            'completed': study_plan.reading_diagnostic_completed,
        },
        'writing': {
            'available': True,
            'completed': study_plan.writing_diagnostic_completed,
        },
        'math': {
            'available': True,
            'completed': study_plan.math_diagnostic_completed,
        },
    }

    return {
        'state': computed_state,
        'prompt': prompt,
        'milestones': milestones,
        'diagnostic_status': diagnostic_status,
    }


def dismiss_prompt(study_plan, prompt_id: str) -> bool:
    """
    Dismiss a prompt by setting the appropriate dismissed_at timestamp.

    Args:
        study_plan: StudyPlan model instance
        prompt_id: The prompt ID to dismiss

    Returns:
        bool: True if prompt was dismissed, False if invalid prompt_id
    """
    dismissed_field = PROMPT_DISMISSED_FIELDS.get(prompt_id)

    if not dismissed_field:
        # Either invalid prompt_id or non-dismissible prompt (like welcome)
        return False

    # Set the dismissed timestamp
    setattr(study_plan, dismissed_field, timezone.now())
    study_plan.save(update_fields=[dismissed_field, 'updated_at'])

    return True


def mark_welcome_seen(study_plan) -> None:
    """
    Mark the welcome prompt as seen and transition state.

    Args:
        study_plan: StudyPlan model instance
    """
    if study_plan.welcome_seen_at is None:
        study_plan.welcome_seen_at = timezone.now()
        # Recompute state after marking welcome seen
        study_plan.onboarding_state = compute_onboarding_state(study_plan)
        study_plan.save(update_fields=['welcome_seen_at', 'onboarding_state', 'updated_at'])


def mark_first_practice_completed(study_plan) -> None:
    """
    Mark that the user has completed their first practice session.
    This can transition the user to ENGAGED state.

    Args:
        study_plan: StudyPlan model instance
    """
    if study_plan.first_practice_completed_at is None:
        study_plan.first_practice_completed_at = timezone.now()
        # Recompute state after marking practice completed
        study_plan.onboarding_state = compute_onboarding_state(study_plan)

        # If now engaged, mark onboarding as completed
        if study_plan.onboarding_state == 'ENGAGED':
            study_plan.onboarding_completed = True

        study_plan.save(update_fields=[
            'first_practice_completed_at',
            'onboarding_state',
            'onboarding_completed',
            'updated_at'
        ])


def mark_post_diagnostic_seen(study_plan) -> None:
    """
    Mark that the user has seen the post-diagnostic prompt.

    Args:
        study_plan: StudyPlan model instance
    """
    if study_plan.post_diagnostic_seen_at is None:
        study_plan.post_diagnostic_seen_at = timezone.now()
        study_plan.save(update_fields=['post_diagnostic_seen_at', 'updated_at'])
