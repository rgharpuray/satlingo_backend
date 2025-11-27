import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Passage(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='free')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'passages'
        indexes = [
            models.Index(fields=['difficulty']),
            models.Index(fields=['tier']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    correct_answer_index = models.IntegerField(validators=[MinValueValidator(0)])
    explanation = models.TextField(null=True, blank=True)
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'questions'
        indexes = [
            models.Index(fields=['passage']),
            models.Index(fields=['order']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.passage.title} - Q{self.order}"


class QuestionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    order = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'question_options'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['order']),
        ]
        ordering = ['order']
        unique_together = [['question', 'order']]
    
    def __str__(self):
        return f"{self.question} - Option {self.order}"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.session_token[:8]}..."


class UserProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress', null=True, blank=True)
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_progress'
        indexes = [
            models.Index(fields=['user', 'passage']),
            models.Index(fields=['user']),
            models.Index(fields=['passage']),
        ]
        unique_together = [['user', 'passage']]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.passage.title}"


class UserAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers', null=True, blank=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_option_index = models.IntegerField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_answers'
        indexes = [
            models.Index(fields=['user', 'question']),
            models.Index(fields=['user']),
            models.Index(fields=['question']),
        ]
        unique_together = [['user', 'question']]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.question}"

