import uuid
import logging
import threading
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

logger = logging.getLogger(__name__)


def validate_gcs_icon_url(value):
    """
    Validator that ensures icon URLs are hosted on the approved GCS bucket.
    This prevents arbitrary external URLs from being used for icons.
    """
    from api.constants import GCS_ICON_URL_PREFIX
    if value and not value.startswith(GCS_ICON_URL_PREFIX):
        raise DjangoValidationError(
            f'Icon URL must start with {GCS_ICON_URL_PREFIX}',
            code='invalid_icon_url'
        )


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
    is_diagnostic = models.BooleanField(default=False, help_text="If true, this passage is the diagnostic test for reading")
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='passages', help_text="Header/section this passage belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_gcs_icon_url],
        help_text="URL to passage icon image (256x256 WebP recommended). Must be hosted on GCS bucket."
    )
    icon_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code (e.g., #58CC02)'
        )],
        help_text="Primary accent color for icon/UI (hex format, e.g., #58CC02)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'passages'
        indexes = [
            models.Index(fields=['difficulty']),
            models.Index(fields=['tier']),
            models.Index(fields=['display_order']),
            models.Index(fields=['header']),
            models.Index(fields=['order_within_header']),
        ]
        ordering = ['header', '-order_within_header', '-display_order', '-created_at']
    
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


class QuestionClassification(models.Model):
    """
    Classification/tag for questions to track user strengths and weaknesses.
    Examples: "Grammar - Subject-Verb Agreement", "Reading - Main Idea", "Math - Algebra"
    """
    CATEGORY_CHOICES = [
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('math', 'Math'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Classification name (e.g., 'Subject-Verb Agreement')")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="Which section this classification belongs to")
    description = models.TextField(blank=True, help_text="Optional description of what this classification covers")
    display_order = models.IntegerField(default=0, help_text="Order for display (higher numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'question_classifications'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['display_order']),
        ]
        ordering = ['category', '-display_order', 'name']
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    correct_answer_index = models.IntegerField(validators=[MinValueValidator(0)])
    explanation = models.TextField(null=True, blank=True)
    order = models.IntegerField()
    classifications = models.ManyToManyField(
        QuestionClassification, 
        blank=True, 
        related_name='passage_questions',
        help_text="Classifications/tags for this question (for tracking user strengths/weaknesses)"
    )
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
    premium_granted_directly = models.BooleanField(default=False, help_text="True if premium was granted via promo code (bypasses Stripe sync)")
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True, help_text="Google OAuth ID")
    apple_id = models.CharField(max_length=255, null=True, blank=True, unique=True, help_text="Apple Sign In ID (sub claim from identity token)")
    
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


class AppStoreSubscription(models.Model):
    """
    Track iOS App Store subscriptions (StoreKit 2).
    Apple requires in-app purchases for iOS apps.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('in_billing_retry', 'In Billing Retry'),
        ('in_grace_period', 'In Grace Period'),
        ('revoked', 'Revoked'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appstore_subscriptions')
    original_transaction_id = models.CharField(max_length=255, unique=True, help_text="Apple's original transaction ID")
    product_id = models.CharField(max_length=255, help_text="Apple product ID (e.g., 'com.keuvi.premium.monthly')")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    purchase_date = models.DateTimeField(help_text="Original purchase date")
    expires_date = models.DateTimeField(help_text="Current expiration date")
    is_in_intro_offer = models.BooleanField(default=False)
    is_upgraded = models.BooleanField(default=False)
    environment = models.CharField(max_length=20, default='Production', help_text="Sandbox or Production")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appstore_subscriptions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['original_transaction_id']),
            models.Index(fields=['expires_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product_id} - {self.status}"
    
    def is_active(self):
        """Check if subscription is currently active"""
        from django.utils import timezone
        return self.status == 'active' and self.expires_date > timezone.now()


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
        # Removed unique_together to allow multiple attempts
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.passage.title}"


class PassageAttempt(models.Model):
    """Store individual attempts at passages with full answer details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passage_attempts', null=True, blank=True)
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    correct_count = models.IntegerField()
    total_questions = models.IntegerField()
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    # Store answers as JSON for full history
    answers_data = models.JSONField(default=list)  # List of {question_id, selected_option_index, is_correct, etc.}
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'passage_attempts'
        indexes = [
            models.Index(fields=['user', 'passage']),
            models.Index(fields=['user']),
            models.Index(fields=['passage']),
            models.Index(fields=['completed_at']),
        ]
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.passage.title} - {self.score}% ({self.completed_at})"


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
            models.Index(fields=['answered_at']),
        ]
        # Removed unique_together to allow multiple attempts per question
    
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
    parsed_data = models.JSONField(null=True, blank=True)  # Store parsed JSON data
    error_message = models.TextField(null=True, blank=True)
    created_passage = models.ForeignKey(Passage, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'passage_ingestions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class Lesson(models.Model):
    """Lessons with structured content chunks and embedded questions"""
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]
    
    LESSON_TYPE_CHOICES = [
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('math', 'Math'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier from JSON (e.g., 'commas')")
    title = models.CharField(max_length=255)
    chunks = models.JSONField(default=list, help_text="Structured content chunks from JSON")
    content = models.TextField(blank=True, help_text="Rendered/flattened content for display")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='free')
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPE_CHOICES, default='reading', help_text="Category: reading, writing, or math")
    is_diagnostic = models.BooleanField(default=False, help_text="If true, this lesson is the diagnostic test for its lesson_type (only one per type)")
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons', help_text="Header/section this lesson belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_gcs_icon_url],
        help_text="URL to lesson icon image (256x256 WebP recommended). Must be hosted on GCS bucket."
    )
    icon_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code (e.g., #58CC02)'
        )],
        help_text="Primary accent color for icon/UI (hex format, e.g., #58CC02)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lessons'
        indexes = [
            models.Index(fields=['lesson_id']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['tier']),
            models.Index(fields=['lesson_type']),
            models.Index(fields=['display_order']),
            models.Index(fields=['header']),
            models.Index(fields=['order_within_header']),
        ]
        ordering = ['header', '-order_within_header', '-display_order', '-created_at']
    
    def __str__(self):
        return self.title


class Header(models.Model):
    """Headers/sections that group lessons and sections/passages (like chapters in a book)"""
    CATEGORY_CHOICES = [
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('math', 'Math'),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('lesson', 'Lesson'),
        ('section', 'Section/Passage'),
        ('both', 'Both'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text="Header title (e.g., 'Algebra Basics', 'Grammar Rules')")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="Category this header belongs to")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='both', help_text="Type of content this header is for: lessons, sections/passages, or both")
    display_order = models.IntegerField(default=0, help_text="Order for display within category (higher numbers appear first)")
    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_gcs_icon_url],
        help_text="URL to header/unit icon image (256x256 WebP recommended). Must be hosted on GCS bucket."
    )
    background_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code (e.g., #1CB0F6)'
        )],
        help_text="Header background/accent color (hex format, e.g., #1CB0F6)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'headers'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['display_order']),
        ]
        ordering = ['category', '-display_order', 'title']
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"


# Proxy models for category-specific admin views
class ReadingLesson(Lesson):
    class Meta:
        proxy = True
        verbose_name = "Reading Lesson"
        verbose_name_plural = "Reading Lessons"


class WritingLesson(Lesson):
    class Meta:
        proxy = True
        verbose_name = "Writing Lesson"
        verbose_name_plural = "Writing Lessons"


class MathLesson(Lesson):
    class Meta:
        proxy = True
        verbose_name = "Math Lesson"
        verbose_name_plural = "Math Lessons"


class LessonQuestion(models.Model):
    """Questions for lessons - extracted from question chunks"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    text = models.JSONField(default=list, help_text="Array of prompt blocks (paragraph, side_by_side, etc.)")
    correct_answer_index = models.IntegerField(validators=[MinValueValidator(0)])
    explanation = models.JSONField(default=list, null=True, blank=True, help_text="Array of explanation blocks")
    order = models.IntegerField(help_text="Order in the lesson (based on chunk position)")
    chunk_index = models.IntegerField(help_text="Index of the question chunk in the chunks array")
    classifications = models.ManyToManyField(
        QuestionClassification, 
        blank=True, 
        related_name='lesson_questions',
        help_text="Classifications/tags for this question (for tracking user strengths/weaknesses)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lesson_questions'
        indexes = [
            models.Index(fields=['lesson']),
            models.Index(fields=['order']),
            models.Index(fields=['chunk_index']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.lesson.title} - Q{self.order}"


class LessonQuestionOption(models.Model):
    """Options for lesson questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(LessonQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    order = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lesson_question_options'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['order']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question} - Option {self.order}"


class LessonAsset(models.Model):
    """Shared assets (diagrams, images) for lessons"""
    ASSET_TYPE_CHOICES = [
        ('image', 'Image'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assets')
    asset_id = models.CharField(max_length=255, help_text="Unique identifier from JSON (e.g., 'diagram-1')")
    type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES, default='image')
    s3_url = models.URLField(max_length=500, help_text="Public S3 URL for the asset")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lesson_assets'
        indexes = [
            models.Index(fields=['lesson']),
            models.Index(fields=['asset_id']),
        ]
        unique_together = [['lesson', 'asset_id']]
    
    def __str__(self):
        return f"{self.lesson.title} - {self.asset_id}"


class LessonQuestionAsset(models.Model):
    """Many-to-many relationship between lesson questions and assets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(LessonQuestion, on_delete=models.CASCADE, related_name='question_assets')
    asset = models.ForeignKey(LessonAsset, on_delete=models.CASCADE, related_name='question_references')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lesson_question_assets'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['asset']),
        ]
        unique_together = [['question', 'asset']]
    
    def __str__(self):
        return f"{self.question} - {self.asset.asset_id}"


class LessonAttempt(models.Model):
    """Store individual attempts at lessons with full answer details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_attempts', null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    correct_count = models.IntegerField()
    total_questions = models.IntegerField()
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    # Store answers as JSON for full history
    # Format: [{question_id, selected_option_index, is_correct}, ...]
    answers_data = models.JSONField(default=list)
    # Track if this was a diagnostic attempt
    is_diagnostic_attempt = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lesson_attempts'
        indexes = [
            models.Index(fields=['user', 'lesson']),
            models.Index(fields=['user']),
            models.Index(fields=['lesson']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['is_diagnostic_attempt']),
        ]
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.lesson.title} - {self.score}% ({self.completed_at})"


class LessonIngestion(models.Model):
    """Track lesson ingestion from JSON files"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parsed_data = models.JSONField(null=True, blank=True)  # Store parsed JSON data
    error_message = models.TextField(null=True, blank=True)
    created_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lesson_ingestions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class WritingSection(models.Model):
    """Writing sections similar to passages but with underlined text selections"""
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
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='writing_sections', help_text="Header/section this writing section belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_gcs_icon_url],
        help_text="URL to writing section icon image (256x256 WebP recommended). Must be hosted on GCS bucket."
    )
    icon_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code (e.g., #58CC02)'
        )],
        help_text="Primary accent color for icon/UI (hex format, e.g., #58CC02)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_sections'
        indexes = [
            models.Index(fields=['difficulty']),
            models.Index(fields=['tier']),
            models.Index(fields=['display_order']),
            models.Index(fields=['header']),
            models.Index(fields=['order_within_header']),
        ]
        ordering = ['header', '-order_within_header', '-display_order', '-created_at']
    
    def __str__(self):
        return self.title


class WritingSectionSelection(models.Model):
    """Underlined text selections in writing sections with numbers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    writing_section = models.ForeignKey(WritingSection, on_delete=models.CASCADE, related_name='selections')
    number = models.IntegerField(validators=[MinValueValidator(1)], help_text="The number shown next to the underlined text (e.g., [1])")
    start_char = models.IntegerField(validators=[MinValueValidator(0)], help_text="Start character position in content")
    end_char = models.IntegerField(validators=[MinValueValidator(0)], help_text="End character position (exclusive)")
    selected_text = models.TextField(help_text="The actual underlined text")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_section_selections'
        indexes = [
            models.Index(fields=['writing_section']),
            models.Index(fields=['number']),
            models.Index(fields=['start_char', 'end_char']),
        ]
        ordering = ['number', 'start_char']
    
    def __str__(self):
        return f"{self.writing_section.title} - [{self.number}] {self.selected_text[:30]}..."
    
    def clean(self):
        """Validate that end_char > start_char and positions are within content length"""
        from django.core.exceptions import ValidationError
        if self.end_char <= self.start_char:
            raise ValidationError('End character must be greater than start character')
        if self.writing_section and self.writing_section.content:
            if self.end_char > len(self.writing_section.content):
                raise ValidationError(f'End character ({self.end_char}) exceeds content length ({len(self.writing_section.content)})')
    
    def save(self, *args, **kwargs):
        """Auto-populate selected_text if not provided"""
        if not self.selected_text and self.writing_section and self.writing_section.content:
            self.selected_text = self.writing_section.content[self.start_char:self.end_char]
        self.full_clean()
        super().save(*args, **kwargs)


class WritingSectionQuestion(models.Model):
    """Questions for writing sections"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    writing_section = models.ForeignKey(WritingSection, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    correct_answer_index = models.IntegerField(validators=[MinValueValidator(0)])
    explanation = models.TextField(null=True, blank=True)
    order = models.IntegerField()
    selection_number = models.IntegerField(null=True, blank=True, help_text="The selection number this question refers to (if any)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_section_questions'
        indexes = [
            models.Index(fields=['writing_section']),
            models.Index(fields=['order']),
            models.Index(fields=['selection_number']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.writing_section.title} - Q{self.order}"


class WritingSectionQuestionOption(models.Model):
    """Options for writing section questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(WritingSectionQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    order = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_section_question_options'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['order']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question} - Option {self.order}"


class WritingSectionIngestion(models.Model):
    """Track writing section ingestion from files"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_type = models.CharField(max_length=50)  # pdf, docx, txt, json
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extracted_text = models.TextField(null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)  # Store parsed JSON data
    error_message = models.TextField(null=True, blank=True)
    created_writing_section = models.ForeignKey(WritingSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_section_ingestions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class WritingSectionAttempt(models.Model):
    """Store individual attempts at writing sections with full answer details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='writing_section_attempts', null=True, blank=True)
    writing_section = models.ForeignKey(WritingSection, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    correct_count = models.IntegerField()
    total_questions = models.IntegerField()
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    # Store answers as JSON for full history
    answers_data = models.JSONField(default=list)  # List of {question_id, selected_option_index, is_correct, etc.}
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_section_attempts'
        indexes = [
            models.Index(fields=['user', 'writing_section']),
            models.Index(fields=['user']),
            models.Index(fields=['writing_section']),
            models.Index(fields=['completed_at']),
        ]
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.writing_section.title} - {self.score}% ({self.completed_at})"


@receiver(post_save, sender=LessonIngestion)
def auto_process_lesson_ingestion(sender, instance, created, **kwargs):
    """Automatically process lesson ingestion when saved with pending status"""
    if created and instance.status == 'pending' and instance.file_path:
        # Mark as processing immediately (use update to avoid signal loop)
        LessonIngestion.objects.filter(pk=instance.pk).update(status='processing')
        
        # Process in background thread
        def process_in_background(ingestion_id):
            import traceback
            from django.db import connection
            connection.close()
            from django import db
            db.connections.close_all()
            from .models import LessonIngestion
            from .lesson_ingestion_utils import process_lesson_ingestion
            ingestion = LessonIngestion.objects.get(pk=ingestion_id)
            try:
                process_lesson_ingestion(ingestion)
            except Exception as e:
                ingestion.status = 'failed'
                ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                ingestion.save()
        
        thread = threading.Thread(target=process_in_background, args=(instance.pk,))
        thread.daemon = True
        thread.start()


@receiver(post_save, sender=PassageIngestion)
def auto_process_ingestion(sender, instance, created, **kwargs):
    """Automatically process ingestion when saved with pending status and files"""
    # Only process if:
    # 1. Has file_path (files are uploaded)
    # 2. Status is pending or failed (check before we update it)
    # 3. Not already processing or completed
    # 4. Does NOT have parsed_data (new JSON-based ingestions are handled in admin.save_model)
    # Use raw status check to avoid signal loop
    if instance.file_path and not instance.parsed_data:
        current_status = PassageIngestion.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        if current_status in ['pending', 'failed']:
            # Mark as processing immediately (use update to avoid signal loop)
            PassageIngestion.objects.filter(pk=instance.pk).update(status='processing')
            
            # Process in background thread
            def process_in_background(ingestion_id):
                import time
                import traceback
                from django.db import connection
                # Small delay to ensure transaction has committed
                time.sleep(0.5)
                connection.close()
                from django import db
                db.connections.close_all()
                
                # Import here to avoid circular imports
                from api.ingestion_utils import process_ingestion
                try:
                    # Try to get the object, with retry logic
                    ingestion = None
                    for attempt in range(3):
                        try:
                            ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                            break
                        except PassageIngestion.DoesNotExist:
                            if attempt < 2:
                                time.sleep(0.5)
                            else:
                                raise
                    
                    if ingestion:
                        # Only use old process_ingestion for backward compatibility (no parsed_data)
                        process_ingestion(ingestion)
                except Exception as e:
                    # Get full traceback for debugging
                    error_trace = traceback.format_exc()
                    try:
                        ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                        ingestion.status = 'failed'
                        ingestion.error_message = f"{str(e)}\n\nTraceback:\n{error_trace}"
                        ingestion.save()
                    except PassageIngestion.DoesNotExist:
                        # Object doesn't exist, can't save error - just log it
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"PassageIngestion {ingestion_id} does not exist. Error was: {str(e)}")
                    except Exception as save_error:
                        # If we can't save the error, log it
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to save error for ingestion {ingestion_id}: {save_error}")
                        logger.error(f"Original error: {error_trace}")
            
            thread = threading.Thread(target=process_in_background, args=(instance.pk,))
            thread.daemon = True
            thread.start()
            
            # Note: On Heroku, daemon threads may be killed when request ends
            # If processing gets stuck, use: heroku run python manage.py process_ingestions --id <id>


# Math Section Models
class MathSection(models.Model):
    """Math sections with questions and shared assets (diagrams)"""
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
    section_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier from JSON (e.g., 'algebra-basics')")
    title = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='free')
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='math_sections', help_text="Header/section this math section belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_gcs_icon_url],
        help_text="URL to math section icon image (256x256 WebP recommended). Must be hosted on GCS bucket."
    )
    icon_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code (e.g., #58CC02)'
        )],
        help_text="Primary accent color for icon/UI (hex format, e.g., #58CC02)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'math_sections'
        indexes = [
            models.Index(fields=['section_id']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['tier']),
            models.Index(fields=['display_order']),
            models.Index(fields=['header']),
            models.Index(fields=['order_within_header']),
        ]
        ordering = ['header', '-order_within_header', '-display_order', '-created_at']
    
    def __str__(self):
        return self.title


class MathAsset(models.Model):
    """Shared assets (diagrams, images) for math sections"""
    ASSET_TYPE_CHOICES = [
        ('image', 'Image'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    math_section = models.ForeignKey(MathSection, on_delete=models.CASCADE, related_name='assets')
    asset_id = models.CharField(max_length=255, help_text="Unique identifier from JSON (e.g., 'diagram-1')")
    type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES, default='image')
    s3_url = models.URLField(max_length=500, help_text="Public S3 URL for the asset")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'math_assets'
        indexes = [
            models.Index(fields=['math_section']),
            models.Index(fields=['asset_id']),
        ]
        unique_together = [['math_section', 'asset_id']]
    
    def __str__(self):
        return f"{self.math_section.title} - {self.asset_id}"


class MathQuestion(models.Model):
    """Questions for math sections"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    math_section = models.ForeignKey(MathSection, on_delete=models.CASCADE, related_name='questions')
    question_id = models.CharField(max_length=255, help_text="Unique identifier from JSON (e.g., 'q1')")
    prompt = models.JSONField(default=list, help_text="Array of prompt blocks (paragraph, side_by_side, etc.)")
    correct_answer_index = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    explanation = models.JSONField(default=list, help_text="Array of explanation blocks")
    order = models.IntegerField(help_text="Order of the question")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'math_questions'
        indexes = [
            models.Index(fields=['math_section']),
            models.Index(fields=['question_id']),
            models.Index(fields=['order']),
        ]
        unique_together = [['math_section', 'question_id']]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.math_section.title} - {self.question_id}"


class MathQuestionOption(models.Model):
    """Options for math questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(MathQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    order = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'math_question_options'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['order']),
        ]
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question} - Option {self.order}"


class MathQuestionAsset(models.Model):
    """Many-to-many relationship between questions and assets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(MathQuestion, on_delete=models.CASCADE, related_name='question_assets')
    asset = models.ForeignKey(MathAsset, on_delete=models.CASCADE, related_name='question_references')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'math_question_assets'
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['asset']),
        ]
        unique_together = [['question', 'asset']]
    
    def __str__(self):
        return f"{self.question} - {self.asset.asset_id}"


class MathSectionIngestion(models.Model):
    """Track math section ingestion from files"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_type = models.CharField(max_length=50)  # pdf, docx, txt, json
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extracted_text = models.TextField(null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)  # Store parsed JSON data
    error_message = models.TextField(null=True, blank=True)
    created_math_section = models.ForeignKey(MathSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'math_section_ingestions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class MathSectionAttempt(models.Model):
    """Store individual attempts at math sections with full answer details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='math_section_attempts', null=True, blank=True)
    math_section = models.ForeignKey(MathSection, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    correct_count = models.IntegerField()
    total_questions = models.IntegerField()
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    # Store answers as JSON for full history
    answers_data = models.JSONField(default=list)  # List of {question_id, selected_option_index, is_correct, etc.}
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'math_section_attempts'
        indexes = [
            models.Index(fields=['user', 'math_section']),
            models.Index(fields=['user']),
            models.Index(fields=['math_section']),
            models.Index(fields=['completed_at']),
        ]
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.math_section.title} - {self.score}% ({self.completed_at})"


class StudyPlan(models.Model):
    """
    User's study plan generated from diagnostic test results.
    Tracks strengths and weaknesses by classification.
    Also tracks onboarding state for penguin-guided onboarding flow.
    """
    # Onboarding state choices
    ONBOARDING_STATE_CHOICES = [
        ('WELCOME', 'Welcome'),
        ('PROFILE_SETUP', 'Profile Setup'),
        ('DIAGNOSTIC_NUDGE', 'Diagnostic Nudge'),
        ('DIAGNOSTIC_IN_PROGRESS', 'Diagnostic In Progress'),
        ('POST_DIAGNOSTIC', 'Post Diagnostic'),
        ('ENGAGED', 'Engaged'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='study_plan')

    # Store performance data by classification as JSON
    # Format: {classification_id: {correct: X, total: Y, percentage: Z}}
    reading_performance = models.JSONField(default=dict, blank=True, help_text="Reading classification performance")
    writing_performance = models.JSONField(default=dict, blank=True, help_text="Writing classification performance")
    math_performance = models.JSONField(default=dict, blank=True, help_text="Math classification performance")

    # Track which diagnostics have been completed
    reading_diagnostic_completed = models.BooleanField(default=False)
    writing_diagnostic_completed = models.BooleanField(default=False)
    math_diagnostic_completed = models.BooleanField(default=False)

    # Store the diagnostic references (reading uses Passage, others use Lesson)
    reading_diagnostic_passage = models.ForeignKey('Passage', on_delete=models.SET_NULL, null=True, blank=True, related_name='reading_study_plans', help_text="Reading diagnostic is a passage")
    writing_diagnostic = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='writing_study_plans')
    math_diagnostic = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='math_study_plans')

    # Recommended lessons based on weaknesses
    recommended_lessons = models.ManyToManyField('Lesson', blank=True, related_name='recommended_for_users')

    # Onboarding state tracking
    onboarding_state = models.CharField(
        max_length=30,
        default='WELCOME',
        choices=ONBOARDING_STATE_CHOICES,
        help_text="Current onboarding state"
    )

    # Track what prompts user has seen/dismissed
    welcome_seen_at = models.DateTimeField(null=True, blank=True, help_text="When user saw the welcome prompt")
    profile_prompt_dismissed_at = models.DateTimeField(null=True, blank=True, help_text="When user dismissed the profile setup prompt")
    diagnostic_prompt_dismissed_at = models.DateTimeField(null=True, blank=True, help_text="When user dismissed the diagnostic nudge prompt")
    post_diagnostic_seen_at = models.DateTimeField(null=True, blank=True, help_text="When user saw the post-diagnostic prompt")

    # Track first practice for "engaged" state
    first_practice_completed_at = models.DateTimeField(null=True, blank=True, help_text="When user completed their first practice session")

    # Quick access flag (computed from above but stored for performance)
    onboarding_completed = models.BooleanField(default=False, help_text="Whether user has completed onboarding")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'study_plans'
    
    def __str__(self):
        return f"Study Plan for {self.user.email}"
    
    def get_strengths(self, category):
        """Get classifications where user scores >= 80%"""
        perf = getattr(self, f'{category}_performance', {})
        strengths = []
        for class_id, data in perf.items():
            if data.get('percentage', 0) >= 80:
                strengths.append({
                    'classification_id': class_id,
                    'name': data.get('name', ''),
                    'percentage': data.get('percentage', 0),
                    'correct': data.get('correct', 0),
                    'total': data.get('total', 0),
                })
        return sorted(strengths, key=lambda x: x['percentage'], reverse=True)
    
    def get_weaknesses(self, category):
        """Get classifications where user scores < 60%"""
        perf = getattr(self, f'{category}_performance', {})
        weaknesses = []
        for class_id, data in perf.items():
            if data.get('percentage', 0) < 60:
                weaknesses.append({
                    'classification_id': class_id,
                    'name': data.get('name', ''),
                    'percentage': data.get('percentage', 0),
                    'correct': data.get('correct', 0),
                    'total': data.get('total', 0),
                })
        return sorted(weaknesses, key=lambda x: x['percentage'])
    
    def get_improving(self, category):
        """Get classifications where user scores 60-79%"""
        perf = getattr(self, f'{category}_performance', {})
        improving = []
        for class_id, data in perf.items():
            pct = data.get('percentage', 0)
            if 60 <= pct < 80:
                improving.append({
                    'classification_id': class_id,
                    'name': data.get('name', ''),
                    'percentage': pct,
                    'correct': data.get('correct', 0),
                    'total': data.get('total', 0),
                })
        return sorted(improving, key=lambda x: x['percentage'], reverse=True)


class DiscountCode(models.Model):
    """
    Represents a discount/promotion code for web subscriptions.
    Syncs with Stripe Coupons and Promotion Codes.

    Location: api/models.py
    Usage: Created/managed via Django admin, automatically syncs to Stripe.
    Related: Used with checkout sessions in api/stripe_views.py
    """

    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage Off'),
        ('amount', 'Fixed Amount Off'),
    ]

    DURATION_CHOICES = [
        ('once', 'Once (first payment only)'),
        ('forever', 'Forever (all recurring payments)'),
        ('repeating', 'Repeating (X months)'),
    ]

    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Customer-facing code (e.g., 'STUDENT20', 'WELCOME')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name for admin reference"
    )

    # Discount configuration
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent'
    )
    percent_off = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentage discount (1-100)"
    )
    amount_off = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Fixed amount off in cents (USD)"
    )

    # Duration settings
    duration = models.CharField(
        max_length=10,
        choices=DURATION_CHOICES,
        default='forever'
    )
    duration_in_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of months (only for 'repeating' duration)"
    )

    # Restrictions
    max_redemptions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total uses (leave blank for unlimited)"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date (leave blank for no expiration)"
    )
    first_time_transaction = models.BooleanField(
        default=False,
        help_text="Only allow for first-time customers"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Direct premium grant (bypasses Stripe)
    grants_premium_directly = models.BooleanField(
        default=False,
        help_text="If True, code grants premium directly without Stripe checkout (e.g., for contests, partnerships)"
    )

    # Stripe references (populated on sync)
    stripe_coupon_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    stripe_promotion_code_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # Usage tracking (updated via webhooks or periodic sync)
    times_redeemed = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discount_codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.code} ({self.percent_off}% off)"
        return f"{self.code} (${self.amount_off / 100:.2f} off)"

    def clean(self):
        """Validate discount configuration"""
        from django.core.exceptions import ValidationError

        if self.discount_type == 'percent' and not self.percent_off:
            raise ValidationError('Percentage off is required for percent discount type')
        if self.discount_type == 'amount' and not self.amount_off:
            raise ValidationError('Amount off is required for fixed amount discount type')
        if self.duration == 'repeating' and not self.duration_in_months:
            raise ValidationError('Duration in months is required for repeating duration')

    def is_valid(self):
        """Check if code is currently valid for use"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_redemptions and self.times_redeemed >= self.max_redemptions:
            return False
        return True


@receiver(post_save, sender=DiscountCode)
def sync_discount_code_to_stripe(sender, instance, created, **kwargs):
    """Sync discount code to Stripe on save"""
    from .discount_sync import DiscountSyncService

    # Skip Stripe sync for codes that grant premium directly
    if instance.grants_premium_directly:
        logger.info(f"Skipping Stripe sync for direct premium code '{instance.code}'")
        return

    try:
        if created:
            # New code - create in Stripe
            logger.info(f"Creating discount code '{instance.code}' in Stripe")
            coupon_id, promo_id = DiscountSyncService.create_in_stripe(instance)
            # Update without triggering signal again
            DiscountCode.objects.filter(pk=instance.pk).update(
                stripe_coupon_id=coupon_id,
                stripe_promotion_code_id=promo_id
            )
            logger.info(f"Discount code '{instance.code}' synced to Stripe: coupon={coupon_id}, promo={promo_id}")
        else:
            # Existing code - update active status in Stripe
            logger.info(f"Updating discount code '{instance.code}' in Stripe")
            DiscountSyncService.update_in_stripe(instance)
            logger.info(f"Discount code '{instance.code}' updated in Stripe")
    except Exception as e:
        logger.error(f"Failed to sync discount code '{instance.code}' to Stripe: {str(e)}", exc_info=True)
        # Don't re-raise - allow the model save to complete even if Stripe sync fails
        # Admin can manually retry or check Stripe dashboard


@receiver(pre_delete, sender=DiscountCode)
def deactivate_discount_code_in_stripe(sender, instance, **kwargs):
    """Deactivate promotion code in Stripe before deletion"""
    from .discount_sync import DiscountSyncService

    try:
        logger.info(f"Deactivating discount code '{instance.code}' in Stripe before deletion")
        DiscountSyncService.deactivate_in_stripe(instance)
        logger.info(f"Discount code '{instance.code}' deactivated in Stripe")
    except Exception as e:
        logger.error(f"Failed to deactivate discount code '{instance.code}' in Stripe: {str(e)}", exc_info=True)
        # Don't re-raise - allow deletion to proceed

