from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PassageViewSet, QuestionViewSet, ProgressView,
    PassageProgressView, StartSessionView, SubmitPassageView,
    ReviewPassageView, AnswerView, AdminPassageView
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
]

