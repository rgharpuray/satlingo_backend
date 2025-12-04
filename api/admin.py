from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
import nested_admin
import os
from django.conf import settings
from .models import Passage, Question, QuestionOption, User, UserSession, UserProgress, UserAnswer, PassageAnnotation, PassageIngestion
from .ingestion_utils import extract_text_from_image, extract_text_from_pdf, parse_passage_with_ai, create_passage_from_parsed_data


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


@admin.register(Passage)
class PassageAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for passages with inline questions, options, and annotations"""
    list_display = ['title', 'difficulty', 'tier', 'question_count', 'annotation_count', 'created_at', 'preview_link']
    list_filter = ['difficulty', 'tier', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display', 'annotation_count_display']
    inlines = [PassageAnnotationInline, QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'content', 'difficulty', 'tier')
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'annotation_count_display', 'created_at', 'updated_at'),
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
    
    class Media:
        css = {
            'all': ('admin/css/passage_admin.css',)
        }
        js = ('admin/js/passage_admin.js', 'admin/js/annotation_helper.js',)


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for individual questions"""
    list_display = ['short_text', 'passage', 'order', 'correct_answer_index', 'option_count', 'has_explanation']
    list_filter = ['passage', 'order', 'passage__difficulty', 'passage__tier']
    search_fields = ['text', 'passage__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [QuestionOptionInline]
    
    def get_queryset(self, request):
        """Optimize queryset for list view"""
        return super().get_queryset(request).select_related('passage')
    
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
    """Custom form for file upload"""
    file = forms.FileField(required=True, help_text="Upload an image (PNG, JPG) or PDF file containing a passage with questions")
    
    class Meta:
        model = PassageIngestion
        fields = ['file']


@admin.register(PassageIngestion)
class PassageIngestionAdmin(admin.ModelAdmin):
    """Admin interface for passage ingestion"""
    form = PassageIngestionForm
    list_display = ['file_name', 'file_type', 'status', 'created_passage_link', 'created_at', 'process_action']
    list_filter = ['status', 'file_type', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_path', 'extracted_text_preview', 'status', 'error_message', 'created_passage_link', 'created_at', 'updated_at']
    actions = ['process_selected']
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file',)
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_name', 'file_path', 'file_type', 'error_message')
        }),
        ('Results', {
            'fields': ('extracted_text_preview', 'created_passage_link'),
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
    
    def created_passage_link(self, obj):
        """Link to created passage"""
        if obj.created_passage:
            url = reverse('admin:api_passage_change', args=[obj.created_passage.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.created_passage.title)
        return '-'
    created_passage_link.short_description = 'Created Passage'
    
    def process_action(self, obj):
        """Display process button for manual triggering"""
        if obj.status in ['pending', 'failed'] and obj.file_path:
            # Use admin action URL
            url = reverse('admin:api_passageingestion_changelist')
            return format_html(
                '<a class="button" href="{}" onclick="if(confirm(\'Process this ingestion?\\nThis will extract text and create a passage.\')) {{ window.location.href=\'?action=process_selected&_selected_action={}\'; return false; }}">Process Now</a>',
                url, obj.pk
            )
        elif obj.status == 'processing':
            return format_html('<span style="color: orange;">Processing...</span>')
        elif obj.status == 'completed':
            return format_html('<span style="color: green;">✓ Completed</span>')
        return '-'
    process_action.short_description = 'Actions'
    
    def process_selected(self, request, queryset):
        """Admin action to process selected ingestions"""
        processed = 0
        for ingestion in queryset:
            if ingestion.status in ['pending', 'failed'] and ingestion.file_path:
                try:
                    process_ingestion(ingestion)
                    processed += 1
                except Exception as e:
                    self.message_user(request, f"Failed to process {ingestion.file_name}: {str(e)}", level='ERROR')
        self.message_user(request, f"Processed {processed} ingestion(s).", level='SUCCESS')
    process_selected.short_description = 'Process selected ingestions'
    
    def save_model(self, request, obj, form, change):
        """Override save to handle file upload and process ingestion"""
        # Handle file upload for new objects
        if not change and 'file' in form.cleaned_data:
            uploaded_file = form.cleaned_data['file']
            
            # Save file to media directory
            media_dir = settings.MEDIA_ROOT / 'ingestions'
            media_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename to avoid conflicts
            import uuid
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = media_dir / unique_filename
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            obj.file_name = uploaded_file.name
            obj.file_path = str(file_path)
            
            # Determine file type
            ext = file_ext.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                obj.file_type = 'image'
            elif ext == '.pdf':
                obj.file_type = 'pdf'
            else:
                obj.file_type = 'unknown'
        
        super().save_model(request, obj, form, change)
        
        # Process ingestion automatically if it's a new object with a file
        # Note: Processing happens synchronously, so it may take a moment
        if not change and obj.file_path:
            # Process in a try-except to handle errors gracefully
            try:
                process_ingestion(obj)
            except Exception as e:
                obj.status = 'failed'
                obj.error_message = str(e)
                obj.save()
                # Re-raise to show error message to user
                from django.contrib import messages
                messages.error(request, f"Ingestion processing failed: {str(e)}")


def process_ingestion(ingestion):
    """Process an ingestion: extract text, parse with AI, create passage"""
    ingestion.status = 'processing'
    ingestion.save()
    
    try:
        # Extract text from file
        if ingestion.file_type == 'image':
            extracted_text = extract_text_from_image(ingestion.file_path)
        elif ingestion.file_type == 'pdf':
            extracted_text = extract_text_from_pdf(ingestion.file_path)
        else:
            raise Exception(f"Unsupported file type: {ingestion.file_type}")
        
        ingestion.extracted_text = extracted_text
        ingestion.save()
        
        # Parse with AI
        parsed_data = parse_passage_with_ai(extracted_text)
        
        # Create passage
        passage = create_passage_from_parsed_data(parsed_data)
        
        ingestion.created_passage = passage
        ingestion.status = 'completed'
        ingestion.save()
        
    except Exception as e:
        ingestion.status = 'failed'
        ingestion.error_message = str(e)
        ingestion.save()
        raise
