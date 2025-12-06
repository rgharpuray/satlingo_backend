from django.contrib import admin
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
import nested_admin
import os
import threading
from django.conf import settings
from .models import Passage, Question, QuestionOption, User, UserSession, UserProgress, UserAnswer, PassageAnnotation, PassageIngestion
from .ingestion_utils import (
    extract_text_from_image, extract_text_from_pdf, extract_text_from_multiple_images,
    extract_text_from_docx, extract_text_from_txt, extract_text_from_document,
    parse_passage_with_ai, create_passage_from_parsed_data
)


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
        """Display processing status - processing happens automatically"""
        if obj.status == 'processing':
            # Show progress message if available
            progress_msg = obj.error_message if obj.error_message and 'Step' in obj.error_message else 'Processing...'
            return format_html(
                '<span style="color: orange; font-weight: bold;">⏳ {}</span>',
                progress_msg
            )
        elif obj.status == 'completed':
            success_msg = obj.error_message if obj.error_message and '✓' in obj.error_message else 'Completed'
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', success_msg)
        elif obj.status == 'failed':
            error_msg = obj.error_message[:150] + '...' if obj.error_message and len(obj.error_message) > 150 else (obj.error_message or 'Unknown error')
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Failed</span><br>'
                '<small style="color: #999; display: block; margin-top: 4px; max-width: 300px;">{}</small>',
                error_msg
            )
        elif obj.status == 'pending' and obj.file_path:
            # Auto-process pending items
            return format_html('<span style="color: #666;">Will process automatically...</span>')
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
        processed = 0
        failed = 0
        
        def process_in_background(ingestion_id):
            """Process ingestion in background thread"""
            from django.db import connection
            connection.close()
            from django import db
            db.connections.close_all()
            
            ingestion = PassageIngestion.objects.get(pk=ingestion_id)
            try:
                process_ingestion(ingestion)
            except Exception as e:
                ingestion.status = 'failed'
                ingestion.error_message = str(e)
                ingestion.save()
        
        for ingestion in queryset:
            if ingestion.status in ['pending', 'failed'] and ingestion.file_path:
                # Mark as processing immediately
                ingestion.status = 'processing'
                ingestion.save()
                
                # Process in background thread
                thread = threading.Thread(target=process_in_background, args=(ingestion.pk,))
                thread.daemon = True
                thread.start()
                processed += 1
        
        if processed > 0:
            self.message_user(request, f"Started processing {processed} ingestion(s) in the background. The page will refresh automatically to show status updates.", level='SUCCESS')
        else:
            self.message_user(request, "No ingestions available to process.", level='WARNING')
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
                    from django.db import connection
                    # Close the connection from the main thread
                    connection.close()
                    # Get fresh connection for this thread
                    from django import db
                    db.connections.close_all()
                    
                    # Get the ingestion object in this thread
                    ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                    try:
                        process_ingestion(ingestion)
                    except Exception as e:
                        ingestion.status = 'failed'
                        ingestion.error_message = str(e)
                        ingestion.save()
                
                # Start background processing for each ingestion
                for ingestion in created_ingestions:
                    thread = threading.Thread(target=process_in_background, args=(ingestion.pk,))
                    thread.daemon = True
                    thread.start()
                
                # Show success message
                from django.contrib import messages
                if len(created_ingestions) > 1:
                    messages.success(request, f"Successfully uploaded {len(created_ingestions)} files. Processing is happening in the background - check back in a moment to see results.")
                else:
                    messages.success(request, f"Successfully uploaded {created_ingestions[0].file_name}. Processing is happening in the background - check back in a moment to see results.")
                
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
                    from django.db import connection
                    connection.close()
                    from django import db
                    db.connections.close_all()
                    
                    ingestion = PassageIngestion.objects.get(pk=ingestion_id)
                    try:
                        process_ingestion(ingestion)
                    except Exception as e:
                        ingestion.status = 'failed'
                        ingestion.error_message = str(e)
                        ingestion.save()
                
                thread = threading.Thread(target=process_in_background, args=(obj.pk,))
                thread.daemon = True
                thread.start()
                
                from django.contrib import messages
                messages.info(request, "Processing started automatically in the background.")
        else:
            super().save_model(request, obj, form, change)


def process_ingestion(ingestion):
    """Process an ingestion: extract text, parse with AI, create passage - ensures only ONE passage per ingestion"""
    # Prevent duplicate processing
    ingestion.refresh_from_db()
    if ingestion.status == 'processing':
        # Check if it's been processing too long (might be stuck)
        # If error_message contains progress, it's actively processing
        if not ingestion.error_message or 'Step' not in ingestion.error_message:
            # Might be stuck, allow reprocessing
            pass
        else:
            # Already processing, skip
            return
    if ingestion.status == 'completed' and ingestion.created_passage:
        # Already completed with a passage, skip to prevent duplicates
        return
    
    ingestion.status = 'processing'
    ingestion.error_message = 'Step 1/4: Starting processing...'
    ingestion.save()
    
    try:
        # Check if we have multiple files (screenshots of the same document)
        file_paths = ingestion.file_paths if hasattr(ingestion, 'file_paths') and ingestion.file_paths else []
        is_multiple_screenshots = len(file_paths) > 1
        
        # Step 2: Extract text from file(s)
        ingestion.error_message = f'Step 2/4: Extracting text from {ingestion.file_type} file(s)...'
        ingestion.save()
        
        if ingestion.file_type == 'image':
            if is_multiple_screenshots:
                # Multiple screenshots - combine them
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} images...'
                ingestion.save()
                extracted_text = extract_text_from_multiple_images(file_paths)
            else:
                # Single image
                extracted_text = extract_text_from_image(ingestion.file_path)
        elif ingestion.file_type == 'pdf':
            extracted_text = extract_text_from_pdf(ingestion.file_path)
        elif ingestion.file_type == 'docx':
            # For documents, if multiple files, combine them
            if is_multiple_screenshots:
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} document files...'
                ingestion.save()
                text_parts = []
                for idx, file_path in enumerate(file_paths, 1):
                    ingestion.error_message = f'Step 2/4: Processing document {idx}/{len(file_paths)}...'
                    ingestion.save()
                    text = extract_text_from_docx(file_path)
                    if text:
                        text_parts.append(text)
                extracted_text = "\n\n---DOCUMENT BREAK---\n\n".join(text_parts)
            else:
                extracted_text = extract_text_from_docx(ingestion.file_path)
        elif ingestion.file_type == 'txt':
            # For text files, if multiple files, combine them
            if is_multiple_screenshots:
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} text files...'
                ingestion.save()
                text_parts = []
                for idx, file_path in enumerate(file_paths, 1):
                    ingestion.error_message = f'Step 2/4: Processing text file {idx}/{len(file_paths)}...'
                    ingestion.save()
                    text = extract_text_from_txt(file_path)
                    if text:
                        text_parts.append(text)
                extracted_text = "\n\n---DOCUMENT BREAK---\n\n".join(text_parts)
            else:
                extracted_text = extract_text_from_txt(ingestion.file_path)
        else:
            raise Exception(f"Unsupported file type: {ingestion.file_type}")
        
        ingestion.extracted_text = extracted_text
        ingestion.error_message = f'Step 2/4: Text extraction complete. Extracted {len(extracted_text)} characters.'
        ingestion.save()
        
        # Step 3: Parse with AI - pass context about multiple screenshots
        ingestion.error_message = 'Step 3/4: Parsing text with AI to extract passage and questions...'
        ingestion.save()
        parsed_data = parse_passage_with_ai(extracted_text, is_multiple_screenshots=is_multiple_screenshots)
        
        ingestion.error_message = f'Step 3/4: AI parsing complete. Found {len(parsed_data.get("questions", []))} questions.'
        ingestion.save()
        
        # Step 4: Create passage
        ingestion.error_message = 'Step 4/4: Creating passage and questions in database...'
        ingestion.save()
        
        # Ensure only ONE passage is created per ingestion
        # If a passage already exists, don't create another
        if not ingestion.created_passage:
            # Create passage - this function creates exactly ONE passage
            passage = create_passage_from_parsed_data(parsed_data)
            ingestion.created_passage = passage
        
        ingestion.status = 'completed'
        ingestion.error_message = f'✓ Successfully created passage "{parsed_data.get("title", "Untitled")}" with {len(parsed_data.get("questions", []))} questions.'
        ingestion.save()
        
    except Exception as e:
        ingestion.status = 'failed'
        ingestion.error_message = f'✗ Error at {ingestion.error_message if "Step" in str(ingestion.error_message) else "processing"}: {str(e)}'
        ingestion.save()
        raise
