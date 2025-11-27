from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
import nested_admin
from .models import Passage, Question, QuestionOption, User, UserSession, UserProgress, UserAnswer


class QuestionOptionInline(nested_admin.NestedTabularInline):
    """Inline editor for question options"""
    model = QuestionOption
    extra = 4  # Show 4 empty option forms by default
    min_num = 2  # Minimum 2 options required
    fields = ('order', 'text')
    ordering = ('order',)
    
    def get_extra(self, request, obj=None, **kwargs):
        """Show 4 options by default, adjust if question exists"""
        if obj and obj.pk:
            # If editing existing question, show only empty forms
            return 0
        return 4


class QuestionInline(nested_admin.NestedStackedInline):
    """Inline editor for questions within a passage"""
    model = Question
    extra = 1  # Show 1 empty question form by default
    fields = ('order', 'text', 'correct_answer_index', 'explanation')
    inlines = [QuestionOptionInline]  # Now we can nest inlines!
    ordering = ('order',)


@admin.register(Passage)
class PassageAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for passages with inline questions and options"""
    list_display = ['title', 'difficulty', 'tier', 'question_count', 'created_at', 'preview_link']
    list_filter = ['difficulty', 'tier', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'content', 'difficulty', 'tier')
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        """Display number of questions for this passage"""
        if obj.pk:
            return obj.questions.count()
        return 0
    question_count.short_description = 'Questions'
    
    def question_count_display(self, obj):
        """Read-only field showing question count"""
        if obj.pk:
            count = obj.questions.count()
            return f"{count} question{'s' if count != 1 else ''}"
        return "Save passage to add questions"
    question_count_display.short_description = 'Question Count'
    
    def preview_link(self, obj):
        """Link to preview the passage"""
        if obj.pk:
            url = reverse('admin:api_passage_change', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">View</a>', url)
        return '-'
    preview_link.short_description = 'Actions'
    
    class Media:
        css = {
            'all': ('admin/css/passage_admin.css',)
        }
        js = ('admin/js/passage_admin.js',)


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for individual questions"""
    list_display = ['short_text', 'passage', 'order', 'correct_answer_index', 'option_count', 'has_explanation']
    list_filter = ['passage', 'order', 'passage__difficulty', 'passage__tier']
    search_fields = ['text', 'passage__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [QuestionOptionInline]
    
    fieldsets = (
        ('Question Information', {
            'fields': ('id', 'passage', 'order', 'text', 'correct_answer_index', 'explanation')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        """Display truncated question text"""
        if obj.text:
            return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
        return '-'
    short_text.short_description = 'Question Text'
    
    def option_count(self, obj):
        """Display number of options"""
        if obj.pk:
            return obj.options.count()
        return 0
    option_count.short_description = 'Options'
    
    def has_explanation(self, obj):
        """Show if explanation exists"""
        return bool(obj.explanation)
    has_explanation.boolean = True
    has_explanation.short_description = 'Has Explanation'


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    """Admin interface for question options"""
    list_display = ['question', 'order', 'short_text', 'is_correct_answer']
    list_filter = ['question__passage', 'order']
    search_fields = ['text', 'question__text', 'question__passage__title']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Option Information', {
            'fields': ('id', 'question', 'order', 'text')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        """Display truncated option text"""
        if obj.text:
            return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
        return '-'
    short_text.short_description = 'Option Text'
    
    def is_correct_answer(self, obj):
        """Show if this is the correct answer"""
        if obj.question and obj.question.pk:
            return obj.order == obj.question.correct_answer_index
        return False
    is_correct_answer.boolean = True
    is_correct_answer.short_description = 'Correct Answer'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for users"""
    list_display = ['email', 'username', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'username']
    readonly_fields = ['id', 'date_joined', 'last_login']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'email', 'username', 'password')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface for user sessions"""
    list_display = ['user', 'session_token_short', 'expires_at', 'is_expired', 'created_at']
    list_filter = ['expires_at', 'created_at']
    search_fields = ['user__email', 'session_token']
    readonly_fields = ['id', 'session_token', 'created_at']
    
    def session_token_short(self, obj):
        """Display shortened session token"""
        if obj.session_token:
            return obj.session_token[:20] + '...'
        return '-'
    session_token_short.short_description = 'Session Token'
    
    def is_expired(self, obj):
        """Check if session is expired"""
        from django.utils import timezone
        if obj.expires_at:
            return timezone.now() > obj.expires_at
        return False
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    """Admin interface for user progress"""
    list_display = ['user', 'passage', 'is_completed', 'score', 'time_spent_display', 'completed_at']
    list_filter = ['is_completed', 'completed_at', 'passage__difficulty', 'passage__tier']
    search_fields = ['user__email', 'passage__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Progress Information', {
            'fields': ('id', 'user', 'passage', 'is_completed', 'score', 'time_spent_seconds', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def time_spent_display(self, obj):
        """Display time spent in readable format"""
        if obj.time_spent_seconds:
            minutes = obj.time_spent_seconds // 60
            seconds = obj.time_spent_seconds % 60
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return '-'
    time_spent_display.short_description = 'Time Spent'


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    """Admin interface for user answers"""
    list_display = ['user', 'question_short', 'selected_option_index', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at', 'question__passage']
    search_fields = ['user__email', 'question__text', 'question__passage__title']
    readonly_fields = ['id', 'answered_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Answer Information', {
            'fields': ('id', 'user', 'question', 'selected_option_index', 'is_correct')
        }),
        ('Metadata', {
            'fields': ('answered_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_short(self, obj):
        """Display truncated question text"""
        if obj.question:
            text = obj.question.text
            return text[:60] + '...' if len(text) > 60 else text
        return '-'
    question_short.short_description = 'Question'
