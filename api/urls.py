from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    PassageViewSet, QuestionViewSet, ProgressView,
    PassageProgressView, StartSessionView, SubmitPassageView,
    ReviewPassageView, AnswerView, AdminPassageView
)
from .auth_views import register, login, me
from .stripe_views import (
    create_checkout_session, create_portal_session,
    subscription_status, stripe_webhook
)

router = DefaultRouter()
router.register(r'passages', PassageViewSet, basename='passage')
router.register(r'questions', QuestionViewSet, basename='question')

urlpatterns = [
    # Passages and Questions (handled by router)
    path('', include(router.urls)),
    
    # Progress endpoints
    path('progress', ProgressView.as_view(), name='progress'),
    path('progress/passages/<str:passage_id>', PassageProgressView.as_view(), name='progress-passage'),
    path('progress/passages/<str:passage_id>/start', StartSessionView.as_view(), name='progress-start'),
    path('progress/passages/<str:passage_id>/submit', SubmitPassageView.as_view(), name='progress-submit'),
    path('progress/passages/<str:passage_id>/review', ReviewPassageView.as_view(), name='progress-review'),
    
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
    
    # Stripe/Payment endpoints
    path('payments/checkout', create_checkout_session, name='create-checkout'),
    path('payments/portal', create_portal_session, name='create-portal'),
    path('payments/subscription', subscription_status, name='subscription-status'),
    path('payments/webhook', stripe_webhook, name='stripe-webhook'),
]

