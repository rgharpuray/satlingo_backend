from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta, date
import uuid
import json
import os
from django.conf import settings

from .models import (
    Passage, Question, QuestionOption, User, UserSession,
    UserProgress, UserAnswer, WordOfTheDay, PassageAttempt,
    Lesson, LessonQuestion, LessonQuestionOption, LessonAttempt,
    WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption,
    WritingSectionAttempt,
    MathSection, MathQuestion, MathQuestionOption, MathAsset, MathSectionAttempt,
    QuestionClassification, StudyPlan
)
from .serializers import (
    PassageListSerializer, PassageDetailSerializer, QuestionListSerializer,
    QuestionSerializer, UserProgressSerializer, UserProgressSummarySerializer,
    UserAnswerSerializer, SubmitPassageRequestSerializer, SubmitPassageResponseSerializer,
    ReviewResponseSerializer, ReviewAnswerSerializer, CreatePassageSerializer,
    PassageAnnotationSerializer, WordOfTheDaySerializer,
    LessonListSerializer, LessonDetailSerializer, LessonQuestionSerializer,
    WritingSectionListSerializer, WritingSectionDetailSerializer, WritingSectionQuestionSerializer,
    SubmitWritingSectionRequestSerializer, SubmitWritingSectionResponseSerializer,
    WritingSectionAttemptSerializer,
    MathSectionListSerializer, MathSectionDetailSerializer, MathQuestionSerializer,
    QuestionClassificationSerializer, UserStrengthWeaknessSerializer
)


class PassageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for passages endpoints.
    GET /passages - List all passages
    GET /passages/:id - Get passage detail
    GET /passages/:id/questions - Get questions for a passage
    """
    queryset = Passage.objects.all()
    serializer_class = PassageListSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PassageDetailSerializer
        return PassageListSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context for attempt_count"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """Get passage detail with premium check"""
        passage = self.get_object()
        user = get_user_from_request(request)
        
        # Check if passage is premium and user doesn't have access
        if passage.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This passage requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Passage.objects.annotate(
            question_count=Count('questions'),
            header_display_order=Coalesce('header__display_order', 0)
        ).select_related('header').order_by(
            '-header_display_order',
            '-order_within_header',
            '-display_order',
            '-created_at'
        )
        difficulty = self.request.query_params.get('difficulty', None)
        tier = self.request.query_params.get('tier', None)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Get user for premium check
        user = get_user_from_request(self.request)
        is_premium_user = user and (user.is_premium or user.has_active_subscription)
        
        # Handle tier filtering
        if tier:
            # If explicitly requesting premium tier, check access
            if tier == 'premium' and not is_premium_user:
                # Non-premium users requesting premium get empty result
                queryset = queryset.none()
            else:
                queryset = queryset.filter(tier=tier)
        # No tier filter: show all content (including premium)
        # Frontend will handle showing preview/lock for premium content
        # Premium users see all passages (free + premium)
        # Non-premium users see all but with preview/lock on premium
        # No filtering - let frontend handle the UI
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for a passage without correct answers/explanations"""
        passage = self.get_object()
        user = get_user_from_request(request)
        
        # Check if passage is premium and user doesn't have access
        if passage.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This passage requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        questions = passage.questions.all().order_by('order')
        serializer = QuestionListSerializer(questions, many=True)
        return Response({'questions': serializer.data})
    
    @action(detail=True, methods=['get'])
    def annotations(self, request, pk=None):
        """
        Get annotations for a passage.
        Only returns annotations for questions the user has answered.
        Use this to get all annotations for a passage after answering multiple questions.
        """
        passage = self.get_object()
        user = get_user_from_request(request)
        
        # Check if passage is premium and user doesn't have access
        if passage.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This passage requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get all annotations for this passage
        all_annotations = passage.annotations.all().select_related('question')
        
        # Filter: only show annotations for questions the user has answered
        if user:
            # Get all question IDs the user has answered for this passage
            answered_question_ids = set(
                UserAnswer.objects.filter(
                    user=user,
                    question__passage=passage
                ).values_list('question_id', flat=True)
            )
            
            # Filter annotations to only those for answered questions
            # (or annotations with no question_id - show those too)
            filtered_annotations = [
                ann for ann in all_annotations
                if ann.question_id is None or ann.question_id in answered_question_ids
            ]
        else:
            # Anonymous users don't see any annotations
            filtered_annotations = []
        
        serializer = PassageAnnotationSerializer(filtered_annotations, many=True)
        return Response({'annotations': serializer.data})


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for questions endpoints.
    GET /questions/:id - Get a specific question
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get question without correct answer for active sessions"""
        question = self.get_object()
        serializer = QuestionListSerializer(question)
        return Response(serializer.data)


def get_user_from_request(request):
    """Helper function to get user from request (supports JWT authentication)"""
    # Check if user is authenticated via JWT or session
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


class ProgressView(APIView):
    """
    View for user progress endpoints.
    GET /progress - Get user's progress across all passages
    """
    
    def get(self, request):
        """GET /progress - Get user's progress across all passages"""
        user = get_user_from_request(request)
        
        if user:
            progress_queryset = UserProgress.objects.filter(user=user)
        else:
            # For anonymous users, return empty progress
            progress_queryset = UserProgress.objects.none()
        
        completed_passages = list(
            progress_queryset.filter(is_completed=True).values_list('passage_id', flat=True)
        )
        scores = {
            str(progress.passage_id): progress.score
            for progress in progress_queryset.filter(is_completed=True, score__isnull=False)
        }
        total_passages = Passage.objects.count()
        completed_count = len(completed_passages)
        
        serializer = UserProgressSummarySerializer({
            'completed_passages': completed_passages,
            'scores': scores,
            'total_passages': total_passages,
            'completed_count': completed_count,
        })
        return Response(serializer.data)


class PassageProgressView(APIView):
    """
    View for passage-specific progress endpoints.
    GET /progress/passages/:passage_id - Get progress for a specific passage
    """
    
    def get(self, request, passage_id):
        """GET /progress/passages/:passage_id"""
        user = get_user_from_request(request)
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        if user:
            progress, _ = UserProgress.objects.get_or_create(
                user=user,
                passage=passage,
                defaults={'is_completed': False}
            )
        else:
            # For anonymous users, return default progress
            progress = UserProgress(
                user=None,
                passage=passage,
                is_completed=False
            )
        
        serializer = UserProgressSerializer(progress)
        return Response(serializer.data)


class StartSessionView(APIView):
    """
    View for starting a passage session.
    POST /progress/passages/:passage_id/start - Start a session
    """
    
    def post(self, request, passage_id):
        """POST /progress/passages/:passage_id/start"""
        user = get_user_from_request(request)
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        # For now, just return a session ID
        # In a full implementation, you'd create a session record
        session_id = uuid.uuid4()
        
        return Response({
            'session_id': str(session_id),
            'passage_id': str(passage.id),
            'started_at': timezone.now().isoformat(),
        })


class SubmitPassageView(APIView):
    """
    View for submitting answers to a passage.
    POST /progress/passages/:passage_id/submit - Submit answers
    """
    
    def post(self, request, passage_id):
        """POST /progress/passages/:passage_id/submit"""
        user = get_user_from_request(request)
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        serializer = SubmitPassageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        answers_data = serializer.validated_data['answers']
        time_spent = serializer.validated_data.get('time_spent_seconds', 0)
        
        # Get all questions for the passage
        questions = passage.questions.all().order_by('order')
        question_dict = {str(q.id): q for q in questions}
        
        # Process answers
        answer_results = []
        correct_count = 0
        total_questions = questions.count()
        
        for answer_data in answers_data:
            question_id = str(answer_data['question_id'])
            if question_id not in question_dict:
                continue
            
            question = question_dict[question_id]
            selected_index = answer_data['selected_option_index']
            is_correct = selected_index == question.correct_answer_index
            
            if is_correct:
                correct_count += 1
            
            # Save user answer (create new record for each attempt)
            if user:
                UserAnswer.objects.create(
                    user=user,
                    question=question,
                    selected_option_index=selected_index,
                    is_correct=is_correct,
                )
            
            # Get annotations for this question (now that user has answered)
            annotations = []
            if user:  # Only include annotations if user is authenticated
                from .serializers import PassageAnnotationSerializer
                question_annotations = question.annotations.all().order_by('start_char')
                annotations = PassageAnnotationSerializer(question_annotations, many=True).data
            
            answer_results.append({
                'question_id': question_id,
                'selected_option_index': selected_index,
                'correct_answer_index': question.correct_answer_index,
                'is_correct': is_correct,
                'explanation': question.explanation,
                'annotations': annotations,  # Include annotations for this question
            })
        
        # Calculate score
        score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0
        
        # Create a new attempt record (for logged-in users only)
        attempt = None
        if user:
            from .models import PassageAttempt
            attempt = PassageAttempt.objects.create(
                user=user,
                passage=passage,
                score=score,
                correct_count=correct_count,
                total_questions=total_questions,
                time_spent_seconds=time_spent,
                answers_data=answer_results,
            )
            
            # Also update UserProgress to track latest (for backward compatibility)
            UserProgress.objects.update_or_create(
                user=user,
                passage=passage,
                defaults={
                    'is_completed': True,
                    'score': score,  # Store latest score
                    'time_spent_seconds': time_spent,
                    'completed_at': timezone.now(),
                }
            )
        
        response_data = {
            'passage_id': str(passage.id),
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'is_completed': True,
            'answers': answer_results,
            'completed_at': timezone.now().isoformat(),
            'attempt_id': str(attempt.id) if attempt else None,  # Include attempt ID
        }
        
        serializer = SubmitPassageResponseSerializer(response_data)
        return Response(serializer.data)


class ReviewPassageView(APIView):
    """
    View for getting review data for a completed passage.
    GET /progress/passages/:passage_id/review - Get review data
    """
    
    def get(self, request, passage_id):
        """GET /progress/passages/:passage_id/review"""
        user = get_user_from_request(request)
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        # Get user progress
        if user:
            try:
                progress = UserProgress.objects.get(user=user, passage=passage)
                score = progress.score
            except UserProgress.DoesNotExist:
                score = None
        else:
            score = None
        
        # Get user answers
        if user:
            user_answers = {
                str(ua.question_id): ua
                for ua in UserAnswer.objects.filter(user=user, question__passage=passage)
            }
        else:
            user_answers = {}
        
        # Build review data
        review_answers = []
        questions = passage.questions.all().order_by('order')
        
        # Get annotations for answered questions
        if user:
            answered_question_ids = set(
                UserAnswer.objects.filter(
                    user=user,
                    question__passage=passage
                ).values_list('question_id', flat=True)
            )
            # Get annotations for answered questions
            annotations_by_question = {}
            for ann in passage.annotations.filter(question_id__in=answered_question_ids).select_related('question'):
                q_id = str(ann.question_id)
                if q_id not in annotations_by_question:
                    annotations_by_question[q_id] = []
                annotations_by_question[q_id].append({
                    'id': str(ann.id),
                    'start_char': ann.start_char,
                    'end_char': ann.end_char,
                    'selected_text': ann.selected_text,
                    'explanation': ann.explanation,
                    'order': ann.order,
                })
        else:
            annotations_by_question = {}
        
        correct_count = 0
        total_questions = questions.count()
        
        for question in questions:
            user_answer = user_answers.get(str(question.id))
            options = [opt.text for opt in question.options.all().order_by('order')]
            
            # Count correct answers
            if user_answer and user_answer.is_correct:
                correct_count += 1
            
            # Include annotations for this question if user has answered it
            question_annotations = annotations_by_question.get(str(question.id), [])
            
            review_answers.append({
                'question_id': str(question.id),
                'question_text': question.text,
                'options': options,
                'selected_option_index': user_answer.selected_option_index if user_answer else None,
                'correct_answer_index': question.correct_answer_index,
                'is_correct': user_answer.is_correct if user_answer else None,
                'explanation': question.explanation,
                'annotations': question_annotations,  # Annotations for this question
            })
        
        response_data = {
            'passage_id': str(passage.id),
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'answers': review_answers,
        }
        
        serializer = ReviewResponseSerializer(response_data)
        return Response(serializer.data)


class AnswerView(APIView):
    """
    View for user answers endpoints.
    POST /answers - Submit an answer
    GET /answers/passage/:passage_id - Get all answers for a passage
    """
    
    def post(self, request):
        """POST /answers - Submit an answer"""
        user = get_user_from_request(request)
        
        question_id = request.data.get('question_id')
        selected_option_index = request.data.get('selected_option_index')
        
        if not question_id or selected_option_index is None:
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'question_id and selected_option_index are required'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Question not found'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        is_correct = selected_option_index == question.correct_answer_index
        
        if user:
            user_answer, created = UserAnswer.objects.update_or_create(
                user=user,
                question=question,
                defaults={
                    'selected_option_index': selected_option_index,
                    'is_correct': is_correct,
                }
            )
            # Fetch with annotations prefetched for serializer
            user_answer = UserAnswer.objects.select_related('question').prefetch_related('question__annotations').get(pk=user_answer.pk)
            # Include annotations for this question (now that user has answered)
            serializer = UserAnswerSerializer(user_answer)
            return Response(serializer.data)
        else:
            # For anonymous users, return a response without saving (no annotations)
            return Response({
                'id': str(uuid.uuid4()),
                'question_id': str(question_id),
                'selected_option_index': selected_option_index,
                'answered_at': timezone.now().isoformat(),
                'annotations': [],  # No annotations for anonymous users
            })
    
    def get(self, request, passage_id):
        """GET /answers/passage/:passage_id"""
        user = get_user_from_request(request)
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        if user:
            answers = UserAnswer.objects.filter(user=user, question__passage=passage).select_related('question').prefetch_related('question__annotations')
            serializer = UserAnswerSerializer(answers, many=True)
            return Response({'answers': serializer.data})
        else:
            return Response({'answers': []})


class AdminPassageView(APIView):
    """
    Admin endpoints for managing passages.
    POST /admin/passages - Create a passage
    PUT /admin/passages/:id - Update a passage
    DELETE /admin/passages/:id - Delete a passage
    """
    
    def post(self, request):
        """POST /admin/passages"""
        serializer = CreatePassageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create passage
        passage = Passage.objects.create(
            title=serializer.validated_data['title'],
            content=serializer.validated_data['content'],
            difficulty=serializer.validated_data['difficulty'],
        )
        
        # Create questions and options
        for q_data in serializer.validated_data['questions']:
            question = Question.objects.create(
                passage=passage,
                text=q_data['text'],
                correct_answer_index=q_data['correct_answer_index'],
                explanation=q_data.get('explanation'),
                order=q_data['order'],
            )
            
            # Create options
            for idx, option_text in enumerate(q_data['options']):
                QuestionOption.objects.create(
                    question=question,
                    text=option_text,
                    order=idx,
                )
        
        response_serializer = PassageDetailSerializer(passage)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def put(self, request, passage_id):
        """PUT /admin/passages/:id"""
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        serializer = CreatePassageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update passage
        passage.title = serializer.validated_data['title']
        passage.content = serializer.validated_data['content']
        passage.difficulty = serializer.validated_data['difficulty']
        passage.save()
        
        # Delete existing questions
        passage.questions.all().delete()
        
        # Create new questions and options
        for q_data in serializer.validated_data['questions']:
            question = Question.objects.create(
                passage=passage,
                text=q_data['text'],
                correct_answer_index=q_data['correct_answer_index'],
                explanation=q_data.get('explanation'),
                order=q_data['order'],
            )
            
            # Create options
            for idx, option_text in enumerate(q_data['options']):
                QuestionOption.objects.create(
                    question=question,
                    text=option_text,
                    order=idx,
                )
        
        response_serializer = PassageDetailSerializer(passage)
        return Response(response_serializer.data)
    
    def delete(self, request, passage_id):
        """DELETE /admin/passages/:id"""
        # Convert string to UUID (handles both uppercase and lowercase)
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        passage = get_object_or_404(Passage, id=passage_uuid)
        passage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PassageAttemptsView(APIView):
    """
    View for getting past attempts for a passage.
    GET /progress/passages/:passage_id/attempts - Get all attempts for a passage
    """
    
    def get(self, request, passage_id):
        """GET /progress/passages/:passage_id/attempts"""
        user = get_user_from_request(request)
        
        # Fallback: check request.user directly if get_user_from_request didn't work
        if not user and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        if not user:
            return Response(
                {'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required. Please log in.'}},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Convert string to UUID
        try:
            passage_uuid = uuid.UUID(str(passage_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid passage ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        passage = get_object_or_404(Passage, id=passage_uuid)
        
        # Get all attempts for this user and passage
        attempts = PassageAttempt.objects.filter(
            user=user,
            passage=passage
        ).order_by('-completed_at')
        
        from .serializers import PassageAttemptSerializer
        # Convert attempts to serializer format
        attempts_data = []
        for attempt in attempts:
            attempts_data.append({
                'id': attempt.id,
                'passage_id': str(attempt.passage.id),
                'score': attempt.score,
                'correct_count': attempt.correct_count,
                'total_questions': attempt.total_questions,
                'time_spent_seconds': attempt.time_spent_seconds,
                'completed_at': attempt.completed_at,
                'answers': attempt.answers_data or [],
            })
        serializer = PassageAttemptSerializer(attempts_data, many=True)
        return Response(serializer.data)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for lessons endpoints.
    GET /lessons - List all lessons
    GET /lessons/:id - Get lesson detail
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonListSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LessonDetailSerializer
        return LessonListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get lesson detail with premium check"""
        lesson = self.get_object()
        user = get_user_from_request(request)
        
        # Check if lesson is premium and user doesn't have access
        if lesson.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This lesson requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Lesson.objects.annotate(
            question_count=Count('questions')
        ).select_related('header')  # Optimize header loading
        difficulty = self.request.query_params.get('difficulty', None)
        tier = self.request.query_params.get('tier', None)
        lesson_type = self.request.query_params.get('lesson_type', None)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)
        
        # Get user for premium check
        user = get_user_from_request(self.request)
        is_premium_user = user and (user.is_premium or user.has_active_subscription)
        
        # Handle tier filtering
        if tier:
            if tier == 'premium' and not is_premium_user:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(tier=tier)
        # No tier filter: show all content (including premium)
        # Frontend will handle showing preview/lock for premium content
        # No filtering - let frontend handle the UI
        
        return queryset


class WritingSectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for writing sections endpoints.
    GET /writing-sections - List all writing sections
    GET /writing-sections/:id - Get writing section detail
    GET /writing-sections/:id/questions - Get questions for a writing section
    """
    queryset = WritingSection.objects.all()
    serializer_class = WritingSectionListSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WritingSectionDetailSerializer
        return WritingSectionListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get writing section detail with premium check"""
        writing_section = self.get_object()
        user = get_user_from_request(request)
        
        # Check if writing section is premium and user doesn't have access
        if writing_section.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This writing section requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = WritingSection.objects.annotate(
            question_count=Count('questions'),
            selection_count=Count('selections'),
            header_display_order=Coalesce('header__display_order', 0)
        ).select_related('header').order_by(
            '-header_display_order',
            '-order_within_header',
            '-display_order',
            '-created_at'
        )
        difficulty = self.request.query_params.get('difficulty', None)
        tier = self.request.query_params.get('tier', None)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Get user for premium check
        user = get_user_from_request(self.request)
        is_premium_user = user and (user.is_premium or user.has_active_subscription)
        
        # Handle tier filtering
        if tier:
            if tier == 'premium' and not is_premium_user:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(tier=tier)
        # No tier filter: show all content (including premium)
        # Frontend will handle showing preview/lock for premium content
        # No filtering - let frontend handle the UI
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for a writing section without correct answers/explanations"""
        writing_section = self.get_object()
        user = get_user_from_request(request)
        
        # Check if writing section is premium and user doesn't have access
        if writing_section.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This writing section requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        questions = writing_section.questions.all().order_by('order')
        serializer = WritingSectionQuestionSerializer(questions, many=True)
        return Response({'questions': serializer.data})


class MathSectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for math sections endpoints.
    GET /math-sections - List all math sections
    GET /math-sections/:id - Get math section detail
    GET /math-sections/:id/questions - Get questions for a math section
    """
    queryset = MathSection.objects.all()
    serializer_class = MathSectionListSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MathSectionDetailSerializer
        return MathSectionListSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context for attempt_count"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """Get math section detail with premium check"""
        math_section = self.get_object()
        user = get_user_from_request(request)
        
        # Check if math section is premium and user doesn't have access
        if math_section.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This math section requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = MathSection.objects.annotate(
            question_count=Count('questions'),
            asset_count=Count('assets'),
            header_display_order=Coalesce('header__display_order', 0)
        ).select_related('header').order_by(
            '-header_display_order',
            '-order_within_header',
            '-display_order',
            '-created_at'
        )
        difficulty = self.request.query_params.get('difficulty', None)
        tier = self.request.query_params.get('tier', None)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Get user for premium check
        user = get_user_from_request(self.request)
        is_premium_user = user and (user.is_premium or user.has_active_subscription)
        
        # Handle tier filtering
        if tier:
            if tier == 'premium' and not is_premium_user:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(tier=tier)
        # No tier filter: show all content (including premium)
        # Frontend will handle showing preview/lock for premium content
        # No filtering - let frontend handle the UI
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for a math section without correct answers/explanations"""
        math_section = self.get_object()
        user = get_user_from_request(request)
        
        # Check if math section is premium and user doesn't have access
        if math_section.tier == 'premium':
            if not user or not (user.is_premium or user.has_active_subscription):
                return Response(
                    {'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'This math section requires a premium subscription',
                        'upgrade_url': '/web/subscription'
                    }},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        questions = math_section.questions.all().order_by('order')
        serializer = MathQuestionSerializer(questions, many=True)
        return Response({'results': serializer.data})


class SubmitWritingSectionView(APIView):
    """
    View for submitting answers to a writing section.
    POST /progress/writing-sections/:writing_section_id/submit - Submit answers
    
    Supports incremental submissions (one question at a time) and aggregates into final attempt.
    """
    
    def post(self, request, writing_section_id):
        """POST /progress/writing-sections/:writing_section_id/submit"""
        user = get_user_from_request(request)
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(writing_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid writing section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        writing_section = get_object_or_404(WritingSection, id=section_uuid)
        
        serializer = SubmitWritingSectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        answers_data = serializer.validated_data['answers']
        time_spent = serializer.validated_data.get('time_spent_seconds', 0)
        is_complete = request.data.get('is_complete', False)
        
        # Get all questions for the writing section
        questions = writing_section.questions.all().order_by('order')
        question_dict = {str(q.id): q for q in questions}
        total_questions_in_section = questions.count()
        
        # Check if there's an in-progress attempt
        in_progress_attempt = None
        if user:
            recent_attempts = WritingSectionAttempt.objects.filter(
                user=user,
                writing_section=writing_section
            ).order_by('-created_at')
            
            if recent_attempts.exists():
                latest_attempt = recent_attempts.first()
                if len(latest_attempt.answers_data) < total_questions_in_section:
                    in_progress_attempt = latest_attempt
        
        # Process answers
        answer_results = []
        if in_progress_attempt:
            # Merge with existing answers
            existing_answers = {a['question_id']: a for a in in_progress_attempt.answers_data}
            
            for answer_data in answers_data:
                question_id = str(answer_data['question_id'])
                if question_id not in question_dict:
                    continue
                
                question = question_dict[question_id]
                selected_index = answer_data['selected_option_index']
                is_correct = selected_index == question.correct_answer_index
                
                answer_result = {
                    'question_id': question_id,
                    'selected_option_index': selected_index,
                    'correct_answer_index': question.correct_answer_index,
                    'is_correct': is_correct,
                    'explanation': question.explanation,
                }
                existing_answers[question_id] = answer_result
            
            answer_results = list(existing_answers.values())
        else:
            # New submission
            for answer_data in answers_data:
                question_id = str(answer_data['question_id'])
                if question_id not in question_dict:
                    continue
                
                question = question_dict[question_id]
                selected_index = answer_data['selected_option_index']
                is_correct = selected_index == question.correct_answer_index
                
                # Note: UserAnswer is only for Passage questions
                # Writing section answers are stored in WritingSectionAttempt.answers_data (JSON field)
                
                answer_results.append({
                    'question_id': question_id,
                    'selected_option_index': selected_index,
                    'correct_answer_index': question.correct_answer_index,
                    'is_correct': is_correct,
                    'explanation': question.explanation,
                })
        
        # Calculate score
        correct_count = sum(1 for a in answer_results if a.get('is_correct', False))
        total_questions_answered = len(answer_results)
        is_final_submission = is_complete or (total_questions_answered >= total_questions_in_section)
        
        total_questions_for_score = total_questions_in_section if is_final_submission else total_questions_answered
        score = int((correct_count / total_questions_for_score * 100)) if total_questions_for_score > 0 else 0
        
        # Update or create attempt record
        attempt = None
        if user:
            if in_progress_attempt and not is_final_submission:
                # Update existing in-progress attempt
                in_progress_attempt.answers_data = answer_results
                in_progress_attempt.correct_count = correct_count
                in_progress_attempt.total_questions = total_questions_answered
                in_progress_attempt.time_spent_seconds = time_spent
                in_progress_attempt.save()
                attempt = in_progress_attempt
            elif in_progress_attempt:
                # Finalize existing attempt
                in_progress_attempt.score = score
                in_progress_attempt.correct_count = correct_count
                in_progress_attempt.total_questions = total_questions_in_section
                in_progress_attempt.answers_data = answer_results
                in_progress_attempt.time_spent_seconds = time_spent
                in_progress_attempt.save()
                attempt = in_progress_attempt
            else:
                # Create new attempt
                attempt = WritingSectionAttempt.objects.create(
                    user=user,
                    writing_section=writing_section,
                    score=score,
                    correct_count=correct_count,
                    total_questions=total_questions_in_section if is_final_submission else total_questions_answered,
                    time_spent_seconds=time_spent,
                    answers_data=answer_results,
                )
        
        response_data = {
            'writing_section_id': str(writing_section.id),
            'score': score,
            'total_questions': total_questions_in_section,
            'total_questions_answered': total_questions_answered,
            'correct_count': correct_count,
            'is_completed': is_final_submission,
            'answers': answer_results,
            'completed_at': timezone.now().isoformat() if is_final_submission else None,
            'attempt_id': str(attempt.id) if attempt else None,
        }
        
        serializer = SubmitWritingSectionResponseSerializer(response_data)
        return Response(serializer.data)


class ReviewWritingSectionView(APIView):
    """
    View for getting review data for a completed writing section.
    GET /progress/writing-sections/:writing_section_id/review - Get review data
    """
    
    def get(self, request, writing_section_id):
        """GET /progress/writing-sections/:writing_section_id/review"""
        user = get_user_from_request(request)
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(writing_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid writing section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        writing_section = get_object_or_404(WritingSection, id=section_uuid)
        
        # Get the most recent attempt for this user and writing section
        attempt = None
        if user:
            attempt = WritingSectionAttempt.objects.filter(
                user=user,
                writing_section=writing_section
            ).order_by('-completed_at').first()
        
        # Build review data from the attempt
        review_answers = []
        questions = writing_section.questions.all().order_by('order')
        
        correct_count = 0
        total_questions = questions.count()
        
        # Get answers from attempt if available
        attempt_answers = {}
        if attempt and attempt.answers_data:
            for ans in attempt.answers_data:
                attempt_answers[str(ans.get('question_id'))] = ans
        
        for question in questions:
            question_id_str = str(question.id)
            attempt_answer = attempt_answers.get(question_id_str)
            options = [opt.text for opt in question.options.all().order_by('order')]
            
            # Count correct answers
            if attempt_answer and attempt_answer.get('is_correct'):
                correct_count += 1
            
            review_answers.append({
                'question_id': question_id_str,
                'question_text': question.text,
                'options': options,
                'selected_option_index': attempt_answer.get('selected_option_index') if attempt_answer else None,
                'correct_answer_index': question.correct_answer_index,
                'is_correct': attempt_answer.get('is_correct', False) if attempt_answer else False,
                'explanation': question.explanation,
            })
        
        score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0
        
        response_data = {
            'writing_section_id': str(writing_section.id),
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'answers': review_answers,
        }
        
        serializer = ReviewResponseSerializer(response_data)
        return Response(serializer.data)


class WritingSectionAttemptsView(APIView):
    """
    View for getting past attempts for a writing section.
    GET /progress/writing-sections/:writing_section_id/attempts - Get all attempts for a writing section
    """
    
    def get(self, request, writing_section_id):
        """GET /progress/writing-sections/:writing_section_id/attempts"""
        user = get_user_from_request(request)
        
        if not user:
            return Response(
                {'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required. Please log in.'}},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(writing_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid writing section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        writing_section = get_object_or_404(WritingSection, id=section_uuid)
        
        # Get all attempts for this user and writing section
        attempts = WritingSectionAttempt.objects.filter(
            user=user,
            writing_section=writing_section
        ).order_by('-completed_at')
        
        # Convert attempts to serializer format
        attempts_data = []
        for attempt in attempts:
            attempts_data.append({
                'id': attempt.id,
                'writing_section_id': str(attempt.writing_section.id),
                'score': attempt.score,
                'correct_count': attempt.correct_count,
                'total_questions': attempt.total_questions,
                'time_spent_seconds': attempt.time_spent_seconds,
                'completed_at': attempt.completed_at,
                'answers': attempt.answers_data or [],
            })
        serializer = WritingSectionAttemptSerializer(attempts_data, many=True)
        return Response(serializer.data)


class SubmitMathSectionView(APIView):
    """
    View for submitting answers to a math section.
    POST /progress/math-sections/:math_section_id/submit - Submit answers
    
    Supports incremental submissions (one question at a time) and aggregates into final attempt.
    """
    
    def post(self, request, math_section_id):
        """POST /progress/math-sections/:math_section_id/submit"""
        user = get_user_from_request(request)
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(math_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid math section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        math_section = get_object_or_404(MathSection, id=section_uuid)
        
        # Use the same serializer as writing sections
        serializer = SubmitWritingSectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        answers_data = serializer.validated_data['answers']
        time_spent = serializer.validated_data.get('time_spent_seconds', 0)
        is_complete = request.data.get('is_complete', False)
        
        # Get all questions for the math section
        questions = math_section.questions.all().order_by('order')
        question_dict = {str(q.id): q for q in questions}
        total_questions_in_section = questions.count()
        
        # Check if there's an in-progress attempt
        in_progress_attempt = None
        if user:
            recent_attempts = MathSectionAttempt.objects.filter(
                user=user,
                math_section=math_section
            ).order_by('-created_at')
            
            if recent_attempts.exists():
                latest_attempt = recent_attempts.first()
                if len(latest_attempt.answers_data) < total_questions_in_section:
                    in_progress_attempt = latest_attempt
        
        # Process answers
        answer_results = []
        if in_progress_attempt:
            # Merge with existing answers
            existing_answers = {a['question_id']: a for a in in_progress_attempt.answers_data}
            
            for answer_data in answers_data:
                question_id = str(answer_data['question_id'])
                if question_id not in question_dict:
                    continue
                
                question = question_dict[question_id]
                selected_index = answer_data['selected_option_index']
                is_correct = selected_index == question.correct_answer_index
                
                answer_result = {
                    'question_id': question_id,
                    'selected_option_index': selected_index,
                    'correct_answer_index': question.correct_answer_index,
                    'is_correct': is_correct,
                    'explanation': question.explanation or '',
                }
                existing_answers[question_id] = answer_result
            
            answer_results = list(existing_answers.values())
        else:
            # New submission
            for answer_data in answers_data:
                question_id = str(answer_data['question_id'])
                if question_id not in question_dict:
                    continue
                
                question = question_dict[question_id]
                selected_index = answer_data['selected_option_index']
                is_correct = selected_index == question.correct_answer_index
                
                answer_results.append({
                    'question_id': question_id,
                    'selected_option_index': selected_index,
                    'correct_answer_index': question.correct_answer_index,
                    'is_correct': is_correct,
                    'explanation': question.explanation or '',
                })
        
        # Calculate score
        correct_count = sum(1 for a in answer_results if a.get('is_correct', False))
        total_questions_answered = len(answer_results)
        is_final_submission = is_complete or (total_questions_answered >= total_questions_in_section)
        
        total_questions_for_score = total_questions_in_section if is_final_submission else total_questions_answered
        score = int((correct_count / total_questions_for_score * 100)) if total_questions_for_score > 0 else 0
        
        # Update or create attempt record
        attempt = None
        if user:
            if in_progress_attempt and not is_final_submission:
                # Update existing in-progress attempt
                in_progress_attempt.answers_data = answer_results
                in_progress_attempt.correct_count = correct_count
                in_progress_attempt.total_questions = total_questions_answered
                in_progress_attempt.time_spent_seconds = time_spent
                in_progress_attempt.save()
                attempt = in_progress_attempt
            elif in_progress_attempt:
                # Finalize existing attempt
                in_progress_attempt.score = score
                in_progress_attempt.correct_count = correct_count
                in_progress_attempt.total_questions = total_questions_in_section
                in_progress_attempt.answers_data = answer_results
                in_progress_attempt.time_spent_seconds = time_spent
                in_progress_attempt.save()
                attempt = in_progress_attempt
            else:
                # Create new attempt
                attempt = MathSectionAttempt.objects.create(
                    user=user,
                    math_section=math_section,
                    score=score,
                    correct_count=correct_count,
                    total_questions=total_questions_in_section if is_final_submission else total_questions_answered,
                    time_spent_seconds=time_spent,
                    answers_data=answer_results,
                )
        
        response_data = {
            'writing_section_id': str(math_section.id),  # Use writing_section_id to match serializer
            'score': score,
            'total_questions': total_questions_in_section,
            'total_questions_answered': total_questions_answered,
            'correct_count': correct_count,
            'is_completed': is_final_submission,
            'answers': answer_results,
            'completed_at': timezone.now().isoformat() if is_final_submission else None,
            'attempt_id': str(attempt.id) if attempt else None,
        }
        
        # Use the same response serializer as writing sections (it expects writing_section_id)
        serializer = SubmitWritingSectionResponseSerializer(response_data)
        return Response(serializer.data)


class ReviewMathSectionView(APIView):
    """
    View for getting review data for a completed math section.
    GET /progress/math-sections/:math_section_id/review - Get review data
    """
    
    def get(self, request, math_section_id):
        """GET /progress/math-sections/:math_section_id/review"""
        user = get_user_from_request(request)
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(math_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid math section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        math_section = get_object_or_404(MathSection, id=section_uuid)
        
        # Get the most recent attempt for this user and math section
        attempt = None
        if user:
            attempt = MathSectionAttempt.objects.filter(
                user=user,
                math_section=math_section
            ).order_by('-completed_at').first()
        
        # Build review data from the attempt
        review_answers = []
        questions = math_section.questions.all().order_by('order')
        
        correct_count = 0
        total_questions = questions.count()
        
        # Get answers from attempt if available
        attempt_answers = {}
        if attempt and attempt.answers_data:
            for ans in attempt.answers_data:
                attempt_answers[str(ans.get('question_id'))] = ans
        
        for question in questions:
            question_id_str = str(question.id)
            attempt_answer = attempt_answers.get(question_id_str)
            options = [opt.text for opt in question.options.all().order_by('order')]
            
            # Count correct answers
            if attempt_answer and attempt_answer.get('is_correct'):
                correct_count += 1
            
            review_answers.append({
                'question_id': question_id_str,
                'question_text': question.prompt or question.text or '',
                'options': options,
                'selected_option_index': attempt_answer.get('selected_option_index') if attempt_answer else None,
                'correct_answer_index': question.correct_answer_index,
                'is_correct': attempt_answer.get('is_correct', False) if attempt_answer else False,
                'explanation': question.explanation or '',
            })
        
        score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0
        
        response_data = {
            'writing_section_id': str(math_section.id),  # Use writing_section_id to match serializer
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'answers': review_answers,
        }
        
        serializer = ReviewResponseSerializer(response_data)
        return Response(serializer.data)


class MathSectionAttemptsView(APIView):
    """
    View for getting past attempts for a math section.
    GET /progress/math-sections/:math_section_id/attempts - Get all attempts for a math section
    """
    
    def get(self, request, math_section_id):
        """GET /progress/math-sections/:math_section_id/attempts"""
        user = get_user_from_request(request)
        
        if not user:
            return Response(
                {'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required. Please log in.'}},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Convert string to UUID
        try:
            section_uuid = uuid.UUID(str(math_section_id))
        except (ValueError, AttributeError):
            return Response(
                {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid math section ID format'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        math_section = get_object_or_404(MathSection, id=section_uuid)
        
        # Get all attempts for this user and math section
        attempts = MathSectionAttempt.objects.filter(
            user=user,
            math_section=math_section
        ).order_by('-completed_at')
        
        # Convert attempts to serializer format
        attempts_data = []
        for attempt in attempts:
            attempts_data.append({
                'id': attempt.id,
                'writing_section_id': str(attempt.math_section.id),  # Use writing_section_id to match serializer
                'score': attempt.score,
                'correct_count': attempt.correct_count,
                'total_questions': attempt.total_questions,
                'time_spent_seconds': attempt.time_spent_seconds,
                'completed_at': attempt.completed_at,
                'answers': attempt.answers_data or [],
            })
        
        # Use the same serializer as writing sections (they have the same structure)
        serializer = WritingSectionAttemptSerializer(attempts_data, many=True)
        return Response(serializer.data)


class WordOfTheDayView(APIView):
    """
    GET /word-of-the-day - Get today's word of the day
    Generates a new word using AI if one doesn't exist for today
    """
    
    def get(self, request):
        today = date.today()
        
        # Try to get today's word
        word_of_day = WordOfTheDay.objects.filter(date=today).first()
        
        if word_of_day:
            serializer = WordOfTheDaySerializer(word_of_day)
            return Response(serializer.data)
        
        # Generate new word using AI
        try:
            word_data = self._generate_word_with_ai()
            if word_data:
                word_of_day = WordOfTheDay.objects.create(
                    word=word_data['word'],
                    definition=word_data['definition'],
                    synonyms=word_data['synonyms'],
                    example_sentence=word_data['example_sentence'],
                    date=today
                )
                serializer = WordOfTheDaySerializer(word_of_day)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': {'code': 'INTERNAL_ERROR', 'message': 'Failed to generate word of the day'}},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            # Fallback to a default word if AI fails
            return Response(
                {'error': {'code': 'INTERNAL_ERROR', 'message': f'Error generating word: {str(e)}'}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_word_with_ai(self):
        """Generate word of the day using OpenAI"""
        api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            # Fallback: return a default word if no API key
            return {
                'word': 'Eloquent',
                'definition': 'Fluent or persuasive in speaking or writing.',
                'synonyms': ['Articulate', 'Fluent', 'Expressive', 'Well-spoken'],
                'example_sentence': 'The eloquent speaker captivated the audience with her powerful words.'
            }
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = """Generate a SAT-level vocabulary word with the following format (return as JSON):
{
  "word": "the vocabulary word",
  "definition": "a clear, concise definition suitable for SAT prep",
  "synonyms": ["synonym1", "synonym2", "synonym3", "synonym4"],
  "example_sentence": "a sentence demonstrating the word's usage in context"
}

Choose a word that is:
- Appropriate for SAT vocabulary level (not too easy, not too obscure)
- Useful for academic reading comprehension
- Can be clearly defined and has good synonyms

Return ONLY valid JSON, no other text."""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates SAT vocabulary words in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON (might have markdown code blocks)
            if content.startswith('```'):
                # Remove markdown code blocks
                lines = content.split('\n')
                content = '\n'.join([line for line in lines if not line.strip().startswith('```')])
            
            word_data = json.loads(content)
            
            # Validate required fields
            required_fields = ['word', 'definition', 'synonyms', 'example_sentence']
            if all(field in word_data for field in required_fields):
                # Ensure synonyms is a list
                if isinstance(word_data['synonyms'], str):
                    word_data['synonyms'] = [s.strip() for s in word_data['synonyms'].split(',')]
                return word_data
        
        except Exception as e:
            # Fallback on any error
            pass
        
        # Fallback word
        return {
            'word': 'Eloquent',
            'definition': 'Fluent or persuasive in speaking or writing.',
            'synonyms': ['Articulate', 'Fluent', 'Expressive', 'Well-spoken'],
            'example_sentence': 'The eloquent speaker captivated the audience with her powerful words.'
        }


class QuestionClassificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for question classifications.
    GET /classifications - List all classifications
    GET /classifications/:id - Get classification detail
    """
    queryset = QuestionClassification.objects.all()
    serializer_class = QuestionClassificationSerializer
    
    def get_queryset(self):
        queryset = QuestionClassification.objects.all()
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class UserProfileView(APIView):
    """
    Get user profile with strengths and weaknesses analysis.
    GET /profile - Get current user's profile with performance analysis
    """
    
    def get(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get all classifications
        classifications = QuestionClassification.objects.all()
        
        # Analyze performance by classification
        performance_data = []
        
        for classification in classifications:
            # Get passage questions with this classification
            passage_question_ids = list(classification.passage_questions.values_list('id', flat=True))
            
            # Get lesson questions with this classification  
            lesson_question_ids = list(classification.lesson_questions.values_list('id', flat=True))
            
            # Count answers from passage attempts (UserAnswer tracks these)
            passage_answers = UserAnswer.objects.filter(
                user=user,
                question_id__in=passage_question_ids
            )
            passage_correct = passage_answers.filter(is_correct=True).count()
            passage_total = passage_answers.count()
            
            # For lesson questions, we check WritingSectionAttempt and MathSectionAttempt answers_data
            # These store answers as JSON: {question_id, selected_option_index, is_correct, etc.}
            lesson_correct = 0
            lesson_total = 0
            
            # Check writing section attempts
            writing_attempts = WritingSectionAttempt.objects.filter(user=user)
            for attempt in writing_attempts:
                if attempt.answers_data:
                    for answer in attempt.answers_data:
                        q_id = answer.get('question_id')
                        if q_id and str(q_id) in [str(lid) for lid in lesson_question_ids]:
                            lesson_total += 1
                            if answer.get('is_correct'):
                                lesson_correct += 1
            
            # Check math section attempts
            math_attempts = MathSectionAttempt.objects.filter(user=user)
            for attempt in math_attempts:
                if attempt.answers_data:
                    for answer in attempt.answers_data:
                        q_id = answer.get('question_id')
                        if q_id and str(q_id) in [str(lid) for lid in lesson_question_ids]:
                            lesson_total += 1
                            if answer.get('is_correct'):
                                lesson_correct += 1
            
            total_questions = passage_total + lesson_total
            correct_answers = passage_correct + lesson_correct
            
            if total_questions > 0:
                accuracy = (correct_answers / total_questions) * 100
                
                # Define strength (>= 80%) and weakness (<= 50%)
                is_strength = accuracy >= 80 and total_questions >= 3
                is_weakness = accuracy <= 50 and total_questions >= 3
                
                performance_data.append({
                    'classification_id': str(classification.id),
                    'classification_name': classification.name,
                    'category': classification.category,
                    'total_questions': total_questions,
                    'correct_answers': correct_answers,
                    'accuracy': round(accuracy, 1),
                    'is_strength': is_strength,
                    'is_weakness': is_weakness,
                })
        
        # Sort by accuracy
        performance_data.sort(key=lambda x: x['accuracy'], reverse=True)
        
        # Extract strengths and weaknesses
        strengths = [p for p in performance_data if p['is_strength']]
        weaknesses = [p for p in performance_data if p['is_weakness']]
        
        # Get or create study plan
        study_plan, _ = StudyPlan.objects.get_or_create(user=user)
        
        # Get diagnostic tests (reading is a passage, writing/math are lessons)
        reading_diagnostic = Passage.objects.filter(is_diagnostic=True).first()
        writing_diagnostic = Lesson.objects.filter(lesson_type='writing', is_diagnostic=True).first()
        math_diagnostic = Lesson.objects.filter(lesson_type='math', is_diagnostic=True).first()
        
        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'is_premium': user.is_premium or user.has_active_subscription,
            },
            'performance': performance_data,
            'strengths': strengths[:5],  # Top 5 strengths
            'weaknesses': weaknesses[:5],  # Top 5 weaknesses (lowest accuracy)
            'total_classifications_analyzed': len(performance_data),
            'study_plan': {
                'reading': {
                    'diagnostic_completed': study_plan.reading_diagnostic_completed,
                    'diagnostic_passage_id': str(reading_diagnostic.id) if reading_diagnostic else None,
                    'diagnostic_passage_title': reading_diagnostic.title if reading_diagnostic else None,
                    'diagnostic_type': 'passage',
                    'strengths': study_plan.get_strengths('reading'),
                    'weaknesses': study_plan.get_weaknesses('reading'),
                    'improving': study_plan.get_improving('reading'),
                },
                'writing': {
                    'diagnostic_completed': study_plan.writing_diagnostic_completed,
                    'diagnostic_lesson_id': str(writing_diagnostic.id) if writing_diagnostic else None,
                    'diagnostic_lesson_title': writing_diagnostic.title if writing_diagnostic else None,
                    'diagnostic_type': 'lesson',
                    'strengths': study_plan.get_strengths('writing'),
                    'weaknesses': study_plan.get_weaknesses('writing'),
                    'improving': study_plan.get_improving('writing'),
                },
                'math': {
                    'diagnostic_completed': study_plan.math_diagnostic_completed,
                    'diagnostic_lesson_id': str(math_diagnostic.id) if math_diagnostic else None,
                    'diagnostic_lesson_title': math_diagnostic.title if math_diagnostic else None,
                    'diagnostic_type': 'lesson',
                    'strengths': study_plan.get_strengths('math'),
                    'weaknesses': study_plan.get_weaknesses('math'),
                    'improving': study_plan.get_improving('math'),
                },
                'recommended_lessons': [
                    {'id': str(l.id), 'title': l.title, 'lesson_type': l.lesson_type}
                    for l in study_plan.recommended_lessons.all()[:10]
                ],
            },
        })


class DiagnosticSubmitView(APIView):
    """
    Submit diagnostic test results and generate study plan.
    POST /diagnostic/submit - Submit diagnostic answers and generate study plan
    
    For reading: expects passage_id (uses Question model)
    For writing/math: expects lesson_id (uses LessonQuestion model)
    """
    
    def post(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        lesson_id = request.data.get('lesson_id')
        passage_id = request.data.get('passage_id')
        answers = request.data.get('answers', [])  # [{question_id, selected_option_index, is_correct}, ...]
        
        # Get or create study plan
        study_plan, _ = StudyPlan.objects.get_or_create(user=user)
        
        # Handle reading diagnostic (passage-based)
        if passage_id:
            try:
                passage = Passage.objects.get(id=passage_id)
            except Passage.DoesNotExist:
                return Response({'error': 'Passage not found'}, status=status.HTTP_404_NOT_FOUND)
            
            if not passage.is_diagnostic:
                return Response({'error': 'This passage is not a diagnostic test'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate performance by classification using Question model
            performance = {}
            
            for answer in answers:
                question_id = answer.get('question_id')
                is_correct = answer.get('is_correct', False)
                
                try:
                    question = Question.objects.get(id=question_id)
                except Question.DoesNotExist:
                    continue
                
                # Get classifications for this question
                for classification in question.classifications.all():
                    class_id = str(classification.id)
                    
                    if class_id not in performance:
                        performance[class_id] = {
                            'name': classification.name,
                            'correct': 0,
                            'total': 0,
                            'percentage': 0,
                        }
                    
                    performance[class_id]['total'] += 1
                    if is_correct:
                        performance[class_id]['correct'] += 1
            
            # Calculate percentages
            for class_id, data in performance.items():
                if data['total'] > 0:
                    data['percentage'] = round((data['correct'] / data['total']) * 100, 1)
            
            # Update study plan for reading
            study_plan.reading_performance = performance
            study_plan.reading_diagnostic_completed = True
            study_plan.reading_diagnostic_passage = passage
            study_plan.save()
            
            return Response({
                'status': 'success',
                'category': 'reading',
                'performance': performance,
                'strengths': study_plan.get_strengths('reading'),
                'weaknesses': study_plan.get_weaknesses('reading'),
                'improving': study_plan.get_improving('reading'),
            })
        
        # Handle writing/math diagnostic (lesson-based)
        if not lesson_id:
            return Response({'error': 'lesson_id or passage_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not lesson.is_diagnostic:
            return Response({'error': 'This lesson is not a diagnostic test'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate performance by classification
        performance = {}
        
        for answer in answers:
            question_id = answer.get('question_id')
            is_correct = answer.get('is_correct', False)
            
            try:
                question = LessonQuestion.objects.get(id=question_id)
            except LessonQuestion.DoesNotExist:
                continue
            
            # Get classifications for this question
            for classification in question.classifications.all():
                class_id = str(classification.id)
                
                if class_id not in performance:
                    performance[class_id] = {
                        'name': classification.name,
                        'correct': 0,
                        'total': 0,
                        'percentage': 0,
                    }
                
                performance[class_id]['total'] += 1
                if is_correct:
                    performance[class_id]['correct'] += 1
        
        # Calculate percentages
        for class_id, data in performance.items():
            if data['total'] > 0:
                data['percentage'] = round((data['correct'] / data['total']) * 100, 1)
        
        # Update study plan based on lesson type (only writing and math now)
        category = lesson.lesson_type
        if category == 'writing':
            study_plan.writing_performance = performance
            study_plan.writing_diagnostic_completed = True
            study_plan.writing_diagnostic = lesson
        elif category == 'math':
            study_plan.math_performance = performance
            study_plan.math_diagnostic_completed = True
            study_plan.math_diagnostic = lesson
        
        # Find recommended lessons based on weaknesses
        weaknesses = study_plan.get_weaknesses(category)
        weakness_classifications = [w['classification_id'] for w in weaknesses]
        
        if weakness_classifications:
            # Find lessons that cover these classifications
            # (This is a simplified approach - you may want more sophisticated matching)
            recommended = Lesson.objects.filter(
                lesson_type=category,
                is_diagnostic=False,
            ).exclude(id=lesson.id)[:5]
            
            for rec_lesson in recommended:
                study_plan.recommended_lessons.add(rec_lesson)
        
        study_plan.save()
        
        return Response({
            'status': 'success',
            'category': category,
            'performance': performance,
            'strengths': study_plan.get_strengths(category),
            'weaknesses': study_plan.get_weaknesses(category),
            'improving': study_plan.get_improving(category),
        })


class SubmitLessonView(APIView):
    """
    Submit lesson answers and track progress.
    POST /progress/lessons/<lesson_id>/submit
    
    Supports two modes:
    1. Incremental submission: Submit one answer at a time (for immediate feedback)
       - Send single answer in 'answers' array
       - Backend aggregates answers into in-progress attempt
    2. Final submission: Submit all answers at once (when lesson is complete)
       - Send all answers in 'answers' array
       - Set 'is_complete' to true (or backend detects when all questions answered)
       - Backend finalizes the attempt
    
    Request body:
    {
        "answers": [
            {"question_id": "uuid", "selected_option_index": 0},
            ...
        ],
        "time_spent_seconds": 300,
        "is_complete": true  // Optional: explicitly mark as complete
    }
    """
    
    def post(self, request, lesson_id):
        user = get_user_from_request(request)
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)
        
        answers = request.data.get('answers', [])
        time_spent = request.data.get('time_spent_seconds')
        is_complete = request.data.get('is_complete', False)
        
        if not answers:
            return Response({'error': 'No answers provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all questions for this lesson to determine total count
        all_questions = lesson.questions.all().order_by('order')
        total_questions_in_lesson = all_questions.count()
        question_dict = {str(q.id): q for q in all_questions}
        
        # Check if there's an in-progress attempt for this user+lesson
        # Look for the most recent attempt that might be in progress
        in_progress_attempt = None
        if user:
            # Get the most recent attempt for this lesson
            recent_attempts = LessonAttempt.objects.filter(
                user=user,
                lesson=lesson
            ).order_by('-created_at')
            
            if recent_attempts.exists():
                latest_attempt = recent_attempts.first()
                # Check if it's potentially in-progress (has fewer answers than total questions)
                if len(latest_attempt.answers_data) < total_questions_in_lesson:
                    in_progress_attempt = latest_attempt
        
        # Process new answers
        processed_answers = []
        if in_progress_attempt:
            # Merge with existing answers (update if question already answered, add if new)
            existing_answers = {a['question_id']: a for a in in_progress_attempt.answers_data}
            
            for answer in answers:
                question_id = str(answer.get('question_id'))
                selected_index = answer.get('selected_option_index', -1)
                
                try:
                    question = question_dict[question_id]
                    is_correct = selected_index == question.correct_answer_index
                    
                    processed_answer = {
                        'question_id': question_id,
                        'selected_option_index': selected_index,
                        'correct_answer_index': question.correct_answer_index,
                        'is_correct': is_correct,
                    }
                    existing_answers[question_id] = processed_answer
                except (KeyError, LessonQuestion.DoesNotExist):
                    processed_answers.append({
                        'question_id': question_id,
                        'selected_option_index': selected_index,
                        'is_correct': False,
                        'error': 'Question not found'
                    })
            
            # Convert back to list
            processed_answers = list(existing_answers.values())
        else:
            # New submission - process all answers
            for answer in answers:
                question_id = str(answer.get('question_id'))
                selected_index = answer.get('selected_option_index', -1)
                
                try:
                    question = question_dict[question_id]
                    is_correct = selected_index == question.correct_answer_index
                    
                    processed_answers.append({
                        'question_id': question_id,
                        'selected_option_index': selected_index,
                        'correct_answer_index': question.correct_answer_index,
                        'is_correct': is_correct,
                    })
                except (KeyError, LessonQuestion.DoesNotExist):
                    processed_answers.append({
                        'question_id': question_id,
                        'selected_option_index': selected_index,
                        'is_correct': False,
                        'error': 'Question not found'
                    })
        
        # Calculate score based on all processed answers
        correct_count = sum(1 for a in processed_answers if a.get('is_correct', False))
        total_questions_answered = len(processed_answers)
        
        # Determine if this is a complete submission
        # Complete if: explicitly marked, or all questions in lesson are answered
        is_final_submission = is_complete or (total_questions_answered >= total_questions_in_lesson)
        
        # Use total questions in lesson for score calculation (not just answered)
        total_questions_for_score = total_questions_in_lesson if is_final_submission else total_questions_answered
        score = round((correct_count / total_questions_for_score) * 100) if total_questions_for_score > 0 else 0
        
        # Update or create attempt record
        if in_progress_attempt and not is_final_submission:
            # Update existing in-progress attempt
            in_progress_attempt.answers_data = processed_answers
            in_progress_attempt.correct_count = correct_count
            in_progress_attempt.total_questions = total_questions_answered
            if time_spent is not None:
                in_progress_attempt.time_spent_seconds = time_spent
            in_progress_attempt.save()
            attempt = in_progress_attempt
        else:
            # Create new attempt (or finalize existing one)
            if in_progress_attempt:
                # Finalize the existing attempt
                in_progress_attempt.score = score
                in_progress_attempt.correct_count = correct_count
                in_progress_attempt.total_questions = total_questions_in_lesson
                in_progress_attempt.answers_data = processed_answers
                if time_spent is not None:
                    in_progress_attempt.time_spent_seconds = time_spent
                in_progress_attempt.save()
                attempt = in_progress_attempt
            else:
                # Create new attempt
                attempt = LessonAttempt.objects.create(
                    user=user,
                    lesson=lesson,
                    score=score,
                    correct_count=correct_count,
                    total_questions=total_questions_in_lesson if is_final_submission else total_questions_answered,
                    time_spent_seconds=time_spent,
                    answers_data=processed_answers,
                    is_diagnostic_attempt=lesson.is_diagnostic,
                )
        
        # If this is a final submission and a diagnostic, update the study plan
        if is_final_submission and lesson.is_diagnostic and user:
            self._update_study_plan(user, lesson, processed_answers)
        
        return Response({
            'status': 'success',
            'attempt_id': str(attempt.id),
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions_in_lesson,
            'total_questions_answered': total_questions_answered,
            'is_complete': is_final_submission,
            'is_diagnostic': lesson.is_diagnostic,
            'answers': processed_answers,
        })
    
    def _update_study_plan(self, user, lesson, answers):
        """Update study plan with diagnostic results"""
        study_plan, _ = StudyPlan.objects.get_or_create(user=user)
        
        # Calculate performance by classification
        performance = {}
        
        for answer in answers:
            question_id = answer.get('question_id')
            is_correct = answer.get('is_correct', False)
            
            try:
                question = LessonQuestion.objects.get(id=question_id)
            except LessonQuestion.DoesNotExist:
                continue
            
            # Get classifications for this question
            for classification in question.classifications.all():
                class_id = str(classification.id)
                
                if class_id not in performance:
                    performance[class_id] = {
                        'name': classification.name,
                        'correct': 0,
                        'total': 0,
                        'percentage': 0,
                    }
                
                performance[class_id]['total'] += 1
                if is_correct:
                    performance[class_id]['correct'] += 1
        
        # Calculate percentages
        for class_id, data in performance.items():
            if data['total'] > 0:
                data['percentage'] = round((data['correct'] / data['total']) * 100, 1)
        
        # Update study plan based on lesson type (only writing and math - reading uses passages)
        category = lesson.lesson_type
        if category == 'writing':
            study_plan.writing_performance = performance
            study_plan.writing_diagnostic_completed = True
            study_plan.writing_diagnostic = lesson
        elif category == 'math':
            study_plan.math_performance = performance
            study_plan.math_diagnostic_completed = True
            study_plan.math_diagnostic = lesson
        
        study_plan.save()


class ReviewLessonView(APIView):
    """
    Review lesson attempt results.
    GET /progress/lessons/<lesson_id>/review
    """
    
    def get(self, request, lesson_id):
        user = get_user_from_request(request)
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get latest attempt for this user
        attempt = LessonAttempt.objects.filter(
            user=user,
            lesson=lesson
        ).order_by('-completed_at').first()
        
        if not attempt:
            return Response({'error': 'No attempts found for this lesson'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get lesson questions with correct answers
        questions = []
        for q in lesson.questions.all().order_by('order'):
            options = [{'text': opt.text, 'order': opt.order} for opt in q.options.all().order_by('order')]
            
            # Find user's answer for this question
            user_answer = None
            for ans in attempt.answers_data:
                if str(ans.get('question_id')) == str(q.id):
                    user_answer = ans
                    break
            
            questions.append({
                'id': str(q.id),
                'text': q.text,
                'options': options,
                'correct_answer_index': q.correct_answer_index,
                'explanation': q.explanation,
                'user_answer_index': user_answer.get('selected_option_index') if user_answer else None,
                'is_correct': user_answer.get('is_correct') if user_answer else False,
            })
        
        return Response({
            'lesson_id': str(lesson.id),
            'lesson_title': lesson.title,
            'score': attempt.score,
            'correct_count': attempt.correct_count,
            'total_questions': attempt.total_questions,
            'completed_at': attempt.completed_at.isoformat(),
            'questions': questions,
        })


class LessonAttemptsView(APIView):
    """
    Get attempt history for a lesson.
    GET /progress/lessons/<lesson_id>/attempts
    """
    
    def get(self, request, lesson_id):
        user = get_user_from_request(request)
        if not user:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)
        
        attempts = LessonAttempt.objects.filter(
            user=user,
            lesson=lesson
        ).order_by('-completed_at')[:10]
        
        return Response({
            'lesson_id': str(lesson.id),
            'lesson_title': lesson.title,
            'attempts': [
                {
                    'id': str(a.id),
                    'score': a.score,
                    'correct_count': a.correct_count,
                    'total_questions': a.total_questions,
                    'completed_at': a.completed_at.isoformat(),
                    'is_diagnostic_attempt': a.is_diagnostic_attempt,
                }
                for a in attempts
            ]
        })

