from rest_framework import serializers
from .models import (
    Passage, Question, QuestionOption, User, UserSession,
    UserProgress, UserAnswer
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
    """Serializer for questions without correct answers/explanations"""
    options = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'order']
    
    def get_options(self, obj):
        """Return options as a simple list of strings"""
        return [opt.text for opt in obj.options.all().order_by('order')]


class PassageListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Passage
        fields = ['id', 'title', 'content', 'difficulty', 'tier', 'question_count', 
                 'created_at', 'updated_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()


class PassageDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Passage
        fields = ['id', 'title', 'content', 'difficulty', 'tier', 'questions', 
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
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question_id', 'selected_option_index', 'is_correct', 
                 'answered_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_correct', 'answered_at', 'created_at', 'updated_at']


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


class SubmitPassageResponseSerializer(serializers.Serializer):
    passage_id = serializers.UUIDField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    answers = AnswerResultSerializer(many=True)
    completed_at = serializers.DateTimeField()


class ReviewAnswerSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    question_text = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField())
    selected_option_index = serializers.IntegerField(allow_null=True)
    correct_answer_index = serializers.IntegerField()
    is_correct = serializers.BooleanField()
    explanation = serializers.CharField(allow_null=True)


class ReviewResponseSerializer(serializers.Serializer):
    passage_id = serializers.UUIDField()
    score = serializers.IntegerField(allow_null=True)
    answers = ReviewAnswerSerializer(many=True)


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

