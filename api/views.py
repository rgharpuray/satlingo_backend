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
    Lesson, LessonQuestion, LessonQuestionOption,
    WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption,
    WritingSectionAttempt,
    MathSection, MathQuestion, MathQuestionOption, MathAsset, MathSectionAttempt
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
    MathSectionListSerializer, MathSectionDetailSerializer, MathQuestionSerializer
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
        
        # Get all questions for the writing section
        questions = writing_section.questions.all().order_by('order')
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
        score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0
        
        # Create a new attempt record (for logged-in users only)
        attempt = None
        if user:
            attempt = WritingSectionAttempt.objects.create(
                user=user,
                writing_section=writing_section,
                score=score,
                correct_count=correct_count,
                total_questions=total_questions,
                time_spent_seconds=time_spent,
                answers_data=answer_results,
            )
        
        response_data = {
            'writing_section_id': str(writing_section.id),
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'is_completed': True,
            'answers': answer_results,
            'completed_at': timezone.now().isoformat(),
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
        
        # Get all questions for the math section
        questions = math_section.questions.all().order_by('order')
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
            
            answer_results.append({
                'question_id': question_id,
                'selected_option_index': selected_index,
                'correct_answer_index': question.correct_answer_index,
                'is_correct': is_correct,
                'explanation': question.explanation or '',
            })
        
        # Calculate score
        score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0
        
        # Create a new attempt record (for logged-in users only)
        attempt = None
        if user:
            attempt = MathSectionAttempt.objects.create(
                user=user,
                math_section=math_section,
                score=score,
                correct_count=correct_count,
                total_questions=total_questions,
                time_spent_seconds=time_spent,
                answers_data=answer_results,
            )
        
        response_data = {
            'writing_section_id': str(math_section.id),  # Use writing_section_id to match serializer
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'is_completed': True,
            'answers': answer_results,
            'completed_at': timezone.now().isoformat(),
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
                'completed_at': attempt.completed_at.isoformat(),
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

