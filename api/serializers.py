from rest_framework import serializers
from .models import (
    Passage, Question, QuestionOption, User, UserSession,
    UserProgress, UserAnswer, PassageAnnotation, WordOfTheDay,
    Lesson, LessonQuestion, LessonQuestionOption, LessonAsset, LessonQuestionAsset,
    WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption,
    MathSection, MathQuestion, MathQuestionOption, MathAsset, MathQuestionAsset, MathSectionAttempt,
    Header, QuestionClassification
)


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    options_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'options_list', 'correct_answer_index', 
                'explanation', 'order']
    
    def get_options_list(self, obj):
        """Return options as a simple list of strings for API compatibility"""
        return [opt.text for opt in obj.options.all().order_by('order')]


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for questions without correct answers (but includes explanations)"""
    options = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'explanation', 'order']
    
    def get_options(self, obj):
        """Return options as a simple list of strings"""
        return [opt.text for opt in obj.options.all().order_by('order')]


class PassageAnnotationSerializer(serializers.ModelSerializer):
    """Serializer for passage annotations"""
    question_id = serializers.UUIDField(source='question.id', read_only=True, allow_null=True)
    
    class Meta:
        model = PassageAnnotation
        fields = ['id', 'question_id', 'start_char', 'end_char', 'selected_text', 'explanation', 'order']


class HeaderSerializer(serializers.ModelSerializer):
    """Serializer for headers"""
    class Meta:
        model = Header
        fields = ['id', 'title', 'category', 'display_order']


class PassageListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Passage
        fields = ['id', 'title', 'content', 'difficulty', 'tier', 'header', 'order_within_header', 'question_count', 'attempt_count', 'attempt_summary',
                 'created_at', 'updated_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
    def get_attempt_count(self, obj):
        """Get number of attempts for the current user"""
        request = self.context.get('request')
        if request:
            # Use the same method as views to get user (supports JWT)
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                from .models import PassageAttempt
                return PassageAttempt.objects.filter(user=user, passage=obj).count()
        return 0
    
    def get_attempt_summary(self, obj):
        """Get summary of attempts (best score, latest score, recent attempts)"""
        request = self.context.get('request')
        if request:
            # Use the same method as views to get user (supports JWT)
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                from .models import PassageAttempt
                attempts = PassageAttempt.objects.filter(user=user, passage=obj).order_by('-completed_at')
                count = attempts.count()
                
                if count == 0:
                    return None
                
                # Get best and latest scores
                best_attempt = attempts.order_by('-score').first()
                latest_attempt = attempts.first()
                
                # Get recent attempts (last 3)
                recent_attempts = list(attempts[:3].values('id', 'score', 'correct_count', 'total_questions', 'completed_at'))
                
                return {
                    'total_attempts': count,
                    'best_score': best_attempt.score if best_attempt else None,
                    'latest_score': latest_attempt.score if latest_attempt else None,
                    'recent_attempts': recent_attempts
                }
        return None


class PassageDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    annotations = PassageAnnotationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Passage
        fields = ['id', 'title', 'content', 'difficulty', 'tier', 'questions', 'annotations',
                 'created_at', 'updated_at']


class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = ['id', 'passage_id', 'is_completed', 'score', 'time_spent_seconds', 
                 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    passage_id = serializers.UUIDField(source='passage.id', read_only=True)


class UserProgressSummarySerializer(serializers.Serializer):
    completed_passages = serializers.ListField(child=serializers.UUIDField())
    scores = serializers.DictField(child=serializers.IntegerField())
    total_passages = serializers.IntegerField()
    completed_count = serializers.IntegerField()


class UserAnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.UUIDField(source='question.id', read_only=True)
    annotations = serializers.SerializerMethodField()  # Annotations for this question
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question_id', 'selected_option_index', 'is_correct', 
                 'answered_at', 'annotations', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_correct', 'answered_at', 'created_at', 'updated_at']
    
    def get_annotations(self, obj):
        """Get annotations for this question - always return them if they exist"""
        if obj.question:
            # Use prefetched annotations if available, otherwise query
            if hasattr(obj.question, '_prefetched_objects_cache') and 'annotations' in obj.question._prefetched_objects_cache:
                annotations = list(obj.question._prefetched_objects_cache['annotations'])
            else:
                annotations = list(obj.question.annotations.all())
            
            # Order by start_char
            annotations.sort(key=lambda a: a.start_char)
            
            return [
                {
                    'id': str(ann.id),
                    'question_id': str(ann.question_id) if ann.question_id else None,
                    'start_char': ann.start_char,
                    'end_char': ann.end_char,
                    'selected_text': ann.selected_text,
                    'explanation': ann.explanation,
                    'order': ann.order,
                }
                for ann in annotations
            ]
        return []


class SubmitAnswerRequestSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_option_index = serializers.IntegerField(min_value=0)


class SubmitPassageRequestSerializer(serializers.Serializer):
    answers = SubmitAnswerRequestSerializer(many=True)
    time_spent_seconds = serializers.IntegerField(min_value=0, required=False)


class AnswerResultSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_option_index = serializers.IntegerField()
    correct_answer_index = serializers.IntegerField()
    is_correct = serializers.BooleanField()
    explanation = serializers.CharField(allow_null=True)
    annotations = PassageAnnotationSerializer(many=True, required=False)  # Annotations for this question


class SubmitPassageResponseSerializer(serializers.Serializer):
    passage_id = serializers.UUIDField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    answers = AnswerResultSerializer(many=True)
    completed_at = serializers.DateTimeField()
    attempt_id = serializers.UUIDField(allow_null=True)  # ID of the attempt record


class ReviewAnnotationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    start_char = serializers.IntegerField()
    end_char = serializers.IntegerField()
    selected_text = serializers.CharField()
    explanation = serializers.CharField()
    order = serializers.IntegerField()


class ReviewAnswerSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    question_text = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField())
    selected_option_index = serializers.IntegerField(allow_null=True)
    correct_answer_index = serializers.IntegerField()
    is_correct = serializers.BooleanField(allow_null=True)
    explanation = serializers.CharField(allow_null=True)
    annotations = ReviewAnnotationSerializer(many=True, required=False)


class ReviewResponseSerializer(serializers.Serializer):
    passage_id = serializers.UUIDField(required=False, allow_null=True)
    writing_section_id = serializers.UUIDField(required=False, allow_null=True)
    score = serializers.IntegerField(allow_null=True)
    correct_count = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    answers = ReviewAnswerSerializer(many=True)


class PassageAttemptSerializer(serializers.Serializer):
    """Serializer for passage attempt history"""
    id = serializers.UUIDField()
    passage_id = serializers.UUIDField()
    score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    time_spent_seconds = serializers.IntegerField(allow_null=True)
    completed_at = serializers.DateTimeField()
    answers = AnswerResultSerializer(many=True)


# Admin serializers
class CreateQuestionSerializer(serializers.Serializer):
    text = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField(), min_length=2)
    correct_answer_index = serializers.IntegerField(min_value=0)
    explanation = serializers.CharField(allow_null=True, required=False)
    order = serializers.IntegerField(min_value=0)


class CreatePassageSerializer(serializers.Serializer):
    title = serializers.CharField()
    content = serializers.CharField()
    difficulty = serializers.ChoiceField(choices=['Easy', 'Medium', 'Hard'])
    questions = CreateQuestionSerializer(many=True)


class WordOfTheDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WordOfTheDay
        fields = ['id', 'word', 'definition', 'synonyms', 'example_sentence', 'date']


# Lesson serializers
class LessonAssetSerializer(serializers.ModelSerializer):
    """Serializer for lesson assets (diagrams/images)"""
    class Meta:
        model = LessonAsset
        fields = ['id', 'asset_id', 'type', 's3_url']


class LessonQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonQuestionOption
        fields = ['id', 'text', 'order']


class LessonQuestionSerializer(serializers.ModelSerializer):
    options = LessonQuestionOptionSerializer(many=True, read_only=True)
    assets = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonQuestion
        fields = ['id', 'text', 'options', 'correct_answer_index', 'explanation', 'order', 'chunk_index', 'assets']
    
    def get_assets(self, obj):
        """Return assets (diagrams) associated with this question"""
        assets = LessonAsset.objects.filter(
            question_references__question=obj
        ).distinct()
        return LessonAssetSerializer(assets, many=True).data


class LessonListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    header = HeaderSerializer(read_only=True)
    
    class Meta:
        model = Lesson
        fields = ['id', 'lesson_id', 'title', 'difficulty', 'tier', 'question_count', 'header', 'order_within_header', 'created_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()


class LessonDetailSerializer(serializers.ModelSerializer):
    questions = LessonQuestionSerializer(many=True, read_only=True)
    assets = LessonAssetSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lesson
        fields = ['id', 'lesson_id', 'title', 'chunks', 'content', 'difficulty', 'tier', 'questions', 'assets', 'created_at', 'updated_at']


# Writing Section Serializers
class WritingSectionSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WritingSectionSelection
        fields = ['id', 'number', 'start_char', 'end_char', 'selected_text']


class WritingSectionQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WritingSectionQuestionOption
        fields = ['id', 'text', 'order']


class WritingSectionQuestionSerializer(serializers.ModelSerializer):
    options = WritingSectionQuestionOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = WritingSectionQuestion
        fields = ['id', 'text', 'options', 'correct_answer_index', 'explanation', 'order', 'selection_number']


class WritingSectionListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    selection_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = WritingSection
        fields = ['id', 'title', 'difficulty', 'tier', 'header', 'order_within_header', 'question_count', 'selection_count', 
                 'attempt_count', 'attempt_summary', 'created_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
    def get_selection_count(self, obj):
        return obj.selections.count()
    
    def get_attempt_count(self, obj):
        """Get number of attempts for the current user"""
        request = self.context.get('request')
        if request:
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                from .models import WritingSectionAttempt
                return WritingSectionAttempt.objects.filter(user=user, writing_section=obj).count()
        return 0
    
    def get_attempt_summary(self, obj):
        """Get summary of attempts (best score, latest score, recent attempts)"""
        request = self.context.get('request')
        if request:
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                from .models import WritingSectionAttempt
                attempts = WritingSectionAttempt.objects.filter(user=user, writing_section=obj).order_by('-completed_at')
                if attempts.exists():
                    best_attempt = attempts.order_by('-score', '-completed_at').first()
                    latest_attempt = attempts.first()
                    recent_attempts = list(attempts[:3].values('score', 'correct_count', 'total_questions', 'completed_at'))
                    return {
                        'best_score': best_attempt.score if best_attempt else None,
                        'latest_score': latest_attempt.score if latest_attempt else None,
                        'recent_attempts': recent_attempts
                    }
        return None


class WritingSectionDetailSerializer(serializers.ModelSerializer):
    selections = WritingSectionSelectionSerializer(many=True, read_only=True)
    questions = WritingSectionQuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = WritingSection
        fields = ['id', 'title', 'content', 'difficulty', 'tier', 'selections', 'questions', 'created_at', 'updated_at']


class SubmitWritingSectionRequestSerializer(serializers.Serializer):
    """Serializer for submitting writing section answers"""
    answers = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of answer objects with question_id and selected_option_index"
    )
    time_spent_seconds = serializers.IntegerField(required=False, allow_null=True, default=0)


class SubmitWritingSectionResponseSerializer(serializers.Serializer):
    """Serializer for writing section submission response"""
    writing_section_id = serializers.UUIDField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    answers = serializers.ListField()
    completed_at = serializers.DateTimeField()
    attempt_id = serializers.UUIDField(allow_null=True)


class WritingSectionAttemptSerializer(serializers.Serializer):
    """Serializer for writing section attempt history"""
    id = serializers.UUIDField()
    writing_section_id = serializers.UUIDField()
    score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    time_spent_seconds = serializers.IntegerField(allow_null=True)
    completed_at = serializers.DateTimeField()
    answers = serializers.ListField()


# Math Section Serializers
class MathAssetSerializer(serializers.ModelSerializer):
    """Serializer for math assets (diagrams/images)"""
    class Meta:
        model = MathAsset
        fields = ['id', 'asset_id', 'type', 's3_url']


class MathQuestionOptionSerializer(serializers.ModelSerializer):
    """Serializer for math question options"""
    class Meta:
        model = MathQuestionOption
        fields = ['id', 'text', 'order']


class MathQuestionSerializer(serializers.ModelSerializer):
    """Serializer for math questions"""
    options = MathQuestionOptionSerializer(many=True, read_only=True)
    choices = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()
    
    class Meta:
        model = MathQuestion
        fields = ['id', 'question_id', 'prompt', 'choices', 'options', 'correct_answer_index', 
                 'explanation', 'order', 'assets']
    
    def get_choices(self, obj):
        """Return options as a simple list of strings for API compatibility"""
        return [opt.text for opt in obj.options.all().order_by('order')]
    
    def get_assets(self, obj):
        """Return assets (diagrams) associated with this question"""
        assets = MathAsset.objects.filter(
            question_references__question=obj
        ).distinct()
        return MathAssetSerializer(assets, many=True).data


class MathSectionListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = MathSection
        fields = ['id', 'section_id', 'title', 'difficulty', 'tier', 'header', 'order_within_header', 'question_count', 
                 'asset_count', 'attempt_count', 'attempt_summary', 'created_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
    def get_asset_count(self, obj):
        return obj.assets.count()
    
    def get_attempt_count(self, obj):
        """Get number of attempts for the current user"""
        request = self.context.get('request')
        if request:
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                return MathSectionAttempt.objects.filter(user=user, math_section=obj).count()
        return 0
    
    def get_attempt_summary(self, obj):
        """Get summary of attempts (best score, latest score, recent attempts)"""
        request = self.context.get('request')
        if request:
            from .views import get_user_from_request
            user = get_user_from_request(request)
            if user:
                attempts = MathSectionAttempt.objects.filter(user=user, math_section=obj).order_by('-completed_at')
                if attempts.exists():
                    best_attempt = attempts.order_by('-score', '-completed_at').first()
                    latest_attempt = attempts.first()
                    recent_attempts = list(attempts[:3].values('score', 'correct_count', 'total_questions', 'completed_at'))
                    return {
                        'best_score': best_attempt.score if best_attempt else None,
                        'latest_score': latest_attempt.score if latest_attempt else None,
                        'recent_attempts': recent_attempts
                    }
        return None


class MathSectionDetailSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    assets = MathAssetSerializer(many=True, read_only=True)
    
    class Meta:
        model = MathSection
        fields = ['id', 'section_id', 'title', 'difficulty', 'tier', 'questions', 'assets', 
                 'created_at', 'updated_at']
    
    def get_questions(self, obj):
        """Return questions ordered by order field"""
        questions = obj.questions.all().order_by('order')
        return MathQuestionSerializer(questions, many=True).data


class QuestionClassificationSerializer(serializers.ModelSerializer):
    """Serializer for question classifications"""
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QuestionClassification
        fields = ['id', 'name', 'category', 'description', 'display_order', 'question_count']
    
    def get_question_count(self, obj):
        """Total number of questions with this classification"""
        return obj.passage_questions.count() + obj.lesson_questions.count()


class UserStrengthWeaknessSerializer(serializers.Serializer):
    """Serializer for user strengths and weaknesses analysis"""
    classification_id = serializers.UUIDField()
    classification_name = serializers.CharField()
    category = serializers.CharField()
    total_questions = serializers.IntegerField()
    correct_answers = serializers.IntegerField()
    accuracy = serializers.FloatField()
    is_strength = serializers.BooleanField()
    is_weakness = serializers.BooleanField()

