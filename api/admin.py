from django.contrib import admin
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Q
import nested_admin
import os
import json
import threading
from django.conf import settings
from .models import Passage, Question, QuestionOption, User, UserSession, UserProgress, UserAnswer, PassageAnnotation, PassageIngestion, Lesson, LessonQuestion, LessonQuestionOption, LessonIngestion, LessonAsset, LessonAttempt, WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption, WritingSectionIngestion, MathSection, MathAsset, MathQuestion, MathQuestionOption, MathQuestionAsset, MathSectionIngestion, ReadingLesson, WritingLesson, MathLesson, Header, Header, Subscription, QuestionClassification, StudyPlan
from .ingestion_utils import (
    extract_text_from_image, extract_text_from_pdf, extract_text_from_multiple_images,
    extract_text_from_docx, extract_text_from_txt, extract_text_from_document,
    parse_passage_with_ai, create_passage_from_parsed_data
)
from .lesson_ingestion_utils import process_lesson_ingestion
from .writing_ingestion_utils import process_writing_ingestion
from .writing_gpt_utils import convert_document_to_writing_json
from .passage_ingestion_utils import process_passage_ingestion
from .passage_gpt_utils import convert_document_to_passage_json
from .math_ingestion_utils import process_math_ingestion
from .math_gpt_utils import convert_document_to_math_json


class MultipleFileInput(forms.Widget):
    """Custom widget for multiple file uploads that bypasses FileInput's multiple restriction"""
    input_type = 'file'
    needs_multipart_form = True
    
    def __init__(self, attrs=None):
        default_attrs = {'multiple': True}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def value_from_datadict(self, data, files, name):
        """Return first file for form validation"""
        if hasattr(files, 'getlist'):
            file_list = files.getlist(name)
            return file_list[0] if file_list else None
        return files.get(name) if files else None
    
    def format_value(self, value):
        """File inputs never have a value"""
        return None
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the file input with multiple attribute"""
        if attrs is None:
            attrs = {}
        
        # Build final attributes - ensure type='file' and multiple are set
        final_attrs = self.build_attrs(self.attrs, extra_attrs=attrs)
        final_attrs['name'] = name
        final_attrs['type'] = 'file'
        final_attrs['multiple'] = True
        # Ensure it's not disabled or readonly
        final_attrs.pop('disabled', None)
        final_attrs.pop('readonly', None)
        
        # Build HTML attributes string - use Django's flatatt equivalent
        from django.forms.utils import flatatt
        html_attrs = flatatt(final_attrs)
        return mark_safe(f'<input{html_attrs} />')


class PassageAnnotationInline(nested_admin.NestedTabularInline):
    """Inline editor for passage annotations"""
    model = PassageAnnotation
    extra = 1  # Show 1 empty annotation form by default
    fields = ('question', 'start_char', 'end_char', 'selected_text', 'explanation', 'order')
    ordering = ('question__order', 'start_char',)
    autocomplete_fields = ['question']  # For easier question selection
    
    def get_formset(self, request, obj=None, **kwargs):
        """Make question field required when creating annotations"""
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['question'].required = True
        return formset
    
    class Media:
        css = {
            'all': ('admin/css/annotation_admin.css',)
        }
        js = ('admin/js/annotation_helper.js',)


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


class PassageAdminForm(forms.ModelForm):
    """Custom form for Passage admin to properly display line breaks"""
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 30,
            'cols': 100,
            'style': 'font-family: monospace; white-space: pre-wrap; font-size: 13px; line-height: 1.5;',
            'wrap': 'off'
        }),
        help_text='Line breaks will be preserved. Use double line breaks (blank lines) for paragraph separation.'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert literal \n strings to actual newlines when displaying
        if self.instance and self.instance.pk and self.instance.content:
            # Replace literal \n (escaped) with actual newlines
            content = self.instance.content
            # Handle both \\n (double escaped) and \n (single escaped) cases
            # Check if content has literal \n strings that need conversion
            if '\\n' in content:
                # Convert literal \n to actual newlines
                # First handle double backslash (\\n -> \n)
                content = content.replace('\\\\n', '\n')
                # Then handle single backslash (\n -> newline)
                content = content.replace('\\n', '\n')
                self.initial['content'] = content
    
    def clean_content(self):
        """Ensure content has actual newlines, not literal \n strings"""
        content = self.cleaned_data.get('content', '')
        if content:
            # Convert any remaining literal \n strings to actual newlines
            # This handles cases where user might paste content with literal \n
            content = content.replace('\\n', '\n')
            # Handle double backslash case
            content = content.replace('\\\\n', '\n')
        return content
    
    class Meta:
        model = Passage
        fields = '__all__'


@admin.register(Passage)
class PassageAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for passages with inline questions, options, and annotations"""
    form = PassageAdminForm
    list_display = ['title', 'difficulty', 'tier', 'is_diagnostic', 'header', 'order_within_header', 'display_order', 'question_count', 'annotation_count', 'created_at', 'preview_link']
    list_filter = ['difficulty', 'tier', 'is_diagnostic', 'header', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display', 'annotation_count_display']
    inlines = [PassageAnnotationInline, QuestionInline]
    actions = ['move_up', 'move_down', 'move_up_in_header', 'move_down_in_header']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter headers by reading category and content_type when assigning to passages"""
        if db_field.name == 'header':
            # Filter headers to only show reading category headers for sections/passages
            kwargs['queryset'] = Header.objects.filter(
                category='reading'
            ).filter(
                Q(content_type='section') | Q(content_type='both')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        """Override queryset to handle missing display_order column gracefully"""
        qs = super().get_queryset(request)
        try:
            # Try to access display_order to see if column exists
            qs.model._meta.get_field('display_order')
        except Exception:
            # Column doesn't exist, defer it to avoid SQL errors
            try:
                return qs.defer('display_order')
            except Exception:
                pass
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamically exclude display_order if column doesn't exist"""
        readonly = ['id', 'created_at', 'updated_at', 'question_count_display', 'annotation_count_display']
        try:
            # Check if display_order field exists
            if obj:
                obj._meta.get_field('display_order')
            elif self.model:
                self.model._meta.get_field('display_order')
        except Exception:
            # Field doesn't exist, don't include it
            pass
        return readonly
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically exclude display_order from fieldsets if column doesn't exist"""
        fieldsets = (
            ('Basic Information', {
                'fields': ('id', 'title', 'content', 'difficulty', 'tier', 'is_diagnostic')
            }),
            ('Metadata', {
                'fields': ('question_count_display', 'annotation_count_display', 'created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )
        try:
            # Check if display_order field exists
            if obj:
                obj._meta.get_field('display_order')
            elif self.model:
                self.model._meta.get_field('display_order')
            # Field exists, add it to fieldsets
            fieldsets = (
                ('Basic Information', {
                    'fields': ('id', 'title', 'content', 'difficulty', 'tier', 'is_diagnostic')
                }),
                ('Organization', {
                    'fields': ('header', 'order_within_header', 'display_order'),
                    'description': 'Assign passage to a header/section and set its order within that header. Only reading category headers will be shown.'
                }),
                ('Metadata', {
                    'fields': ('question_count_display', 'annotation_count_display', 'created_at', 'updated_at'),
                    'classes': ('collapse',)
                }),
            )
        except Exception:
            # Field doesn't exist, use fieldsets without display_order
            pass
        return fieldsets
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'content', 'difficulty', 'tier', 'is_diagnostic')
        }),
        ('Organization', {
            'fields': ('header', 'order_within_header', 'display_order'),
            'description': 'Assign passage to a header/section and set its order within that header. Only reading category headers will be shown.'
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'annotation_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def move_up(self, request, queryset):
        """Move selected items up (increase display_order)"""
        for obj in queryset:
            obj.display_order += 1
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) up.")
    move_up.short_description = "Move up (increase order)"
    
    def move_down(self, request, queryset):
        """Move selected items down (decrease display_order)"""
        for obj in queryset:
            obj.display_order = max(0, obj.display_order - 1)
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) down.")
    move_down.short_description = "Move down (decrease order)"
    
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
    
    def annotation_count(self, obj):
        """Display number of annotations for this passage"""
        if obj.pk:
            return obj.annotations.count()
        return 0
    annotation_count.short_description = 'Annotations'
    
    def annotation_count_display(self, obj):
        """Read-only field showing annotation count"""
        if obj.pk:
            count = obj.annotations.count()
            return f"{count} annotation{'s' if count != 1 else ''}"
        return "Save passage to add annotations"
    annotation_count_display.short_description = 'Annotation Count'
    
    def preview_link(self, obj):
        """Link to preview the passage"""
        if obj.pk:
            url = reverse('admin:api_passage_change', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">View</a>', url)
        return '-'
    preview_link.short_description = 'Actions'
    
    def save_model(self, request, obj, form, change):
        """Ensure only one passage can be diagnostic (for reading)"""
        if obj.is_diagnostic:
            # Unset any other diagnostic passages
            Passage.objects.filter(is_diagnostic=True).exclude(pk=obj.pk).update(is_diagnostic=False)
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/passage_admin.css',)
        }
        js = ('admin/js/passage_admin.js', 'admin/js/annotation_helper.js',)


class BulkClassificationImportForm(forms.Form):
    """Form for bulk importing classifications"""
    category = forms.ChoiceField(choices=QuestionClassification.CATEGORY_CHOICES)
    classifications_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'cols': 80}),
        help_text="Enter one classification name per line"
    )


@admin.register(QuestionClassification)
class QuestionClassificationAdmin(admin.ModelAdmin):
    """Admin interface for question classifications"""
    list_display = ['name', 'category', 'description_short', 'display_order', 'question_count', 'lesson_question_count']
    list_filter = ['category']
    search_fields = ['name', 'description']
    list_editable = ['display_order']
    ordering = ['category', '-display_order', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    change_list_template = 'admin/api/questionclassification/change_list.html'
    
    fieldsets = (
        ('Classification Information', {
            'fields': ('name', 'category', 'description', 'display_order')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('bulk-import/', self.admin_site.admin_view(self.bulk_import_view), name='questionclassification_bulk_import'),
        ]
        return custom_urls + urls
    
    def bulk_import_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        
        if request.method == 'POST':
            form = BulkClassificationImportForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data['category']
                text = form.cleaned_data['classifications_text']
                lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
                
                created_count = 0
                existing_count = 0
                
                for name in lines:
                    # Clean up the name (remove leading dashes, etc.)
                    name = name.lstrip('-').strip()
                    if not name:
                        continue
                    
                    obj, created = QuestionClassification.objects.get_or_create(
                        name=name,
                        defaults={'category': category}
                    )
                    if created:
                        created_count += 1
                    else:
                        existing_count += 1
                
                messages.success(request, f"Created {created_count} new classifications, {existing_count} already existed.")
                return redirect('admin:api_questionclassification_changelist')
        else:
            form = BulkClassificationImportForm()
        
        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Bulk Import Classifications',
            'opts': self.model._meta,
        }
        return render(request, 'admin/api/questionclassification/bulk_import.html', context)
    
    def description_short(self, obj):
        """Truncated description"""
        if obj.description:
            return obj.description[:80] + '...' if len(obj.description) > 80 else obj.description
        return '-'
    description_short.short_description = 'Description'
    
    def question_count(self, obj):
        """Number of passage questions with this classification"""
        return obj.passage_questions.count()
    question_count.short_description = 'Passage Qs'
    
    def lesson_question_count(self, obj):
        """Number of lesson questions with this classification"""
        return obj.lesson_questions.count()
    lesson_question_count.short_description = 'Lesson Qs'


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for individual questions"""
    list_display = ['short_text', 'passage', 'order', 'correct_answer_index', 'option_count', 'has_explanation', 'classification_list']
    list_filter = ['passage', 'order', 'passage__difficulty', 'passage__tier', 'classifications']
    search_fields = ['text', 'passage__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [QuestionOptionInline]
    filter_horizontal = ['classifications']
    
    def get_queryset(self, request):
        """Optimize queryset for list view"""
        return super().get_queryset(request).select_related('passage').prefetch_related('classifications')
    
    fieldsets = (
        ('Question Information', {
            'fields': ('id', 'passage', 'order', 'text', 'correct_answer_index', 'explanation')
        }),
        ('Classifications', {
            'fields': ('classifications',),
            'description': 'Select classifications for this question to track user strengths/weaknesses'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def classification_list(self, obj):
        """Display classifications as comma-separated list"""
        classifications = obj.classifications.all()
        if classifications:
            return ', '.join([c.name for c in classifications])
        return '-'
    classification_list.short_description = 'Classifications'
    
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
    list_display = ['email', 'username', 'is_staff', 'is_active', 'is_premium', 'subscription_status', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'is_premium', 'date_joined']
    search_fields = ['email', 'username']
    readonly_fields = ['id', 'date_joined', 'last_login', 'subscription_status_display']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'email', 'username', 'password')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Subscription', {
            'fields': ('is_premium', 'stripe_customer_id', 'subscription_status_display')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )
    
    def subscription_status(self, obj):
        """Display subscription status in list view"""
        if obj.is_premium:
            return format_html('<span style="color: green;">✓ Premium</span>')
        elif obj.has_active_subscription:
            return format_html('<span style="color: orange;">⚠ Active Sub</span>')
        else:
            return format_html('<span style="color: gray;">Free</span>')
    subscription_status.short_description = 'Subscription'
    subscription_status.boolean = False
    
    def subscription_status_display(self, obj):
        """Display detailed subscription status in detail view"""
        status_parts = []
        
        if obj.is_premium:
            status_parts.append('<strong style="color: green;">Premium: ✓ Enabled</strong>')
        else:
            status_parts.append('<strong style="color: gray;">Premium: ✗ Disabled</strong>')
        
        active_subs = obj.subscriptions.filter(status='active')
        if active_subs.exists():
            status_parts.append(f'<br><strong>Active Subscriptions: {active_subs.count()}</strong>')
            for sub in active_subs[:3]:  # Show up to 3
                status_parts.append(f'<br>  • {sub.stripe_subscription_id} (ends: {sub.current_period_end.strftime("%Y-%m-%d")})')
        else:
            status_parts.append('<br><em>No active subscriptions</em>')
        
        return format_html(''.join(status_parts))
    subscription_status_display.short_description = 'Subscription Details'


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


@admin.register(PassageAnnotation)
class PassageAnnotationAdmin(admin.ModelAdmin):
    """Admin interface for passage annotations"""
    list_display = ['passage', 'question', 'selected_text_short', 'start_char', 'end_char', 'order', 'created_at']
    list_filter = ['passage', 'question', 'created_at']
    search_fields = ['selected_text', 'explanation', 'passage__title', 'question__text']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['question']  # For easier question selection
    
    fieldsets = (
        ('Annotation Information', {
            'fields': ('id', 'passage', 'question', 'start_char', 'end_char', 'selected_text', 'explanation', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def selected_text_short(self, obj):
        """Display truncated selected text"""
        if obj.selected_text:
            return obj.selected_text[:50] + '...' if len(obj.selected_text) > 50 else obj.selected_text
        return '-'
    selected_text_short.short_description = 'Selected Text'


class PassageIngestionForm(forms.ModelForm):
    """Custom form for file upload - supports JSON or documents with GPT conversion"""
    file = forms.FileField(
        required=True,
        help_text="Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT.",
        widget=forms.FileInput(attrs={'accept': '.json,.pdf,.docx,.doc,.txt,application/json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain'})
    )
    use_gpt_conversion = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check this to convert document to JSON using GPT (auto-detected for non-JSON files)"
    )
    
    class Meta:
        model = PassageIngestion
        fields = ['file', 'use_gpt_conversion']
    
    def clean_file(self):
        """Validate uploaded file"""
        data = self.cleaned_data.get('file')
        if data:
            file_ext = os.path.splitext(data.name)[1].lower()
            
            # If it's a JSON file, validate it
            if file_ext == '.json':
                try:
                    data.seek(0)
                    json.loads(data.read().decode('utf-8'))
                    data.seek(0)  # Reset for later use
                except json.JSONDecodeError as e:
                    raise forms.ValidationError(f'Invalid JSON file: {str(e)}')
                except UnicodeDecodeError:
                    raise forms.ValidationError('File must be valid UTF-8 encoded JSON')
            # For other file types, we'll handle them in save_model
            elif file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
                raise forms.ValidationError('File must be JSON (.json), PDF (.pdf), DOCX (.docx), or TXT (.txt)')
        
        return data


@admin.register(PassageIngestion)
class PassageIngestionAdmin(admin.ModelAdmin):
    """Admin interface for passage ingestion"""
    form = PassageIngestionForm
    list_display = ['file_name', 'file_type', 'status', 'created_passage_link', 'created_at', 'process_action']
    list_filter = ['status', 'file_type', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_name', 'file_path', 'file_type', 'extracted_text_preview', 'parsed_data_preview', 'status', 'error_message', 'created_passage_link', 'created_at', 'updated_at']
    actions = ['process_selected']
    
    def get_queryset(self, request):
        """Override queryset to handle missing columns gracefully"""
        qs = super().get_queryset(request)
        # Defer parsed_data to avoid SQL errors if column doesn't exist
        try:
            qs = qs.defer('parsed_data')
        except Exception:
            pass
        
        # Also defer display_order from related Passage model if it doesn't exist
        try:
            from .models import Passage
            Passage._meta.get_field('display_order')
        except Exception:
            # display_order doesn't exist on Passage, use select_related with only() to exclude it
            try:
                qs = qs.select_related('created_passage').only(
                    'id', 'file_name', 'file_path', 'file_paths', 'file_type', 'status',
                    'extracted_text', 'parsed_data', 'error_message', 'created_passage_id',
                    'created_at', 'updated_at',
                    'created_passage__id', 'created_passage__title', 'created_passage__difficulty',
                    'created_passage__tier', 'created_passage__created_at'
                )
            except Exception:
                pass
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamically include parsed_data_preview only if column exists"""
        readonly = ['id', 'file_name', 'file_path', 'file_type', 'extracted_text_preview', 'status', 'error_message', 'created_passage_link', 'created_at', 'updated_at']
        try:
            # Check if we can safely access parsed_data
            if obj and hasattr(obj, 'parsed_data'):
                readonly.insert(5, 'parsed_data_preview')
            elif obj is None:
                # For new objects, include it (will be handled gracefully)
                readonly.insert(5, 'parsed_data_preview')
        except Exception:
            pass
        return readonly
    
    class Media:
        js = ('admin/js/ingestion_admin.js',)
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file', 'use_gpt_conversion'),
            'description': 'Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT. Check "Use GPT conversion" to force GPT conversion even for JSON files.'
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_path', 'error_message')
        }),
        ('Results', {
            'fields': ('extracted_text_preview', 'parsed_data_preview', 'created_passage_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def extracted_text_preview(self, obj):
        """Display preview of extracted text"""
        if obj.extracted_text:
            preview = obj.extracted_text[:500] + '...' if len(obj.extracted_text) > 500 else obj.extracted_text
            return format_html('<pre style="max-height: 200px; overflow: auto;">{}</pre>', preview)
        return '-'
    extracted_text_preview.short_description = 'Extracted Text Preview'
    
    def parsed_data_preview(self, obj):
        """Display preview of parsed JSON data"""
        try:
            # Check if parsed_data field exists and has a value
            if hasattr(obj, 'parsed_data'):
                parsed_data = getattr(obj, 'parsed_data', None)
                if parsed_data:
                    preview = json.dumps(parsed_data, indent=2)[:1000] + '...' if len(json.dumps(parsed_data)) > 1000 else json.dumps(parsed_data, indent=2)
                    return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
        except Exception:
            # Handle case where column doesn't exist in database yet
            pass
        return '-'
    parsed_data_preview.short_description = 'Parsed Data Preview'
    
    def created_passage_link(self, obj):
        """Link to created passage"""
        if obj.created_passage:
            url = reverse('admin:api_passage_change', args=[obj.created_passage.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.created_passage.title)
        return '-'
    created_passage_link.short_description = 'Created Passage'
    
    def process_action(self, obj):
        """Display processing status with a Process Now button for stuck items"""
        if obj.status == 'processing':
            # Show progress message if available, plus a button to restart if stuck
            progress_msg = obj.error_message if obj.error_message and 'Step' in obj.error_message else 'Processing...'
            # Add a button to restart processing if it seems stuck (no passage created)
            if not obj.created_passage:
                restart_url = reverse('admin:api_passageingestion_changelist')
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⏳ {}</span><br>'
                    '<small style="margin-top: 4px; display: block;">'
                    '<a href="#" onclick="processIngestionNow(\'{}\'); return false;" '
                    'style="color: #417690; text-decoration: underline;">🔄 Process Now</a>'
                    '</small>',
                    progress_msg, str(obj.pk)
                )
            return format_html(
                '<span style="color: orange; font-weight: bold;">⏳ {}</span>',
                progress_msg
            )
        elif obj.status == 'completed':
            success_msg = obj.error_message if obj.error_message and '✓' in obj.error_message else 'Completed'
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', success_msg)
        elif obj.status == 'failed':
            error_msg = obj.error_message[:150] + '...' if obj.error_message and len(obj.error_message) > 150 else (obj.error_message or 'Unknown error')
            restart_url = reverse('admin:api_passageingestion_changelist')
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Failed</span><br>'
                '<small style="color: #999; display: block; margin-top: 4px; max-width: 300px;">{}</small><br>'
                '<small style="margin-top: 4px; display: block;">'
                '<a href="#" onclick="processIngestionNow(\'{}\'); return false;" '
                'style="color: #417690; text-decoration: underline;">🔄 Retry</a>'
                '</small>',
                error_msg, str(obj.pk)
            )
        elif obj.status == 'pending' and obj.file_path:
            # Auto-process pending items, but also show a button
            restart_url = reverse('admin:api_passageingestion_changelist')
            return format_html(
                '<span style="color: #666;">Will process automatically...</span><br>'
                '<small style="margin-top: 4px; display: block;">'
                '<a href="#" onclick="processIngestionNow(\'{}\'); return false;" '
                'style="color: #417690; text-decoration: underline;">▶ Process Now</a>'
                '</small>',
                str(obj.pk)
            )
        return '-'
    process_action.short_description = 'Status'
    
    def response_add(self, request, obj, post_url_continue=None):
        """Override to redirect to first ingestion after creation"""
        if hasattr(request, '_ingestion_redirect_id'):
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            url = reverse('admin:api_passageingestion_change', args=[request._ingestion_redirect_id])
            return HttpResponseRedirect(url)
        return super().response_add(request, obj, post_url_continue)
    
    def process_selected(self, request, queryset):
        """Admin action to process selected ingestions - processes asynchronously"""
        # Check if queryset is empty
        if not queryset.exists():
            self.message_user(request, "No ingestions selected. Please check the boxes next to the ingestions you want to process, then select 'Process selected ingestions' from the Action dropdown and click Go.", level='ERROR')
            return
        
        processed = 0
        skipped = 0
        
        def process_in_background(ingestion_id):
            """Process ingestion in background thread"""
            import traceback
            from django.db import connection
            connection.close()
            from django import db
            db.connections.close_all()
            
            try:
                ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                # Use new JSON-based processing if parsed_data exists, otherwise fall back to old method
                if ingestion.parsed_data:
                    process_passage_ingestion(ingestion)
                else:
                    # Fall back to old process_passage_ingestion for backward compatibility
                    process_passage_ingestion(ingestion)
            except Exception as e:
                # Get full traceback for debugging
                error_trace = traceback.format_exc()
                try:
                    ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                    ingestion.status = 'failed'
                    ingestion.error_message = f"{str(e)}\n\nTraceback:\n{error_trace}"
                    ingestion.save()
                except Exception as save_error:
                    # If we can't save the error, log it
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to save error for ingestion {ingestion_id}: {save_error}")
                    logger.error(f"Original error: {error_trace}")
        
        for ingestion in queryset:
            # Process if: pending, failed, or stuck in processing (no passage created)
            if ingestion.file_path:
                # Allow reprocessing if:
                # 1. Status is pending or failed
                # 2. Status is processing but no passage was created (might be stuck)
                if ingestion.status in ['pending', 'failed']:
                    # Mark as processing immediately
                    ingestion.status = 'processing'
                    ingestion.error_message = 'Step 1/4: Starting processing...'
                    ingestion.save()
                    
                    # Process in background thread
                    thread = threading.Thread(target=process_in_background, args=(ingestion.pk,))
                    thread.daemon = True
                    thread.start()
                    processed += 1
                elif ingestion.status == 'processing' and not ingestion.created_passage:
                    # Stuck in processing - reset and reprocess
                    ingestion.status = 'processing'
                    ingestion.error_message = 'Step 1/4: Restarting processing...'
                    ingestion.save()
                    
                    # Process in background thread
                    thread = threading.Thread(target=process_in_background, args=(ingestion.pk,))
                    thread.daemon = True
                    thread.start()
                    processed += 1
                elif ingestion.status == 'completed' and ingestion.created_passage:
                    skipped += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        
        if processed > 0:
            self.message_user(request, f"Started processing {processed} ingestion(s) in the background. The page will refresh automatically to show status updates.", level='SUCCESS')
        elif skipped > 0:
            self.message_user(request, f"No ingestions available to process. {skipped} ingestion(s) were skipped (already completed or missing files).", level='WARNING')
        else:
            self.message_user(request, "No ingestions available to process. Make sure you've selected ingestions and they have uploaded files.", level='WARNING')
    process_selected.short_description = 'Process selected ingestions'
    
    def save_model(self, request, obj, form, change):
        """Override save to handle file upload with GPT conversion"""
        if not change:
            uploaded_file = form.cleaned_data.get('file')
            use_gpt = form.cleaned_data.get('use_gpt_conversion', False)
            
            if uploaded_file:
                import uuid
                from pathlib import Path
                
                # Create media directory if it doesn't exist
                media_dir = Path(settings.MEDIA_ROOT) / 'ingestions'
                media_dir.mkdir(parents=True, exist_ok=True)
                
                # Save file
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = media_dir / unique_filename
                
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                obj.file_name = uploaded_file.name
                obj.file_path = str(file_path)
                obj.file_type = file_ext.lower().lstrip('.')
                
                # Determine if we need GPT conversion
                is_json = file_ext.lower() == '.json'
                is_document = file_ext.lower() in ['.pdf', '.docx', '.doc', '.txt']
                should_use_gpt = use_gpt or (is_document and not is_json)
                
                # Parse JSON or convert document
                try:
                    # Save first to get the ID, but set status to 'processing' to prevent signal handler from running
                    with transaction.atomic():
                        obj.status = 'processing'
                        obj.error_message = 'Processing file...'
                        obj.save()  # Save first to get the ID
                    
                    if is_json:
                        # Direct JSON parsing
                        with open(file_path, 'r', encoding='utf-8') as f:
                            obj.parsed_data = json.load(f)
                        obj.error_message = '✓ Successfully loaded JSON file.'
                    elif should_use_gpt and is_document:
                        # Convert document to JSON using GPT (outside transaction to avoid long-running calls)
                        obj.error_message = 'Converting document to JSON using GPT...'
                        obj.save()
                        
                        # Convert document
                        passage_data = convert_document_to_passage_json(str(file_path), uploaded_file.name)
                        obj.parsed_data = passage_data
                        obj.error_message = f'✓ Successfully converted document to JSON using GPT.'
                    else:
                        raise ValueError(f'Unsupported file type: {file_ext}. Use JSON or enable GPT conversion for documents.')
                except Exception as e:
                    obj.status = 'failed'
                    obj.error_message = f'Failed to process file: {str(e)}'
                
                # Save ingestion with final status
                obj.save()
                
                # Process in background (only if we have parsed_data and didn't fail)
                if obj.status != 'failed' and obj.parsed_data:
                    def process_in_background(ingestion_id):
                        import time
                        import traceback
                        from django.db import connection
                        # Small delay to ensure transaction has committed
                        time.sleep(0.5)
                        connection.close()
                        from django import db
                        db.connections.close_all()
                        from .models import PassageIngestion
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
                                process_passage_ingestion(ingestion)
                        except Exception as e:
                            try:
                                ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                                ingestion.status = 'failed'
                                ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                                ingestion.save()
                            except PassageIngestion.DoesNotExist:
                                # Object doesn't exist, can't save error - just log it
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f"PassageIngestion {ingestion_id} does not exist. Error was: {str(e)}")
                    
                    thread = threading.Thread(target=process_in_background, args=(obj.pk,))
                    thread.daemon = True
                    thread.start()
                    
                    from django.contrib import messages
                    messages.info(request, "Processing started automatically in the background.")
        else:
            super().save_model(request, obj, form, change)


class LessonIngestionForm(forms.ModelForm):
    """Custom form for lesson file upload - supports JSON or documents (PDF, DOCX, TXT) with GPT conversion"""
    file = forms.FileField(
        required=True,
        help_text="Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT.",
        widget=forms.FileInput(attrs={'accept': '.json,.pdf,.docx,.doc,.txt,application/json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain'})
    )
    use_gpt_conversion = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check this to convert document to JSON using GPT (auto-detected for non-JSON files)"
    )
    lesson_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Auto-detect from JSON'), ('reading', 'Reading'), ('writing', 'Writing'), ('math', 'Math')],
        help_text="Set lesson type. If left blank, will use 'lesson_type' from JSON (defaults to 'reading' if not in JSON)."
    )
    
    class Meta:
        model = LessonIngestion
        fields = ['file', 'use_gpt_conversion', 'lesson_type']
    
    def clean_file(self):
        """Validate uploaded file"""
        data = self.cleaned_data.get('file')
        if data:
            file_ext = os.path.splitext(data.name)[1].lower()
            
            # If it's a JSON file, validate it
            if file_ext == '.json':
                try:
                    data.seek(0)
                    json.loads(data.read().decode('utf-8'))
                    data.seek(0)  # Reset for later use
                except json.JSONDecodeError as e:
                    raise forms.ValidationError(f'Invalid JSON file: {str(e)}')
                except UnicodeDecodeError:
                    raise forms.ValidationError('File must be valid UTF-8 encoded JSON')
            # For other file types, we'll handle them in save_model
            elif file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
                raise forms.ValidationError('File must be JSON (.json), PDF (.pdf), DOCX (.docx), or TXT (.txt)')
        
        return data


@admin.register(LessonIngestion)
class LessonIngestionAdmin(admin.ModelAdmin):
    """Admin interface for lesson ingestion from JSON files"""
    form = LessonIngestionForm
    list_display = ['file_name', 'status', 'created_lesson_link', 'created_at', 'process_action']
    list_filter = ['status', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_name', 'file_path', 'status', 'parsed_data_preview', 'error_message', 'created_lesson_link', 'created_at', 'updated_at']
    actions = ['process_selected']
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file', 'use_gpt_conversion', 'lesson_type'),
            'description': 'Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT. Check "Use GPT conversion" to force GPT conversion even for JSON files. Set lesson type here or include it in the JSON as "lesson_type".'
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_path', 'error_message')
        }),
        ('Results', {
            'fields': ('parsed_data_preview', 'created_lesson_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parsed_data_preview(self, obj):
        """Display preview of parsed JSON data"""
        try:
            # Check if parsed_data field exists and has a value
            if hasattr(obj, 'parsed_data'):
                parsed_data = getattr(obj, 'parsed_data', None)
                if parsed_data:
                    preview = json.dumps(parsed_data, indent=2)[:1000] + '...' if len(json.dumps(parsed_data)) > 1000 else json.dumps(parsed_data, indent=2)
                    return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
        except Exception:
            # Handle case where column doesn't exist in database yet
            pass
        return '-'
    parsed_data_preview.short_description = 'Parsed Data Preview'
    
    def created_lesson_link(self, obj):
        """Link to created lesson"""
        if obj.created_lesson:
            url = reverse('admin:api_lesson_change', args=[obj.created_lesson.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_lesson.title)
        return '-'
    created_lesson_link.short_description = 'Created Lesson'
    
    def process_action(self, obj):
        """Display process button for each row"""
        if obj.status in ['pending', 'failed'] or (obj.status == 'processing' and not obj.created_lesson):
            url = reverse('admin:api_lessoningestion_process', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 5px 10px; background: #417690; color: white; text-decoration: none; border-radius: 3px;">Process Now</a>',
                url
            )
        return '-'
    process_action.short_description = 'Actions'
    process_action.allow_tags = True
    
    def process_selected(self, request, queryset):
        """Admin action to process selected ingestions"""
        from .lesson_ingestion_utils import process_lesson_ingestion
        processed = 0
        for ingestion in queryset:
            if ingestion.status in ['pending', 'failed'] or (ingestion.status == 'processing' and not ingestion.created_lesson):
                try:
                    process_lesson_ingestion(ingestion)
                    processed += 1
                except Exception as e:
                    self.message_user(request, f'Error processing {ingestion.file_name}: {str(e)}', level='ERROR')
        
        if processed > 0:
            self.message_user(request, f'Successfully processed {processed} ingestion(s).', level='SUCCESS')
        else:
            self.message_user(request, 'No ingestions to process. Only pending or failed ingestions can be processed.', level='WARNING')
    process_selected.short_description = 'Process selected lesson ingestions'
    
    def get_urls(self):
        """Add custom URL for processing"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:ingestion_id>/process/',
                self.admin_site.admin_view(self.process_ingestion_view),
                name='api_lessoningestion_process',
            ),
        ]
        return custom_urls + urls
    
    def process_ingestion_view(self, request, ingestion_id):
        """Custom view to process a single ingestion"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from .lesson_ingestion_utils import process_lesson_ingestion
        
        ingestion = get_object_or_404(LessonIngestion, pk=ingestion_id)
        
        if ingestion.status not in ['pending', 'failed'] and (ingestion.status != 'processing' or ingestion.created_lesson):
            messages.warning(request, 'This ingestion has already been processed.')
            return redirect('admin:api_lessoningestion_changelist')
        
        try:
            process_lesson_ingestion(ingestion)
            messages.success(request, f'Successfully processed {ingestion.file_name}.')
        except Exception as e:
            messages.error(request, f'Error processing {ingestion.file_name}: {str(e)}')
        
        return redirect('admin:api_lessoningestion_changelist')
    
    def save_model(self, request, obj, form, change):
        """Handle file upload and save ingestion"""
        if not change:  # Only on create
            uploaded_file = request.FILES.get('file')
            use_gpt = form.cleaned_data.get('use_gpt_conversion', False)
            
            if uploaded_file:
                import uuid
                from pathlib import Path
                
                # Create media directory if it doesn't exist
                media_dir = Path(settings.MEDIA_ROOT)
                media_dir.mkdir(parents=True, exist_ok=True)
                
                # Save file
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = media_dir / unique_filename
                
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                obj.file_name = uploaded_file.name
                obj.file_path = str(file_path)
                
                # Determine if we need GPT conversion
                is_json = file_ext.lower() == '.json'
                is_document = file_ext.lower() in ['.pdf', '.docx', '.doc', '.txt']
                should_use_gpt = use_gpt or (is_document and not is_json)
                
                # Save ingestion record first
                obj.status = 'processing'
                obj.error_message = 'Processing file...'
                obj.save()  # Save first to get the ID
                
                # Get lesson_type from form for later use
                lesson_type = form.cleaned_data.get('lesson_type', '').strip()
                
                # Handle JSON files directly (synchronous, fast)
                if is_json:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            obj.parsed_data = json.load(f)
                        
                        # Inject lesson_type from form if provided
                        if lesson_type and obj.parsed_data:
                            obj.parsed_data['lesson_type'] = lesson_type
                        
                        obj.error_message = '✓ Successfully loaded JSON file.'
                        obj.save()
                        
                        # Process in background
                        from .lesson_ingestion_utils import process_lesson_ingestion
                        
                        def process_in_background(ingestion_id):
                            import traceback
                            from django.db import connection
                            connection.close()
                            from django import db
                            db.connections.close_all()
                            from .models import LessonIngestion
                            ingestion = LessonIngestion.objects.get(pk=ingestion_id)
                            try:
                                process_lesson_ingestion(ingestion)
                            except Exception as e:
                                ingestion.status = 'failed'
                                ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                                ingestion.save()
                        
                        # Mark as processing
                        LessonIngestion.objects.filter(pk=obj.pk).update(status='processing')
                        
                        thread = threading.Thread(target=process_in_background, args=(obj.pk,))
                        thread.daemon = True
                        thread.start()
                        
                        from django.contrib import messages
                        messages.info(request, "Processing started automatically in the background.")
                    except Exception as e:
                        import traceback
                        obj.status = 'failed'
                        obj.error_message = f'Failed to process JSON file: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                        obj.save()
                
                # Handle document files with GPT conversion (asynchronous to avoid timeout)
                elif should_use_gpt and is_document:
                    from .lesson_gpt_utils import convert_document_to_lesson_json
                    
                    def convert_and_process_in_background(ingestion_id, file_path_str, file_name, lesson_type_value):
                        import traceback
                        import time
                        from django.db import connection
                        connection.close()
                        from django import db
                        db.connections.close_all()
                        from .models import LessonIngestion
                        from .lesson_ingestion_utils import process_lesson_ingestion
                        
                        # Wait a moment for transaction to commit
                        time.sleep(0.5)
                        
                        ingestion = LessonIngestion.objects.get(pk=ingestion_id)
                        try:
                            # Update status
                            ingestion.error_message = 'Converting document to JSON using GPT...'
                            ingestion.save()
                            
                            # Convert document using GPT
                            lesson_data = convert_document_to_lesson_json(file_path_str, file_name)
                            
                            # Inject lesson_type from form if provided
                            if lesson_type_value and lesson_data:
                                lesson_data['lesson_type'] = lesson_type_value
                            
                            # Update with parsed data
                            ingestion.parsed_data = lesson_data
                            ingestion.error_message = f'✓ Successfully converted document to JSON using GPT.'
                            ingestion.status = 'processing'
                            ingestion.save()
                            
                            # Now process the ingestion
                            process_lesson_ingestion(ingestion)
                        except Exception as e:
                            ingestion.refresh_from_db()
                            ingestion.status = 'failed'
                            ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                            ingestion.save()
                    
                    # Update status and start background thread
                    obj.error_message = 'Converting document to JSON using GPT (this may take a while)...'
                    obj.save()
                    
                    thread = threading.Thread(target=convert_and_process_in_background, args=(obj.pk, str(file_path), uploaded_file.name, lesson_type))
                    thread.daemon = True
                    thread.start()
                    
                    from django.contrib import messages
                    messages.info(request, "File uploaded. GPT conversion and processing started in the background. This may take several minutes.")
                
                else:
                    obj.status = 'failed'
                    obj.error_message = f'Unsupported file type: {file_ext}. Use JSON or enable GPT conversion for documents.'
                    obj.save()
        else:
            super().save_model(request, obj, form, change)


class LessonAssetForm(forms.ModelForm):
    """Custom form for lesson assets with file upload"""
    image_file = forms.FileField(
        required=False,
        help_text="Upload an image file. It will be automatically uploaded to S3 and the S3 URL will be set. Use sentinel format [[Diagram asset_id]] in lesson text.",
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    
    class Meta:
        model = LessonAsset
        fields = ['asset_id', 'type', 'image_file', 's3_url']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make s3_url read-only if it exists
        if self.instance and self.instance.s3_url:
            self.fields['s3_url'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        """Handle image upload and S3 upload"""
        instance = super().save(commit=False)
        
        # Handle file upload if provided
        if 'image_file' in self.cleaned_data and self.cleaned_data['image_file']:
            image_file = self.cleaned_data['image_file']
            
            # Upload to S3
            from .lesson_gpt_utils import upload_lesson_asset_to_s3
            import tempfile
            
            # Save uploaded file temporarily
            file_ext = os.path.splitext(image_file.name)[1].lower()
            if file_ext not in ['.png', '.jpg', '.jpeg', '.svg', '.gif']:
                file_ext = '.png'
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_file.close()
            
            try:
                # Upload to S3
                asset_id = instance.asset_id or os.path.splitext(image_file.name)[0]
                lesson_id = instance.lesson.lesson_id if instance.lesson else 'unknown'
                s3_url = upload_lesson_asset_to_s3(temp_file.name, asset_id, lesson_id)
                instance.s3_url = s3_url
            except Exception as e:
                # Store error in form for display
                self.add_error('image_file', f"Failed to upload image to S3: {str(e)}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        if commit:
            instance.save()
        return instance


class LessonAssetInline(nested_admin.NestedTabularInline):
    """Inline editor for lesson assets (diagrams/images)"""
    model = LessonAsset
    form = LessonAssetForm
    extra = 1
    fields = ('asset_id', 'type', 'image_file', 's3_url', 'preview')
    readonly_fields = ('preview',)
    
    def preview(self, obj):
        """Show preview of the image if S3 URL exists"""
        if obj and obj.s3_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.s3_url)
        return "-"
    preview.short_description = "Preview"


@admin.register(Lesson)
class LessonAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for lessons"""
    list_display = ['title', 'lesson_id', 'lesson_type', 'is_diagnostic', 'header', 'order_within_header', 'difficulty', 'tier', 'question_count', 'created_at']
    list_filter = ['lesson_type', 'is_diagnostic', 'header', 'difficulty', 'tier', 'created_at']
    search_fields = ['title', 'lesson_id', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display', 'edit_chunks_link']
    inlines = [LessonAssetInline]
    actions = ['move_up', 'move_down', 'set_as_reading', 'set_as_writing', 'set_as_math', 'move_up_in_header', 'move_down_in_header']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter headers by lesson type and content_type when assigning to lessons"""
        if db_field.name == 'header':
            # Get the lesson being edited (if any)
            lesson_id = request.resolver_match.kwargs.get('object_id')
            if lesson_id:
                try:
                    lesson = Lesson.objects.get(pk=lesson_id)
                    # Filter headers to only show those matching the lesson's category and for lessons
                    kwargs['queryset'] = Header.objects.filter(
                        category=lesson.lesson_type
                    ).filter(
                        Q(content_type='lesson') | Q(content_type='both')
                    )
                except Lesson.DoesNotExist:
                    pass
            # For new lessons, we can't filter yet - user needs to set lesson_type first
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'lesson_id', 'title', 'lesson_type', 'is_diagnostic', 'difficulty', 'tier')
        }),
        ('Organization', {
            'fields': ('header', 'order_within_header', 'display_order'),
            'description': 'Assign lesson to a header/section and set its order within that header. Only headers matching the lesson type will be shown.'
        }),
        ('Content', {
            'fields': ('edit_chunks_link', 'chunks', 'content'),
            'description': 'Use "Edit Chunks" button above for an easier way to edit chunks and set side-by-side layouts.'
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure only one diagnostic per lesson_type"""
        if obj.is_diagnostic:
            # Unset any other diagnostic lessons of the same type
            Lesson.objects.filter(
                lesson_type=obj.lesson_type, 
                is_diagnostic=True
            ).exclude(pk=obj.pk).update(is_diagnostic=False)
        super().save_model(request, obj, form, change)
    
    def move_up(self, request, queryset):
        """Move selected items up (increase display_order)"""
        for obj in queryset:
            obj.display_order += 1
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) up.")
    move_up.short_description = "Move up (increase order)"
    
    def move_down(self, request, queryset):
        """Move selected items down (decrease display_order)"""
        for obj in queryset:
            obj.display_order = max(0, obj.display_order - 1)
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) down.")
    move_down.short_description = "Move down (decrease order)"
    
    def set_as_reading(self, request, queryset):
        """Set selected lessons as reading type"""
        count = queryset.update(lesson_type='reading')
        self.message_user(request, f"Set {count} lesson(s) as reading.")
    set_as_reading.short_description = "Set as Reading"
    
    def set_as_writing(self, request, queryset):
        """Set selected lessons as writing type"""
        count = queryset.update(lesson_type='writing')
        self.message_user(request, f"Set {count} lesson(s) as writing.")
    set_as_writing.short_description = "Set as Writing"
    
    def set_as_math(self, request, queryset):
        """Set selected lessons as math type"""
        count = queryset.update(lesson_type='math')
        self.message_user(request, f"Set {count} lesson(s) as math.")
    set_as_math.short_description = "Set as Math"
    
    def move_up_in_header(self, request, queryset):
        """Move selected lessons up within their header (increase order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header += 1
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} lesson(s) up within their headers.")
    move_up_in_header.short_description = "Move up within header"
    
    def move_down_in_header(self, request, queryset):
        """Move selected lessons down within their header (decrease order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header = max(0, obj.order_within_header - 1)
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} lesson(s) down within their headers.")
    move_down_in_header.short_description = "Move down within header"
    
    def question_count(self, obj):
        """Display number of questions for this lesson"""
        if obj.pk:
            return obj.questions.count()
        return 0
    question_count.short_description = 'Questions'
    
    def question_count_display(self, obj):
        """Read-only field showing question count"""
        if obj.pk:
            count = obj.questions.count()
            return f"{count} question{'s' if count != 1 else ''}"
        return "Save lesson to see question count"
    question_count_display.short_description = 'Question Count'
    
    def edit_chunks_link(self, obj):
        """Link to user-friendly chunk editor"""
        if obj.pk:
            url = reverse('admin:api_lesson_edit_chunks', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 10px 20px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">📝 Edit Chunks (Easy Mode)</a>',
                url
            )
        return "Save lesson first to edit chunks"
    edit_chunks_link.short_description = 'Edit Chunks'
    edit_chunks_link.allow_tags = True
    
    def get_urls(self):
        """Add custom URL for chunk editor"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:lesson_id>/edit-chunks/',
                self.admin_site.admin_view(self.edit_chunks_view),
                name='api_lesson_edit_chunks',
            ),
        ]
        return custom_urls + urls
    
    def edit_chunks_view(self, request, lesson_id):
        """Custom view for editing chunks with user-friendly interface"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        import json
        
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        
        if request.method == 'POST':
            try:
                chunks_json = request.POST.get('chunks_json')
                if chunks_json:
                    chunks = json.loads(chunks_json)
                    lesson.chunks = chunks
                    # Regenerate content
                    from .lesson_ingestion_utils import _render_lesson_content
                    lesson.content = _render_lesson_content(chunks)
                    lesson.save()
                    messages.success(request, 'Chunks updated successfully!')
                    return redirect('admin:api_lesson_change', lesson_id)
            except Exception as e:
                messages.error(request, f'Error updating chunks: {str(e)}')
        
        # Get available assets for diagram selection
        available_assets = list(lesson.assets.values('asset_id', 's3_url'))
        
        context = {
            'lesson': lesson,
            'chunks_json': mark_safe(json.dumps(lesson.chunks or [])),
            'available_assets': mark_safe(json.dumps(available_assets)),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, lesson),
            'has_change_permission': self.has_change_permission(request, lesson),
        }
        
        return render(request, 'admin/api/lesson_chunks_editor.html', context)


@admin.register(LessonQuestion)
class LessonQuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for lesson questions"""
    list_display = ['text_short', 'lesson', 'order', 'correct_answer_index', 'classification_list', 'edit_prompt_link', 'edit_explanation_link']
    list_filter = ['lesson', 'created_at', 'classifications']
    search_fields = ['lesson__title', 'lesson__lesson_id']
    inlines = []
    readonly_fields = ['edit_prompt_button', 'edit_explanation_button']
    filter_horizontal = ['classifications']
    
    def get_queryset(self, request):
        """Optimize queryset for list view"""
        return super().get_queryset(request).select_related('lesson').prefetch_related('classifications')
    
    fieldsets = (
        ('Question Information', {
            'fields': ('lesson', 'order', 'correct_answer_index', 'chunk_index')
        }),
        ('Classifications', {
            'fields': ('classifications',),
            'description': 'Select classifications for this question to track user strengths/weaknesses'
        }),
        ('Prompt', {
            'fields': ('edit_prompt_button', 'text'),
            'description': 'Click the button below to edit the prompt using the visual editor, or edit the JSON directly in the field below.'
        }),
        ('Explanation', {
            'fields': ('edit_explanation_button', 'explanation'),
            'description': 'Click the button below to edit the explanation using the visual editor, or edit the JSON directly in the field below.'
        }),
    )
    
    def classification_list(self, obj):
        """Display classifications as comma-separated list"""
        classifications = obj.classifications.all()
        if classifications:
            return ', '.join([c.name for c in classifications])
        return '-'
    classification_list.short_description = 'Classifications'
    
    def text_short(self, obj):
        # Handle both JSON array and plain text (for backwards compatibility)
        if isinstance(obj.text, list) and len(obj.text) > 0:
            first_block = obj.text[0]
            if isinstance(first_block, dict) and first_block.get('type') == 'paragraph':
                text = first_block.get('text', '')
            else:
                text = str(first_block)
        else:
            text = str(obj.text) if obj.text else ''
        return text[:100] + '...' if len(text) > 100 else text
    text_short.short_description = 'Question'
    
    def edit_prompt_link(self, obj):
        """Link to user-friendly prompt editor (for list view)"""
        if obj.pk:
            url = reverse('admin:api_lessonquestion_edit_prompt', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 8px 16px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 12px;">📝 Edit Prompt</a>',
                url
            )
        return "Save question first to edit prompt"
    edit_prompt_link.short_description = 'Edit Prompt'
    edit_prompt_link.allow_tags = True
    
    def edit_explanation_link(self, obj):
        """Link to user-friendly explanation editor (for list view)"""
        if obj.pk:
            url = reverse('admin:api_lessonquestion_edit_explanation', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 8px 16px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 12px;">📝 Edit Explanation</a>',
                url
            )
        return "Save question first to edit explanation"
    edit_explanation_link.short_description = 'Edit Explanation'
    edit_explanation_link.allow_tags = True
    
    def edit_prompt_button(self, obj):
        """Button to edit prompt (for detail/edit view)"""
        if obj.pk:
            url = reverse('admin:api_lessonquestion_edit_prompt', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 12px 24px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 14px; margin-bottom: 10px;">📝 Edit Prompt (Easy Mode)</a>',
                url
            )
        return "Save question first to edit prompt"
    edit_prompt_button.short_description = ''
    edit_prompt_button.allow_tags = True
    
    def edit_explanation_button(self, obj):
        """Button to edit explanation (for detail/edit view)"""
        if obj.pk:
            url = reverse('admin:api_lessonquestion_edit_explanation', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 12px 24px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 14px; margin-bottom: 10px;">📝 Edit Explanation (Easy Mode)</a>',
                url
            )
        return "Save question first to edit explanation"
    edit_explanation_button.short_description = ''
    edit_explanation_button.allow_tags = True
    
    def get_urls(self):
        """Add custom URLs for prompt and explanation editors"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:question_id>/edit-prompt/',
                self.admin_site.admin_view(self.edit_prompt_view),
                name='api_lessonquestion_edit_prompt',
            ),
            path(
                '<uuid:question_id>/edit-explanation/',
                self.admin_site.admin_view(self.edit_explanation_view),
                name='api_lessonquestion_edit_explanation',
            ),
        ]
        return custom_urls + urls
    
    def edit_prompt_view(self, request, question_id):
        """Handle the prompt editor page"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        import json
        
        question = get_object_or_404(LessonQuestion, pk=question_id)
        
        if request.method == 'POST':
            try:
                prompt_json = request.POST.get('prompt_json')
                if prompt_json:
                    prompt = json.loads(prompt_json)
                    question.text = prompt
                    question.save()
                    messages.success(request, 'Prompt updated successfully!')
                    return redirect('admin:api_lessonquestion_change', question_id)
            except Exception as e:
                messages.error(request, f'Error updating prompt: {str(e)}')
        
        # Get available assets for diagram selection
        available_assets = list(question.lesson.assets.values('asset_id', 's3_url'))
        
        context = {
            'question': question,
            'prompt_json': mark_safe(json.dumps(question.text or [])),
            'available_assets': mark_safe(json.dumps(available_assets)),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, question),
            'has_change_permission': self.has_change_permission(request, question),
        }
        
        return render(request, 'admin/api/lesson_question_prompt_editor.html', context)
    
    def edit_explanation_view(self, request, question_id):
        """Handle the explanation editor page"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        import json
        
        question = get_object_or_404(LessonQuestion, pk=question_id)
        
        if request.method == 'POST':
            try:
                explanation_json = request.POST.get('explanation_json')
                if explanation_json:
                    explanation = json.loads(explanation_json)
                    question.explanation = explanation
                    question.save()
                    messages.success(request, 'Explanation updated successfully!')
                    return redirect('admin:api_lessonquestion_change', question_id)
            except Exception as e:
                messages.error(request, f'Error updating explanation: {str(e)}')
        
        # Get available assets for diagram selection
        available_assets = list(question.lesson.assets.values('asset_id', 's3_url'))
        
        context = {
            'question': question,
            'explanation_json': mark_safe(json.dumps(question.explanation or [])),
            'available_assets': mark_safe(json.dumps(available_assets)),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, question),
            'has_change_permission': self.has_change_permission(request, question),
        }
        
        return render(request, 'admin/api/lesson_question_explanation_editor.html', context)


@admin.register(LessonQuestionOption)
class LessonQuestionOptionAdmin(admin.ModelAdmin):
    """Admin interface for lesson question options"""
    list_display = ['text_short', 'question', 'order']
    list_filter = ['question__lesson', 'created_at']
    search_fields = ['text', 'question__text']
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Option'


# Writing Section Admin
class WritingSectionIngestionForm(forms.ModelForm):
    """Custom form for writing section file upload - supports JSON or documents with GPT conversion"""
    file = forms.FileField(
        required=True,
        help_text="Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT.",
        widget=forms.FileInput(attrs={'accept': '.json,.pdf,.docx,.doc,.txt,application/json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain'})
    )
    use_gpt_conversion = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check this to convert document to JSON using GPT (auto-detected for non-JSON files)"
    )
    
    class Meta:
        model = WritingSectionIngestion
        fields = ['file', 'use_gpt_conversion']
    
    def clean_file(self):
        """Validate uploaded file"""
        data = self.cleaned_data.get('file')
        if data:
            file_ext = os.path.splitext(data.name)[1].lower()
            
            # If it's a JSON file, validate it
            if file_ext == '.json':
                try:
                    data.seek(0)
                    json.loads(data.read().decode('utf-8'))
                    data.seek(0)  # Reset for later use
                except json.JSONDecodeError as e:
                    raise forms.ValidationError(f'Invalid JSON file: {str(e)}')
                except UnicodeDecodeError:
                    raise forms.ValidationError('File must be valid UTF-8 encoded JSON')
            # For other file types, we'll handle them in save_model
            elif file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
                raise forms.ValidationError('File must be JSON (.json), PDF (.pdf), DOCX (.docx), or TXT (.txt)')
        
        return data


@admin.register(WritingSectionIngestion)
class WritingSectionIngestionAdmin(admin.ModelAdmin):
    """Admin interface for writing section ingestion"""
    form = WritingSectionIngestionForm
    list_display = ['file_name', 'status', 'created_writing_section_link', 'created_at', 'process_action']
    list_filter = ['status', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_name', 'file_path', 'status', 'parsed_data_preview', 'error_message', 'created_writing_section_link', 'created_at', 'updated_at']
    actions = ['process_selected']
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file', 'use_gpt_conversion'),
            'description': 'Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT. Check "Use GPT conversion" to force GPT conversion even for JSON files.'
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_path', 'error_message')
        }),
        ('Results', {
            'fields': ('parsed_data_preview', 'created_writing_section_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parsed_data_preview(self, obj):
        """Display preview of parsed JSON data"""
        try:
            # Check if parsed_data field exists and has a value
            if hasattr(obj, 'parsed_data'):
                parsed_data = getattr(obj, 'parsed_data', None)
                if parsed_data:
                    preview = json.dumps(parsed_data, indent=2)[:1000] + '...' if len(json.dumps(parsed_data)) > 1000 else json.dumps(parsed_data, indent=2)
                    return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
        except Exception:
            # Handle case where column doesn't exist in database yet
            pass
        return '-'
    parsed_data_preview.short_description = 'Parsed Data Preview'
    
    def created_writing_section_link(self, obj):
        """Link to created writing section"""
        if obj.created_writing_section:
            url = reverse('admin:api_writingsection_change', args=[obj.created_writing_section.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_writing_section.title)
        return '-'
    created_writing_section_link.short_description = 'Created Writing Section'
    
    def process_action(self, obj):
        """Display process button for each row"""
        if obj.status in ['pending', 'failed'] or (obj.status == 'processing' and not obj.created_writing_section):
            url = reverse('admin:api_writingsectioningestion_process', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 5px 10px; background: #417690; color: white; text-decoration: none; border-radius: 3px;">Process Now</a>',
                url
            )
        return '-'
    process_action.short_description = 'Actions'
    process_action.allow_tags = True
    
    def process_selected(self, request, queryset):
        """Admin action to process selected ingestions"""
        processed = 0
        for ingestion in queryset:
            if ingestion.status in ['pending', 'failed'] or (ingestion.status == 'processing' and not ingestion.created_writing_section):
                try:
                    process_writing_ingestion(ingestion)
                    processed += 1
                except Exception as e:
                    self.message_user(request, f'Error processing {ingestion.file_name}: {str(e)}', level='ERROR')
        
        if processed > 0:
            self.message_user(request, f'Successfully processed {processed} ingestion(s).', level='SUCCESS')
        else:
            self.message_user(request, 'No ingestions to process. Only pending or failed ingestions can be processed.', level='WARNING')
    process_selected.short_description = 'Process selected writing section ingestions'
    
    def get_urls(self):
        """Add custom URL for processing"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:ingestion_id>/process/',
                self.admin_site.admin_view(self.process_ingestion_view),
                name='api_writingsectioningestion_process',
            ),
        ]
        return custom_urls + urls
    
    def process_ingestion_view(self, request, ingestion_id):
        """Custom view to process a single ingestion"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        ingestion = get_object_or_404(WritingSectionIngestion, pk=ingestion_id)
        
        if ingestion.status not in ['pending', 'failed'] and (ingestion.status != 'processing' or ingestion.created_writing_section):
            messages.warning(request, 'This ingestion has already been processed.')
            return redirect('admin:api_writingsectioningestion_changelist')
        
        try:
            process_writing_ingestion(ingestion)
            messages.success(request, f'Successfully processed {ingestion.file_name}.')
        except Exception as e:
            messages.error(request, f'Error processing {ingestion.file_name}: {str(e)}')
        
        return redirect('admin:api_writingsectioningestion_changelist')
    
    def save_model(self, request, obj, form, change):
        """Handle file upload and save ingestion"""
        from django.db import transaction
        
        if not change:  # Only on create
            uploaded_file = request.FILES.get('file')
            use_gpt = form.cleaned_data.get('use_gpt_conversion', False)
            
            if not uploaded_file:
                # No file uploaded - use default save
                super().save_model(request, obj, form, change)
                return
            
            import uuid
            from pathlib import Path
            
            # Create media directory if it doesn't exist
            media_dir = Path(settings.MEDIA_ROOT)
            media_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = media_dir / unique_filename
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            obj.file_name = uploaded_file.name
            obj.file_path = str(file_path)
            obj.file_type = file_ext[1:] if file_ext.startswith('.') else file_ext
            
            # Determine if we need GPT conversion
            is_json = file_ext.lower() == '.json'
            is_document = file_ext.lower() in ['.pdf', '.docx', '.doc', '.txt']
            should_use_gpt = use_gpt or (is_document and not is_json)
            
            # Handle JSON files directly
            if is_json:
                try:
                    with transaction.atomic():
                        # Direct JSON parsing
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                obj.parsed_data = json.load(f)
                        except UnicodeDecodeError:
                            # Try with error handling for non-UTF-8 files
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                obj.parsed_data = json.load(f)
                        obj.status = 'pending'
                        obj.save()
                except Exception as e:
                    with transaction.atomic():
                        obj.status = 'failed'
                        obj.error_message = f'Failed to parse JSON file: {str(e)}'
                        obj.save()
                    return
            
            # Handle documents that need GPT conversion
            elif should_use_gpt and is_document:
                # Save initial state in transaction
                try:
                    with transaction.atomic():
                        obj.status = 'processing'
                        obj.error_message = 'Converting document to JSON using GPT...'
                        obj.save()  # Save first to get the ID
                except Exception as e:
                    obj.status = 'failed'
                    obj.error_message = f'Failed to save ingestion: {str(e)}'
                    obj.save()
                    return
                
                # GPT conversion happens outside transaction to avoid long-running transactions
                try:
                    writing_data = convert_document_to_writing_json(str(file_path), uploaded_file.name)
                    # Update in a new transaction
                    with transaction.atomic():
                        obj.refresh_from_db()
                        obj.parsed_data = writing_data
                        obj.error_message = f'✓ Successfully converted document to JSON using GPT.'
                        obj.status = 'pending'  # Reset to pending so background processing can run
                        obj.save()
                except Exception as gpt_error:
                    # GPT conversion failed - don't proceed to processing
                    try:
                        with transaction.atomic():
                            obj.refresh_from_db()
                            obj.status = 'failed'
                            obj.error_message = f'Failed to convert document to JSON using GPT: {str(gpt_error)}'
                            obj.save()
                    except Exception as save_error:
                        # If refresh fails, the object might not exist - log and return
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Failed to save error state: {save_error}')
                    return  # Don't start background processing
            
            # Unsupported file type
            else:
                with transaction.atomic():
                    obj.status = 'failed'
                    obj.error_message = f'Unsupported file type: {file_ext}. Use JSON or enable GPT conversion for documents.'
                    obj.save()
                return
            
            # Process in background - only if we have parsed_data (either from JSON or GPT conversion)
            if obj.status != 'failed' and obj.parsed_data:
                def process_in_background(ingestion_id):
                    import traceback
                    from django.db import connection
                    connection.close()
                    from django import db
                    db.connections.close_all()
                    from .models import WritingSectionIngestion
                    ingestion = WritingSectionIngestion.objects.get(pk=ingestion_id)
                    try:
                        process_writing_ingestion(ingestion)
                    except Exception as e:
                        ingestion.status = 'failed'
                        ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                        ingestion.save()
                
                # Mark as processing in a new transaction
                try:
                    with transaction.atomic():
                        WritingSectionIngestion.objects.filter(pk=obj.pk).update(status='processing')
                except Exception as e:
                    # If update fails, log but don't crash
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Failed to update status to processing: {e}')
                
                thread = threading.Thread(target=process_in_background, args=(obj.pk,))
                thread.daemon = True
                thread.start()
        else:
            super().save_model(request, obj, form, change)


@admin.register(WritingSection)
class WritingSectionAdmin(admin.ModelAdmin):
    """Admin interface for writing sections"""
    list_display = ['title', 'difficulty', 'tier', 'header', 'order_within_header', 'display_order', 'selection_count', 'question_count', 'created_at']
    list_filter = ['difficulty', 'tier', 'header', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
    actions = ['move_up', 'move_down', 'move_up_in_header', 'move_down_in_header']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter headers by writing category and content_type when assigning to writing sections"""
        if db_field.name == 'header':
            # Filter headers to only show writing category headers for sections
            kwargs['queryset'] = Header.objects.filter(
                category='writing'
            ).filter(
                Q(content_type='section') | Q(content_type='both')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'content', 'difficulty', 'tier')
        }),
        ('Organization', {
            'fields': ('header', 'order_within_header', 'display_order'),
            'description': 'Assign writing section to a header/section and set its order within that header. Only writing category headers will be shown.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def move_up(self, request, queryset):
        """Move selected items up (increase display_order)"""
        for obj in queryset:
            obj.display_order += 1
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) up.")
    move_up.short_description = "Move up (increase order)"
    
    def move_down(self, request, queryset):
        """Move selected items down (decrease display_order)"""
        for obj in queryset:
            obj.display_order = max(0, obj.display_order - 1)
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) down.")
    move_down.short_description = "Move down (decrease order)"
    
    def move_up_in_header(self, request, queryset):
        """Move selected writing sections up within their header (increase order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header += 1
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} writing section(s) up within their headers.")
    move_up_in_header.short_description = "Move up within header"
    
    def move_down_in_header(self, request, queryset):
        """Move selected writing sections down within their header (decrease order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header = max(0, obj.order_within_header - 1)
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} writing section(s) down within their headers.")
    move_down_in_header.short_description = "Move down within header"
    
    def selection_count(self, obj):
        """Display number of selections"""
        if obj.pk:
            return obj.selections.count()
        return 0
    selection_count.short_description = 'Selections'
    
    def question_count(self, obj):
        """Display number of questions"""
        if obj.pk:
            return obj.questions.count()
        return 0
    question_count.short_description = 'Questions'


@admin.register(WritingSectionSelection)
class WritingSectionSelectionAdmin(admin.ModelAdmin):
    """Admin interface for writing section selections"""
    list_display = ['number', 'writing_section', 'selected_text_short', 'start_char', 'end_char']
    list_filter = ['writing_section', 'created_at']
    search_fields = ['selected_text', 'writing_section__title']
    
    def selected_text_short(self, obj):
        return obj.selected_text[:50] + '...' if len(obj.selected_text) > 50 else obj.selected_text
    selected_text_short.short_description = 'Selected Text'


@admin.register(WritingSectionQuestion)
class WritingSectionQuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for writing section questions"""
    list_display = ['text_short', 'writing_section', 'order', 'correct_answer_index', 'selection_number']
    list_filter = ['writing_section', 'created_at']
    search_fields = ['text', 'writing_section__title']
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Question'


@admin.register(WritingSectionQuestionOption)
class WritingSectionQuestionOptionAdmin(admin.ModelAdmin):
    """Admin interface for writing section question options"""
    list_display = ['text_short', 'question', 'order']
    list_filter = ['question__writing_section', 'created_at']
    search_fields = ['text', 'question__text']
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Option'
# Math Section Admin - to be added to admin.py

class MathSectionIngestionForm(forms.ModelForm):
    """Custom form for math section file upload - supports JSON or documents with GPT conversion"""
    file = forms.FileField(
        required=True,
        help_text="Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT.",
        widget=forms.FileInput(attrs={'accept': '.json,.pdf,.docx,.doc,.txt,application/json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain'})
    )
    use_gpt_conversion = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check this to convert document to JSON using GPT (auto-detected for non-JSON files)"
    )
    
    class Meta:
        model = MathSectionIngestion
        fields = ['file', 'use_gpt_conversion']
    
    def clean_file(self):
        """Validate uploaded file"""
        data = self.cleaned_data.get('file')
        if data:
            file_ext = os.path.splitext(data.name)[1].lower()
            
            # If it's a JSON file, validate it
            if file_ext == '.json':
                try:
                    data.seek(0)
                    json.loads(data.read().decode('utf-8'))
                    data.seek(0)  # Reset for later use
                except json.JSONDecodeError as e:
                    raise forms.ValidationError(f'Invalid JSON file: {str(e)}')
                except UnicodeDecodeError:
                    raise forms.ValidationError('File must be valid UTF-8 encoded JSON')
            # For other file types, we'll handle them in save_model
            elif file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
                raise forms.ValidationError('File must be JSON (.json), PDF (.pdf), DOCX (.docx), or TXT (.txt)')
        
        return data


@admin.register(MathSectionIngestion)
class MathSectionIngestionAdmin(admin.ModelAdmin):
    """Admin interface for math section ingestion"""
    form = MathSectionIngestionForm
    list_display = ['file_name', 'status', 'error_message_short', 'created_math_section_link', 'created_at', 'process_action']
    list_filter = ['status', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_name', 'file_path', 'status', 'parsed_data_preview', 'error_message', 'created_math_section_link', 'created_at', 'updated_at']
    
    def error_message_short(self, obj):
        """Display short error message in list view"""
        if obj.error_message:
            return obj.error_message[:100] + '...' if len(obj.error_message) > 100 else obj.error_message
        return '-'
    error_message_short.short_description = 'Error'
    actions = ['process_selected']
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file', 'use_gpt_conversion'),
            'description': 'Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT. Check "Use GPT conversion" to force GPT conversion even for JSON files.'
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_path', 'error_message')
        }),
        ('Results', {
            'fields': ('parsed_data_preview', 'created_math_section_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parsed_data_preview(self, obj):
        """Display preview of parsed JSON data"""
        try:
            # Check if parsed_data field exists and has a value
            if hasattr(obj, 'parsed_data'):
                parsed_data = getattr(obj, 'parsed_data', None)
                if parsed_data:
                    preview = json.dumps(parsed_data, indent=2)[:1000] + '...' if len(json.dumps(parsed_data)) > 1000 else json.dumps(parsed_data, indent=2)
                    return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
        except Exception:
            # Handle case where column doesn't exist in database yet
            pass
        return '-'
    parsed_data_preview.short_description = 'Parsed Data Preview'
    
    def created_math_section_link(self, obj):
        """Link to created math section"""
        if obj.created_math_section:
            url = reverse('admin:api_mathsection_change', args=[obj.created_math_section.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_math_section.title)
        return '-'
    created_math_section_link.short_description = 'Created Math Section'
    
    def process_action(self, obj):
        """Display process button for each row"""
        if obj.status in ['pending', 'failed'] or (obj.status == 'processing' and not obj.created_math_section):
            url = reverse('admin:api_mathsectioningestion_process', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 5px 10px; background: #417690; color: white; text-decoration: none; border-radius: 3px;">Process Now</a>',
                url
            )
        return '-'
    process_action.short_description = 'Actions'
    process_action.allow_tags = True
    
    def process_selected(self, request, queryset):
        """Admin action to process selected ingestions"""
        processed = 0
        for ingestion in queryset:
            if ingestion.status in ['pending', 'failed'] or (ingestion.status == 'processing' and not ingestion.created_math_section):
                try:
                    process_math_ingestion(ingestion)
                    processed += 1
                except Exception as e:
                    self.message_user(request, f'Error processing {ingestion.file_name}: {str(e)}', level='ERROR')
        
        if processed > 0:
            self.message_user(request, f'Successfully processed {processed} ingestion(s).', level='SUCCESS')
        else:
            self.message_user(request, 'No ingestions to process. Only pending or failed ingestions can be processed.', level='WARNING')
    process_selected.short_description = 'Process selected math section ingestions'
    
    def get_urls(self):
        """Add custom URL for processing"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:ingestion_id>/process/',
                self.admin_site.admin_view(self.process_ingestion_view),
                name='api_mathsectioningestion_process',
            ),
        ]
        return custom_urls + urls
    
    def process_ingestion_view(self, request, ingestion_id):
        """Custom view to process a single ingestion"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        ingestion = get_object_or_404(MathSectionIngestion, pk=ingestion_id)
        
        if ingestion.status not in ['pending', 'failed'] and (ingestion.status != 'processing' or ingestion.created_math_section):
            messages.warning(request, 'This ingestion has already been processed.')
            return redirect('admin:api_mathsectioningestion_changelist')
        
        try:
            process_math_ingestion(ingestion)
            messages.success(request, f'Successfully processed {ingestion.file_name}.')
        except Exception as e:
            messages.error(request, f'Error processing {ingestion.file_name}: {str(e)}')
        
        return redirect('admin:api_mathsectioningestion_changelist')
    
    def save_model(self, request, obj, form, change):
        """Handle file upload and save ingestion"""
        from django.db import transaction
        
        if not change:  # Only on create
            uploaded_file = request.FILES.get('file')
            use_gpt = form.cleaned_data.get('use_gpt_conversion', False)
            
            if not uploaded_file:
                # No file uploaded - use default save
                super().save_model(request, obj, form, change)
                return
            
            import uuid
            from pathlib import Path
            
            # Create media directory if it doesn't exist
            media_dir = Path(settings.MEDIA_ROOT)
            media_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = media_dir / unique_filename
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            obj.file_name = uploaded_file.name
            obj.file_path = str(file_path)
            obj.file_type = file_ext.lower().lstrip('.')
            
            # Determine if we need GPT conversion
            is_json = file_ext.lower() == '.json'
            is_document = file_ext.lower() in ['.pdf', '.docx', '.doc', '.txt']
            should_use_gpt = use_gpt or (is_document and not is_json)
            
            # Parse JSON or convert document
            try:
                with transaction.atomic():
                    obj.status = 'processing'
                    obj.error_message = 'Processing file...'
                    obj.save()  # Save first to get the ID
                
                if is_json:
                    # Direct JSON parsing
                    with open(file_path, 'r', encoding='utf-8') as f:
                        obj.parsed_data = json.load(f)
                    obj.error_message = '✓ Successfully loaded JSON file.'
                elif should_use_gpt and is_document:
                    # Convert document to JSON using GPT (outside transaction to avoid long-running calls)
                    obj.error_message = 'Converting document to JSON using GPT...'
                    obj.save()
                    
                    # Convert document using GPT with schema
                    try:
                        # This calls GPT API with the math section schema from MATH_SECTION_JSON_SCHEMA.md
                        math_data = convert_document_to_math_json(str(file_path), uploaded_file.name)
                        
                        # Verify we got valid data
                        if not math_data or not isinstance(math_data, dict):
                            raise ValueError("GPT returned invalid data: expected a dictionary")
                        if 'section_id' not in math_data or 'title' not in math_data or 'questions' not in math_data:
                            raise ValueError(f"GPT returned incomplete data. Missing required fields. Got: {list(math_data.keys())}")
                        
                        # Update in a new transaction to ensure data is saved
                        with transaction.atomic():
                            obj.refresh_from_db()
                            obj.parsed_data = math_data
                            obj.error_message = f'✓ Successfully converted document to JSON using GPT. Found {len(math_data.get("questions", []))} questions.'
                            obj.status = 'pending'  # Reset to pending so background processing can run
                            obj.save()
                    except Exception as gpt_error:
                        # GPT conversion failed - don't proceed to processing
                        import traceback
                        error_trace = traceback.format_exc()
                        with transaction.atomic():
                            obj.refresh_from_db()
                            obj.status = 'failed'
                            obj.error_message = f'Failed to convert document to JSON using GPT: {str(gpt_error)}\n\nTraceback:\n{error_trace}'
                            obj.save()  # Save error state
                        return  # Don't start background processing
                else:
                    raise ValueError(f'Unsupported file type: {file_ext}. Use JSON or enable GPT conversion for documents.')
            except Exception as e:
                obj.status = 'failed'
                obj.error_message = f'Failed to process file: {str(e)}'
                obj.save()  # Save error state
                return  # Don't start background processing
            
            # Save ingestion (only if we got here without errors and we have parsed_data)
            # For GPT conversion, we already saved above, so only save if it's JSON
            if is_json:
                obj.save()
            
            # CRITICAL: Refresh from DB to ensure we have the latest parsed_data before starting background processing
            # This prevents race conditions where the in-memory object doesn't match the database
            # Wait a moment for transaction to commit, then refresh
            import time
            time.sleep(0.3)  # Small delay to ensure transaction committed
            obj.refresh_from_db()  # Refresh again after delay
            
            # Process in background (only if we have parsed_data and didn't fail)
            # Double-check from database to be absolutely sure
            if obj.status != 'failed' and obj.parsed_data:
                def process_in_background(ingestion_id):
                    import time
                    import traceback
                    from django.db import connection
                    # Small delay to ensure transaction has committed
                    time.sleep(0.5)
                    connection.close()
                    from django import db
                    db.connections.close_all()
                    from .models import MathSectionIngestion
                    # Try to get the object, with retry logic
                    ingestion = None
                    for attempt in range(5):  # More retries
                        try:
                            ingestion = MathSectionIngestion.objects.get(pk=ingestion_id)
                            # Refresh to ensure we have the latest parsed_data
                            ingestion.refresh_from_db()
                            if ingestion.parsed_data:
                                break
                            elif attempt < 4:
                                time.sleep(1.0)  # Longer delay between retries
                            else:
                                # Last attempt - check error message to see if GPT conversion failed
                                if ingestion.error_message and 'Failed to convert' in ingestion.error_message:
                                    # GPT conversion failed - don't try to process
                                    return
                                raise ValueError(f"parsed_data is still empty after {attempt + 1} retries. Status: {ingestion.status}, Error: {ingestion.error_message[:200] if ingestion.error_message else 'None'}")
                        except MathSectionIngestion.DoesNotExist:
                            if attempt < 4:
                                time.sleep(1.0)
                            else:
                                raise
                    
                    if ingestion and ingestion.parsed_data:
                        try:
                            process_math_ingestion(ingestion)
                        except Exception as e:
                            ingestion.status = 'failed'
                            ingestion.error_message = f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
                            ingestion.save()
                    else:
                        # Log error if we can't get the object or it has no parsed_data
                        import logging
                        logger = logging.getLogger(__name__)
                        if ingestion:
                            logger.error(f"MathSectionIngestion {ingestion_id} has no parsed_data after retries. Status: {ingestion.status}, Error: {ingestion.error_message[:500] if ingestion.error_message else 'None'}")
                            # Update error message in database
                            try:
                                ingestion.status = 'failed'
                                ingestion.error_message = f"Background processing failed: parsed_data is empty. Original error: {ingestion.error_message[:500] if ingestion.error_message else 'None'}"
                                ingestion.save()
                            except:
                                pass
                        else:
                            logger.error(f"MathSectionIngestion {ingestion_id} does not exist after retries")
                
                # Mark as processing in a new transaction
                try:
                    with transaction.atomic():
                        MathSectionIngestion.objects.filter(pk=obj.pk).update(status='processing')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Failed to update status to processing: {e}')
                
                thread = threading.Thread(target=process_in_background, args=(obj.pk,))
                thread.daemon = True
                thread.start()
                
                from django.contrib import messages
                messages.info(request, "Processing started automatically in the background.")
        else:
            super().save_model(request, obj, form, change)


class MathAssetForm(forms.ModelForm):
    """Custom form for math assets with file upload"""
    image_file = forms.FileField(
        required=False,
        help_text="Upload an image file. It will be automatically uploaded to S3 and the S3 URL will be set. Use sentinel format [[Diagram asset_id]] in math section text.",
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    
    class Meta:
        model = MathAsset
        fields = ['asset_id', 'type', 'image_file', 's3_url']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make s3_url read-only if it exists
        if self.instance and self.instance.s3_url:
            self.fields['s3_url'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        """Handle image upload and S3 upload"""
        instance = super().save(commit=False)
        
        # Handle file upload if provided
        if 'image_file' in self.cleaned_data and self.cleaned_data['image_file']:
            image_file = self.cleaned_data['image_file']
            
            # Upload to S3
            from .math_gpt_utils import upload_image_to_s3
            import tempfile
            
            # Save uploaded file temporarily
            file_ext = os.path.splitext(image_file.name)[1].lower()
            if file_ext not in ['.png', '.jpg', '.jpeg', '.svg', '.gif']:
                file_ext = '.png'
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_file.close()
            
            try:
                # Upload to S3
                asset_id = instance.asset_id or os.path.splitext(image_file.name)[0]
                section_id = instance.math_section.section_id if instance.math_section else 'unknown'
                s3_url = upload_image_to_s3(temp_file.name, asset_id, section_id)
                instance.s3_url = s3_url
            except Exception as e:
                # Store error in form for display
                self.add_error('image_file', f"Failed to upload image to S3: {str(e)}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        if commit:
            instance.save()
        return instance


class MathAssetInline(nested_admin.NestedTabularInline):
    """Inline editor for math assets (diagrams/images)"""
    model = MathAsset
    form = MathAssetForm
    extra = 1
    fields = ('asset_id', 'type', 'image_file', 's3_url', 'preview')
    readonly_fields = ('preview',)
    
    def preview(self, obj):
        """Show preview of the image if S3 URL exists"""
        if obj and obj.s3_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.s3_url)
        return "-"
    preview.short_description = "Preview"


@admin.register(MathSection)
class MathSectionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for math sections"""
    list_display = ['title', 'section_id', 'difficulty', 'tier', 'header', 'order_within_header', 'display_order', 'question_count', 'asset_count', 'created_at']
    list_filter = ['difficulty', 'tier', 'header', 'created_at']
    search_fields = ['title', 'section_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display', 'asset_count_display']
    inlines = [MathAssetInline]
    actions = ['move_up', 'move_down', 'move_up_in_header', 'move_down_in_header']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter headers by math category and content_type when assigning to math sections"""
        if db_field.name == 'header':
            # Filter headers to only show math category headers for sections
            kwargs['queryset'] = Header.objects.filter(
                category='math'
            ).filter(
                Q(content_type='section') | Q(content_type='both')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'section_id', 'title', 'difficulty', 'tier')
        }),
        ('Organization', {
            'fields': ('header', 'order_within_header', 'display_order'),
            'description': 'Assign math section to a header/section and set its order within that header. Only math category headers will be shown.'
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'asset_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def move_up(self, request, queryset):
        """Move selected items up (increase display_order)"""
        for obj in queryset:
            obj.display_order += 1
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) up.")
    move_up.short_description = "Move up (increase order)"
    
    def move_down(self, request, queryset):
        """Move selected items down (decrease display_order)"""
        for obj in queryset:
            obj.display_order = max(0, obj.display_order - 1)
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} item(s) down.")
    move_down.short_description = "Move down (decrease order)"
    
    def move_up_in_header(self, request, queryset):
        """Move selected math sections up within their header (increase order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header += 1
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} math section(s) up within their headers.")
    move_up_in_header.short_description = "Move up within header"
    
    def move_down_in_header(self, request, queryset):
        """Move selected math sections down within their header (decrease order_within_header)"""
        for obj in queryset:
            if obj.header:
                obj.order_within_header = max(0, obj.order_within_header - 1)
                obj.save()
        self.message_user(request, f"Moved {queryset.count()} math section(s) down within their headers.")
    move_down_in_header.short_description = "Move down within header"
    
    def question_count(self, obj):
        """Display number of questions for this math section"""
        if obj.pk:
            return obj.questions.count()
        return 0
    question_count.short_description = 'Questions'
    
    def asset_count(self, obj):
        """Display number of assets for this math section"""
        if obj.pk:
            return obj.assets.count()
        return 0
    asset_count.short_description = 'Assets'
    
    def question_count_display(self, obj):
        """Read-only field showing question count"""
        if obj.pk:
            count = obj.questions.count()
            return f"{count} question{'s' if count != 1 else ''}"
        return "Save math section to see question count"
    question_count_display.short_description = 'Question Count'
    
    def asset_count_display(self, obj):
        """Read-only field showing asset count"""
        if obj.pk:
            count = obj.assets.count()
            return f"{count} asset{'s' if count != 1 else ''}"
        return "Save math section to see asset count"
    asset_count_display.short_description = 'Asset Count'


@admin.register(MathQuestion)
class MathQuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for math questions"""
    list_display = ['prompt_short', 'math_section', 'question_id', 'order', 'correct_answer_index', 'edit_explanation_link']
    list_filter = ['math_section', 'created_at']
    search_fields = ['prompt', 'question_id', 'math_section__title']
    readonly_fields = ['edit_prompt_button', 'edit_explanation_button']
    
    fieldsets = (
        ('Question Information', {
            'fields': ('math_section', 'question_id', 'correct_answer_index', 'order')
        }),
        ('Prompt', {
            'fields': ('edit_prompt_button', 'prompt'),
            'description': 'Click the button below to edit the prompt using the visual editor, or edit the JSON directly in the field below.'
        }),
        ('Explanation', {
            'fields': ('edit_explanation_button', 'explanation'),
            'description': 'Click the button below to edit the explanation using the visual editor, or edit the JSON directly in the field below.'
        }),
    )
    
    def prompt_short(self, obj):
        return obj.prompt[:100] + '...' if len(obj.prompt) > 100 else obj.prompt
    prompt_short.short_description = 'Question'
    
    def edit_explanation_link(self, obj):
        """Link to user-friendly explanation editor (for list view)"""
        if obj.pk:
            url = reverse('admin:api_mathquestion_edit_explanation', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 8px 16px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 12px;">📝 Edit Explanation</a>',
                url
            )
        return "Save question first to edit explanation"
    edit_explanation_link.short_description = 'Edit Explanation'
    edit_explanation_link.allow_tags = True
    
    def edit_prompt_button(self, obj):
        """Button to edit prompt (for detail/edit view)"""
        if obj.pk:
            url = reverse('admin:api_mathquestion_edit_prompt', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 12px 24px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 14px; margin-bottom: 10px;">📝 Edit Prompt (Easy Mode)</a>',
                url
            )
        return "Save question first to edit prompt"
    edit_prompt_button.short_description = ''
    edit_prompt_button.allow_tags = True
    
    def edit_explanation_button(self, obj):
        """Button to edit explanation (for detail/edit view)"""
        if obj.pk:
            url = reverse('admin:api_mathquestion_edit_explanation', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="padding: 12px 24px; background: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 14px; margin-bottom: 10px;">📝 Edit Explanation (Easy Mode)</a>',
                url
            )
        return "Save question first to edit explanation"
    edit_explanation_button.short_description = ''
    edit_explanation_button.allow_tags = True
    
    def get_urls(self):
        """Add custom URL for explanation editor"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:question_id>/edit-prompt/',
                self.admin_site.admin_view(self.edit_prompt_view),
                name='api_mathquestion_edit_prompt',
            ),
            path(
                '<uuid:question_id>/edit-explanation/',
                self.admin_site.admin_view(self.edit_explanation_view),
                name='api_mathquestion_edit_explanation',
            ),
        ]
        return custom_urls + urls
    
    def edit_prompt_view(self, request, question_id):
        """Handle the prompt editor page"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        import json
        
        question = get_object_or_404(MathQuestion, pk=question_id)
        
        if request.method == 'POST':
            try:
                prompt_json = request.POST.get('prompt_json')
                if prompt_json:
                    prompt = json.loads(prompt_json)
                    question.prompt = prompt
                    question.save()
                    messages.success(request, 'Prompt updated successfully!')
                    return redirect('admin:api_mathquestion_change', question_id)
            except Exception as e:
                messages.error(request, f'Error updating prompt: {str(e)}')
        
        # Get available assets for diagram selection
        available_assets = list(question.math_section.assets.values('asset_id', 's3_url'))
        
        context = {
            'question': question,
            'prompt_json': mark_safe(json.dumps(question.prompt or [])),
            'available_assets': mark_safe(json.dumps(available_assets)),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, question),
            'has_change_permission': self.has_change_permission(request, question),
        }
        
        return render(request, 'admin/api/math_question_prompt_editor.html', context)
    
    def edit_explanation_view(self, request, question_id):
        """Handle the explanation editor page"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        import json
        
        question = get_object_or_404(MathQuestion, pk=question_id)
        
        if request.method == 'POST':
            try:
                explanation_json = request.POST.get('explanation_json')
                if explanation_json:
                    explanation = json.loads(explanation_json)
                    question.explanation = explanation
                    question.save()
                    messages.success(request, 'Explanation updated successfully!')
                    return redirect('admin:api_mathquestion_change', question_id)
            except Exception as e:
                messages.error(request, f'Error updating explanation: {str(e)}')
        
        # Get available assets for diagram selection
        available_assets = list(question.math_section.assets.values('asset_id', 's3_url'))
        
        context = {
            'question': question,
            'explanation_json': mark_safe(json.dumps(question.explanation or [])),
            'available_assets': mark_safe(json.dumps(available_assets)),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, question),
            'has_change_permission': self.has_change_permission(request, question),
        }
        
        return render(request, 'admin/api/math_question_explanation_editor.html', context)


@admin.register(MathQuestionOption)
class MathQuestionOptionAdmin(admin.ModelAdmin):
    """Admin interface for math question options"""
    list_display = ['text_short', 'question', 'order']
    list_filter = ['question__math_section', 'created_at']
    search_fields = ['text', 'question__prompt']
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Option'


@admin.register(MathAsset)
class MathAssetAdmin(admin.ModelAdmin):
    """Admin interface for math assets"""
    list_display = ['asset_id', 'math_section', 'type', 's3_url_short']
    list_filter = ['type', 'math_section', 'created_at']
    search_fields = ['asset_id', 'math_section__title', 's3_url']
    
    def s3_url_short(self, obj):
        return obj.s3_url[:50] + '...' if len(obj.s3_url) > 50 else obj.s3_url
    s3_url_short.short_description = 'S3 URL'


# Custom Admin Classes for Category Views - Filter by lesson_type
class ReadingLessonAdmin(LessonAdmin):
    """Admin for reading lessons only"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(lesson_type='reading')


class WritingLessonAdmin(LessonAdmin):
    """Admin for writing lessons only"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(lesson_type='writing')


class MathLessonAdmin(LessonAdmin):
    """Admin for math lessons only"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(lesson_type='math')


# Register category-specific admins using proxy models
@admin.register(ReadingLesson)
class ReadingLessonProxyAdmin(ReadingLessonAdmin):
    pass


@admin.register(WritingLesson)
class WritingLessonProxyAdmin(WritingLessonAdmin):
    pass


@admin.register(MathLesson)
class MathLessonProxyAdmin(MathLessonAdmin):
    pass


@admin.register(Header)
class HeaderAdmin(admin.ModelAdmin):
    """Admin interface for headers/sections"""
    list_display = ['title', 'category', 'content_type', 'display_order', 'lesson_count_display', 'passage_count_display', 'writing_section_count_display', 'math_section_count_display', 'created_at']
    list_filter = ['category', 'content_type', 'created_at']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'lesson_count_display', 'passage_count_display', 'writing_section_count_display', 'math_section_count_display']
    actions = ['move_up', 'move_down']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'category', 'content_type', 'display_order'),
            'description': 'content_type: "Lesson" for lessons only, "Section/Passage" for sections/passages only, "Both" for both types'
        }),
        ('Metadata', {
            'fields': ('lesson_count_display', 'passage_count_display', 'writing_section_count_display', 'math_section_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def move_up(self, request, queryset):
        """Move selected headers up (increase display_order)"""
        for obj in queryset:
            obj.display_order += 1
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} header(s) up.")
    move_up.short_description = "Move up (increase order)"
    
    def move_down(self, request, queryset):
        """Move selected headers down (decrease display_order)"""
        for obj in queryset:
            obj.display_order = max(0, obj.display_order - 1)
            obj.save()
        self.message_user(request, f"Moved {queryset.count()} header(s) down.")
    move_down.short_description = "Move down (decrease order)"
    
    def lesson_count(self, obj):
        """Display number of lessons in this header"""
        if obj.pk:
            return obj.lessons.count()
        return 0
    lesson_count.short_description = 'Lessons'
    
    def lesson_count_display(self, obj):
        """Read-only field showing lesson count"""
        if obj.pk:
            count = obj.lessons.count()
            return f"{count} lesson{'s' if count != 1 else ''}"
        return "Save header to see lesson count"
    lesson_count_display.short_description = 'Lesson Count'
    
    def passage_count_display(self, obj):
        """Read-only field showing passage count"""
        if obj.pk:
            count = obj.passages.count()
            return f"{count} passage{'s' if count != 1 else ''}"
        return "Save header to see passage count"
    passage_count_display.short_description = 'Passage Count'
    
    def writing_section_count_display(self, obj):
        """Read-only field showing writing section count"""
        if obj.pk:
            count = obj.writing_sections.count()
            return f"{count} writing section{'s' if count != 1 else ''}"
        return "Save header to see writing section count"
    writing_section_count_display.short_description = 'Writing Section Count'
    
    def math_section_count_display(self, obj):
        """Read-only field showing math section count"""
        if obj.pk:
            count = obj.math_sections.count()
            return f"{count} math section{'s' if count != 1 else ''}"
        return "Save header to see math section count"
    math_section_count_display.short_description = 'Math Section Count'


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    """Admin interface for user study plans"""
    list_display = ['user', 'reading_status', 'writing_status', 'math_status', 'created_at', 'updated_at']
    list_filter = ['reading_diagnostic_completed', 'writing_diagnostic_completed', 'math_diagnostic_completed']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'reading_summary', 'writing_summary', 'math_summary']
    raw_id_fields = ['user', 'reading_diagnostic_passage', 'writing_diagnostic', 'math_diagnostic']
    filter_horizontal = ['recommended_lessons']
    
    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Reading', {
            'fields': ('reading_diagnostic_completed', 'reading_diagnostic_passage', 'reading_performance', 'reading_summary'),
            'classes': ('collapse',)
        }),
        ('Writing', {
            'fields': ('writing_diagnostic_completed', 'writing_diagnostic', 'writing_performance', 'writing_summary'),
            'classes': ('collapse',)
        }),
        ('Math', {
            'fields': ('math_diagnostic_completed', 'math_diagnostic', 'math_performance', 'math_summary'),
            'classes': ('collapse',)
        }),
        ('Recommendations', {
            'fields': ('recommended_lessons',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def reading_status(self, obj):
        if obj.reading_diagnostic_completed:
            strengths = len(obj.get_strengths('reading'))
            weaknesses = len(obj.get_weaknesses('reading'))
            return format_html('<span style="color: green;">✓</span> {} strengths, {} weaknesses', strengths, weaknesses)
        return format_html('<span style="color: gray;">Not started</span>')
    reading_status.short_description = 'Reading'
    
    def writing_status(self, obj):
        if obj.writing_diagnostic_completed:
            strengths = len(obj.get_strengths('writing'))
            weaknesses = len(obj.get_weaknesses('writing'))
            return format_html('<span style="color: green;">✓</span> {} strengths, {} weaknesses', strengths, weaknesses)
        return format_html('<span style="color: gray;">Not started</span>')
    writing_status.short_description = 'Writing'
    
    def math_status(self, obj):
        if obj.math_diagnostic_completed:
            strengths = len(obj.get_strengths('math'))
            weaknesses = len(obj.get_weaknesses('math'))
            return format_html('<span style="color: green;">✓</span> {} strengths, {} weaknesses', strengths, weaknesses)
        return format_html('<span style="color: gray;">Not started</span>')
    math_status.short_description = 'Math'
    
    def reading_summary(self, obj):
        return self._format_summary(obj, 'reading')
    reading_summary.short_description = 'Reading Analysis'
    
    def writing_summary(self, obj):
        return self._format_summary(obj, 'writing')
    writing_summary.short_description = 'Writing Analysis'
    
    def math_summary(self, obj):
        return self._format_summary(obj, 'math')
    math_summary.short_description = 'Math Analysis'
    
    def _format_summary(self, obj, category):
        if not getattr(obj, f'{category}_diagnostic_completed'):
            return 'Diagnostic not completed'
        
        strengths = obj.get_strengths(category)
        weaknesses = obj.get_weaknesses(category)
        improving = obj.get_improving(category)
        
        html = '<div style="font-family: monospace;">'
        
        if strengths:
            html += '<strong style="color: green;">Strengths (≥80%):</strong><br>'
            for s in strengths:
                html += f'&nbsp;&nbsp;• {s["name"]}: {s["percentage"]}% ({s["correct"]}/{s["total"]})<br>'
        
        if improving:
            html += '<strong style="color: orange;">Improving (60-79%):</strong><br>'
            for i in improving:
                html += f'&nbsp;&nbsp;• {i["name"]}: {i["percentage"]}% ({i["correct"]}/{i["total"]})<br>'
        
        if weaknesses:
            html += '<strong style="color: red;">Weaknesses (<60%):</strong><br>'
            for w in weaknesses:
                html += f'&nbsp;&nbsp;• {w["name"]}: {w["percentage"]}% ({w["correct"]}/{w["total"]})<br>'
        
        html += '</div>'
        return format_html(html)


@admin.register(LessonAttempt)
class LessonAttemptAdmin(admin.ModelAdmin):
    """Admin interface for lesson attempts"""
    list_display = ['user_display', 'lesson', 'score', 'correct_count', 'total_questions', 'is_diagnostic_attempt', 'completed_at']
    list_filter = ['is_diagnostic_attempt', 'lesson__lesson_type', 'completed_at']
    search_fields = ['user__email', 'lesson__title']
    readonly_fields = ['id', 'user', 'lesson', 'score', 'correct_count', 'total_questions', 'time_spent_seconds', 'answers_data', 'is_diagnostic_attempt', 'completed_at', 'created_at']
    ordering = ['-completed_at']
    
    def user_display(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_display.short_description = 'User'

