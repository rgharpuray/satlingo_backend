from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    PassageViewSet, QuestionViewSet, ProgressView,
    PassageProgressView, StartSessionView, SubmitPassageView,
    ReviewPassageView, AnswerView, AdminPassageView, WordOfTheDayView,
    PassageAttemptsView, LessonViewSet, WritingSectionViewSet,
    SubmitWritingSectionView, ReviewWritingSectionView, WritingSectionAttemptsView,
    MathSectionViewSet, SubmitMathSectionView, ReviewMathSectionView, MathSectionAttemptsView,
    QuestionClassificationViewSet, UserProfileView, DiagnosticSubmitView,
    SubmitLessonView, ReviewLessonView, LessonAttemptsView
)
from .auth_views import register, login, me, google_oauth_url, google_oauth_callback, google_oauth_token
from .stripe_views import (
    create_checkout_session, create_portal_session,
    subscription_status, stripe_webhook, sync_subscription_from_stripe
)

router = DefaultRouter()
router.register(r'passages', PassageViewSet, basename='passage')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'writing-sections', WritingSectionViewSet, basename='writing-section')
router.register(r'math-sections', MathSectionViewSet, basename='math-section')
router.register(r'classifications', QuestionClassificationViewSet, basename='classification')

urlpatterns = [
    # Passages and Questions (handled by router)
    path('', include(router.urls)),
    
    # Progress endpoints
    path('progress', ProgressView.as_view(), name='progress'),
    path('progress/passages/<str:passage_id>', PassageProgressView.as_view(), name='progress-passage'),
    path('progress/passages/<str:passage_id>/start', StartSessionView.as_view(), name='progress-start'),
    path('progress/passages/<str:passage_id>/submit', SubmitPassageView.as_view(), name='progress-submit'),
    path('progress/passages/<str:passage_id>/review', ReviewPassageView.as_view(), name='progress-review'),
    path('progress/passages/<str:passage_id>/attempts', PassageAttemptsView.as_view(), name='progress-attempts'),
    
    # Writing section progress endpoints
    path('progress/writing-sections/<str:writing_section_id>/submit', SubmitWritingSectionView.as_view(), name='progress-writing-submit'),
    path('progress/writing-sections/<str:writing_section_id>/review', ReviewWritingSectionView.as_view(), name='progress-writing-review'),
    path('progress/writing-sections/<str:writing_section_id>/attempts', WritingSectionAttemptsView.as_view(), name='progress-writing-attempts'),
    
    # Math section progress endpoints
    path('progress/math-sections/<str:math_section_id>/submit', SubmitMathSectionView.as_view(), name='progress-math-submit'),
    path('progress/math-sections/<str:math_section_id>/review', ReviewMathSectionView.as_view(), name='progress-math-review'),
    path('progress/math-sections/<str:math_section_id>/attempts', MathSectionAttemptsView.as_view(), name='progress-math-attempts'),
    
    # Answers endpoints
    path('answers', AnswerView.as_view(), name='answers'),
    path('answers/passage/<str:passage_id>', AnswerView.as_view(), name='answers-passage'),
    
    # Admin endpoints
    path('admin/passages', AdminPassageView.as_view(), name='admin-passages'),
    path('admin/passages/<str:passage_id>', AdminPassageView.as_view(), name='admin-passage-detail'),
    
    # Authentication endpoints
    path('auth/register', register, name='register'),
    path('auth/login', login, name='login'),
    path('auth/me', me, name='me'),
    path('auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/url', google_oauth_url, name='google-oauth-url'),
    path('auth/google/callback', google_oauth_callback, name='google-oauth-callback'),
    path('auth/google/token', google_oauth_token, name='google-oauth-token'),  # For iOS: verify ID token directly
    
    # Stripe/Payment endpoints
    path('payments/checkout', create_checkout_session, name='create-checkout'),
    path('payments/portal', create_portal_session, name='create-portal'),
    path('payments/subscription', subscription_status, name='subscription-status'),
    path('payments/sync', sync_subscription_from_stripe, name='sync-subscription'),
    path('payments/webhook', stripe_webhook, name='stripe-webhook'),
    
    # Word of the Day
    path('word-of-the-day', WordOfTheDayView.as_view(), name='word-of-the-day'),
    
    # User Profile (strengths/weaknesses)
    path('profile', UserProfileView.as_view(), name='user-profile'),
    
    # Diagnostic test submission
    path('diagnostic/submit', DiagnosticSubmitView.as_view(), name='diagnostic-submit'),
    
    # Lesson progress endpoints
    path('progress/lessons/<str:lesson_id>/submit', SubmitLessonView.as_view(), name='progress-lesson-submit'),
    path('progress/lessons/<str:lesson_id>/review', ReviewLessonView.as_view(), name='progress-lesson-review'),
    path('progress/lessons/<str:lesson_id>/attempts', LessonAttemptsView.as_view(), name='progress-lesson-attempts'),
]

