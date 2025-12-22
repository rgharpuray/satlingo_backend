from django.contrib import admin
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
import nested_admin
import os
import json
import threading
from django.conf import settings
from .models import Passage, Question, QuestionOption, User, UserSession, UserProgress, UserAnswer, PassageAnnotation, PassageIngestion, Lesson, LessonQuestion, LessonQuestionOption, LessonIngestion, WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption, WritingSectionIngestion
from .ingestion_utils import (
    extract_text_from_image, extract_text_from_pdf, extract_text_from_multiple_images,
    extract_text_from_docx, extract_text_from_txt, extract_text_from_document,
    parse_passage_with_ai, create_passage_from_parsed_data, process_ingestion
)
from .lesson_ingestion_utils import process_lesson_ingestion
from .writing_ingestion_utils import process_writing_ingestion
from .writing_gpt_utils import convert_document_to_writing_json


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
    """Custom form for file upload - supports multiple files"""
    file = forms.FileField(
        required=True,
        help_text="Upload one or more files: images (PNG, JPG), PDFs, Word documents (.docx, .doc), or text files (.txt) containing passages with questions. Hold Ctrl/Cmd to select multiple files.",
        widget=MultipleFileInput(attrs={'accept': 'image/*,application/pdf,.pdf,.docx,.doc,text/plain,.txt'})
    )
    
    class Meta:
        model = PassageIngestion
        fields = ['file']
    
    def clean_file(self):
        """Handle multiple file uploads - return first file for validation"""
        # The widget's value_from_datadict should return the first file
        # This satisfies the required field validation
        # save_model will handle all files via request.FILES.getlist('file')
        data = self.cleaned_data.get('file')
        return data


@admin.register(PassageIngestion)
class PassageIngestionAdmin(admin.ModelAdmin):
    """Admin interface for passage ingestion"""
    form = PassageIngestionForm
    list_display = ['file_name', 'file_type', 'status', 'created_passage_link', 'created_at', 'process_action']
    list_filter = ['status', 'file_type', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = ['id', 'file_name', 'file_path', 'file_type', 'extracted_text_preview', 'status', 'error_message', 'created_passage_link', 'created_at', 'updated_at']
    actions = ['process_selected']
    
    class Media:
        js = ('admin/js/ingestion_admin.js',)
    
    fieldsets = (
        ('File Upload', {
            'fields': ('file',),
            'description': 'You can select multiple files at once by holding Ctrl (Windows/Linux) or Cmd (Mac) while clicking files.'
        }),
        ('Processing Status', {
            'fields': ('id', 'status', 'file_path', 'error_message')
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
                process_ingestion(ingestion)
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
        """Override save to handle file upload and process ingestion - supports multiple files"""
        # Handle file upload for new objects - check request.FILES directly for multiple files
        if not change:
            uploaded_files = request.FILES.getlist('file')
            
            # Fallback to single file if multiple not available
            if not uploaded_files:
                uploaded_file = form.cleaned_data.get('file')
                if uploaded_file:
                    uploaded_files = [uploaded_file]
            
            if uploaded_files:
                # Use transaction to prevent database locking issues
                with transaction.atomic():
                    # Save all files and collect their paths
                    media_dir = settings.MEDIA_ROOT / 'ingestions'
                    media_dir.mkdir(parents=True, exist_ok=True)
                    
                    import uuid
                    file_paths = []
                    file_names = []
                    file_type = None
                    
                    for uploaded_file in uploaded_files:
                        # Save file to media directory
                        file_ext = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        file_path = media_dir / unique_filename
                        
                        with open(file_path, 'wb+') as destination:
                            for chunk in uploaded_file.chunks():
                                destination.write(chunk)
                        
                        file_paths.append(str(file_path))
                        file_names.append(uploaded_file.name)
                        
                        # Determine file type
                        ext = file_ext.lower()
                        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                            if file_type is None:
                                file_type = 'image'
                        elif ext == '.pdf':
                            if file_type is None:
                                file_type = 'pdf'
                        elif ext == '.docx':
                            if file_type is None:
                                file_type = 'docx'
                        elif ext == '.doc':
                            # Legacy .doc files - note that extraction may not work perfectly
                            if file_type is None:
                                file_type = 'docx'  # Try to process as docx, will show error if fails
                        elif ext == '.txt':
                            if file_type is None:
                                file_type = 'txt'
                    
                    if file_type is None:
                        file_type = 'unknown'
                    
                    # Create ONE ingestion object for all files (they're screenshots of the same document)
                    ingestion = PassageIngestion()
                    ingestion.file_name = f"{len(file_names)} files: {', '.join(file_names[:3])}" + (f" and {len(file_names)-3} more" if len(file_names) > 3 else "")
                    ingestion.file_path = file_paths[0]  # Primary file for backward compatibility
                    ingestion.file_paths = file_paths  # All file paths
                    ingestion.file_type = file_type
                    ingestion.save()
                    
                    created_ingestions = [ingestion]
                
                # Process ingestions asynchronously in background threads
                def process_in_background(ingestion_id):
                    """Process ingestion in background thread"""
                    import traceback
                    from django.db import connection
                    # Close the connection from the main thread
                    connection.close()
                    # Get fresh connection for this thread
                    from django import db
                    db.connections.close_all()
                    
                    # Get the ingestion object in this thread
                    try:
                        ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                        process_ingestion(ingestion)
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
                
                # Start background processing for each ingestion
                for ingestion in created_ingestions:
                    thread = threading.Thread(target=process_in_background, args=(ingestion.pk,))
                    thread.daemon = True
                    thread.start()
                
                # Show success message
                from django.contrib import messages
                if len(created_ingestions) > 1:
                    messages.success(request, f"Successfully uploaded {len(created_ingestions)} files. Processing is happening in the background - check back in a moment to see results.")
                    messages.info(request, "💡 Tip: If processing gets stuck, select the ingestion(s) and use the 'Process selected ingestions' action, or run: heroku run python manage.py process_ingestions --app keuvi")
                else:
                    messages.success(request, f"Successfully uploaded {created_ingestions[0].file_name}. Processing is happening in the background - check back in a moment to see results.")
                    messages.info(request, "💡 Tip: If processing gets stuck, select the ingestion and use the 'Process selected ingestions' action, or run: heroku run python manage.py process_ingestions --id <id> --app keuvi")
                
                # Store first ingestion ID for redirect in response_add
                if created_ingestions:
                    request._ingestion_redirect_id = created_ingestions[0].pk
                
                # Don't save the original obj since we created separate ones
                return
            else:
                # No files uploaded
                from django.contrib import messages
                messages.error(request, "No files were uploaded.")
                return
        
        # For editing existing objects - auto-process if pending/failed
        if change:
            super().save_model(request, obj, form, change)
            # Auto-process if it has files and is pending/failed
            if obj.file_path and obj.status in ['pending', 'failed']:
                # Mark as processing and start background processing
                obj.status = 'processing'
                obj.save()
                
                # Process in background
                def process_in_background(ingestion_id):
                    import traceback
                    from django.db import connection
                    connection.close()
                    from django import db
                    db.connections.close_all()
                    
                    try:
                        ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                        process_ingestion(ingestion)
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
    
    class Meta:
        model = LessonIngestion
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
            'fields': ('file', 'use_gpt_conversion'),
            'description': 'Upload a JSON file OR a document (PDF, DOCX, TXT). Documents will be automatically converted to JSON using GPT. Check "Use GPT conversion" to force GPT conversion even for JSON files.'
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
        if obj.parsed_data:
            preview = json.dumps(obj.parsed_data, indent=2)[:1000] + '...' if len(json.dumps(obj.parsed_data)) > 1000 else json.dumps(obj.parsed_data, indent=2)
            return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
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
                
                # Parse JSON or convert document
                try:
                    if is_json:
                        # Direct JSON parsing
                        with open(file_path, 'r', encoding='utf-8') as f:
                            obj.parsed_data = json.load(f)
                    elif should_use_gpt and is_document:
                        # Convert document to JSON using GPT
                        from .lesson_gpt_utils import convert_document_to_lesson_json
                        obj.status = 'processing'
                        obj.error_message = 'Converting document to JSON using GPT...'
                        obj.save()  # Save first to get the ID
                        
                        # Convert document
                        lesson_data = convert_document_to_lesson_json(str(file_path), uploaded_file.name)
                        obj.parsed_data = lesson_data
                        obj.error_message = f'✓ Successfully converted document to JSON using GPT.'
                    else:
                        raise ValueError(f'Unsupported file type: {file_ext}. Use JSON or enable GPT conversion for documents.')
                except Exception as e:
                    obj.status = 'failed'
                    obj.error_message = f'Failed to process file: {str(e)}'
                
                # Save ingestion
                obj.save()
                
                # Process in background
                if obj.status != 'failed' and obj.parsed_data:
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
        else:
            super().save_model(request, obj, form, change)


@admin.register(Lesson)
class LessonAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for lessons"""
    list_display = ['title', 'lesson_id', 'difficulty', 'tier', 'question_count', 'created_at']
    list_filter = ['difficulty', 'tier', 'created_at']
    search_fields = ['title', 'lesson_id', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at', 'question_count_display']
    inlines = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'lesson_id', 'title', 'difficulty', 'tier')
        }),
        ('Content', {
            'fields': ('chunks', 'content'),
        }),
        ('Metadata', {
            'fields': ('question_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
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


@admin.register(LessonQuestion)
class LessonQuestionAdmin(nested_admin.NestedModelAdmin):
    """Admin interface for lesson questions"""
    list_display = ['text_short', 'lesson', 'order', 'correct_answer_index']
    list_filter = ['lesson', 'created_at']
    search_fields = ['text', 'lesson__title']
    inlines = []
    
    def text_short(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_short.short_description = 'Question'


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
        if obj.parsed_data:
            preview = json.dumps(obj.parsed_data, indent=2)[:1000] + '...' if len(json.dumps(obj.parsed_data)) > 1000 else json.dumps(obj.parsed_data, indent=2)
            return format_html('<pre style="max-height: 200px; overflow: auto; font-size: 11px;">{}</pre>', escape(preview))
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
    list_display = ['title', 'difficulty', 'tier', 'selection_count', 'question_count', 'created_at']
    list_filter = ['difficulty', 'tier', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'content', 'difficulty', 'tier')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
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
