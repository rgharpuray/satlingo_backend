import uuid
import threading
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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


class PassageAnnotation(models.Model):
    """
    Annotations for specific text selections in passages.
    Shown AFTER user answers the associated question.
    Annotations are on the passage text but tied to specific questions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='annotations')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='annotations', null=False, blank=False)
    start_char = models.IntegerField(validators=[MinValueValidator(0)])  # Start character position
    end_char = models.IntegerField(validators=[MinValueValidator(0)])  # End character position (exclusive)
    selected_text = models.TextField()  # The actual selected text (for reference)
    explanation = models.TextField()  # Explanation/comment for this selection
    order = models.IntegerField(default=0)  # Order for display (if multiple annotations for same question)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'passage_annotations'
        indexes = [
            models.Index(fields=['passage']),
            models.Index(fields=['question']),
            models.Index(fields=['start_char', 'end_char']),
        ]
        ordering = ['question__order', 'start_char']  # Order by question order, then position in text
    
    def __str__(self):
        question_ref = f"Q{self.question.order}" if self.question else "General"
        return f"{self.passage.title} - {question_ref} - {self.selected_text[:30]}..."
    
    def clean(self):
        """Validate that end_char > start_char and positions are within passage length"""
        from django.core.exceptions import ValidationError
        if not self.question:
            raise ValidationError('Question is required for annotations')
        if self.end_char <= self.start_char:
            raise ValidationError('End character must be greater than start character')
        if self.passage and self.passage.content:
            if self.end_char > len(self.passage.content):
                raise ValidationError(f'End character ({self.end_char}) exceeds passage length ({len(self.passage.content)})')
        # Ensure question belongs to the same passage
        if self.question and self.passage:
            if self.question.passage != self.passage:
                raise ValidationError('Question must belong to the same passage')
    
    def save(self, *args, **kwargs):
        """Auto-populate selected_text if not provided"""
        if not self.selected_text and self.passage and self.passage.content:
            self.selected_text = self.passage.content[self.start_char:self.end_char]
        self.full_clean()
        super().save(*args, **kwargs)


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
    is_premium = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email
    
    @property
    def has_active_subscription(self):
        """Check if user has an active premium subscription"""
        return self.subscriptions.filter(status='active').exists()


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_subscription_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.status}"
    
    def is_active(self):
        """Check if subscription is currently active"""
        from django.utils import timezone
        return self.status == 'active' and self.current_period_end > timezone.now()


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


class WordOfTheDay(models.Model):
    """Word of the Day feature for vocabulary building"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    word = models.CharField(max_length=100, unique=True)
    definition = models.TextField()
    synonyms = models.JSONField(default=list)  # List of synonym strings
    example_sentence = models.TextField()
    date = models.DateField(unique=True)  # One word per day
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'word_of_the_day'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.word} - {self.date}"


class PassageIngestion(models.Model):
    """Track passage ingestion from files/screenshots"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)  # Primary file name or combined name
    file_path = models.CharField(max_length=500)  # Primary file path (for backward compatibility)
    file_paths = models.JSONField(default=list, blank=True)  # Multiple file paths (for screenshots of same document)
    file_type = models.CharField(max_length=50)  # image, pdf, etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extracted_text = models.TextField(null=True, blank=True)  # OCR/extracted text (combined from all files)
    error_message = models.TextField(null=True, blank=True)
    created_passage = models.ForeignKey(Passage, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'passage_ingestions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


@receiver(post_save, sender=PassageIngestion)
def auto_process_ingestion(sender, instance, created, **kwargs):
    """Automatically process ingestion when saved with pending status and files"""
    # Only process if:
    # 1. Has file_path (files are uploaded)
    # 2. Status is pending or failed (check before we update it)
    # 3. Not already processing or completed
    # Use raw status check to avoid signal loop
    if instance.file_path:
        current_status = PassageIngestion.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        if current_status in ['pending', 'failed']:
            # Mark as processing immediately (use update to avoid signal loop)
            PassageIngestion.objects.filter(pk=instance.pk).update(status='processing')
            
            # Process in background thread
            def process_in_background(ingestion_id):
                from django.db import connection
                connection.close()
                from django import db
                db.connections.close_all()
                
                # Import here to avoid circular imports
                from api.admin import process_ingestion
                ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                try:
                    process_ingestion(ingestion)
                except Exception as e:
                    ingestion.status = 'failed'
                    ingestion.error_message = str(e)
                    ingestion.save()
            
            thread = threading.Thread(target=process_in_background, args=(instance.pk,))
            thread.daemon = True
            thread.start()

