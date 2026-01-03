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
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='passages', help_text="Header/section this passage belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
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
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True, help_text="Google OAuth ID")
    
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
    display_order = models.IntegerField(default=0, help_text="Order for display in admin (higher numbers appear first)")
    header = models.ForeignKey('Header', on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons', help_text="Header/section this lesson belongs to")
    order_within_header = models.IntegerField(default=0, help_text="Order within the header (higher numbers appear first)")
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

