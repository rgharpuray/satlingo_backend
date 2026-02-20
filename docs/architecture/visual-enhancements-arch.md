# Visual Enhancements Architecture

**Architect**: PACT Architect Agent
**Date**: 2026-02-19
**Status**: Architecture Complete
**Phase**: Architect (PACT Framework)

---

## 1. Executive Summary

This document defines the architecture for adding Duolingo-style visual icons to Keuvi content. The design extends five existing models (Lesson, Passage, Header, MathSection, WritingSection) with icon support while maintaining backward compatibility and leveraging existing GCS infrastructure.

**Key Design Decisions**:
1. **URLField for icon storage**: Store icon URLs directly rather than file references for simplicity and CDN compatibility
2. **Nullable fields with fallback logic**: All new fields are nullable; API returns computed `icon_url` with category-based defaults
3. **Pre-generated sizes**: Start with storing multiple size variants (Option A from research) for simplicity
4. **Dual color fields**: `icon_color` for content models, `background_color` for Header model

---

## 2. System Context

### 2.1 Current Architecture

```
                                +------------------+
                                |   Mobile Apps    |
                                | (iOS / Android)  |
                                +--------+---------+
                                         |
                                         | REST API
                                         v
                            +------------+------------+
                            |    Django Backend       |
                            |  (satlingo_backend)     |
                            +------------+------------+
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
                    v                    v                    v
            +-------+------+    +--------+-------+   +--------+-------+
            |  PostgreSQL  |    |      GCS       |   |    Stripe      |
            |   Database   |    | (Media Assets) |   |  (Payments)    |
            +--------------+    +----------------+   +----------------+
```

### 2.2 Proposed Icon Flow

```
                      +------------------+
                      |   Admin Upload   |
                      |  or AI Generate  |
                      +--------+---------+
                               |
                               v
                      +--------+---------+
                      |  Django Backend  |
                      | (Process/Resize) |
                      +--------+---------+
                               |
                    +----------+----------+
                    |                     |
                    v                     v
            +-------+------+     +--------+-------+
            |  PostgreSQL  |     |      GCS       |
            | (icon_url)   |     |  icons/...     |
            +--------------+     +----------------+
                    |                     |
                    +----------+----------+
                               |
                               v
                      +--------+---------+
                      |   API Response   |
                      | (icon_url field) |
                      +--------+---------+
                               |
                               v
                      +--------+---------+
                      |   Mobile Apps    |
                      | (AsyncImage/Coil)|
                      +------------------+
```

---

## 3. Component Architecture

### 3.1 Data Model Changes

#### 3.1.1 Lesson Model Extension

```python
# api/models.py - Add to Lesson model (line ~435)

class Lesson(models.Model):
    # ... existing fields ...

    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to lesson icon image (256x256 WebP recommended)"
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
```

#### 3.1.2 Passage Model Extension

```python
# api/models.py - Add to Passage model (line ~14)

class Passage(models.Model):
    # ... existing fields ...

    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to passage icon image (256x256 WebP recommended)"
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
```

#### 3.1.3 Header Model Extension

```python
# api/models.py - Add to Header model (line ~486)

class Header(models.Model):
    # ... existing fields ...

    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to header/unit icon image (256x256 WebP recommended)"
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
```

#### 3.1.4 MathSection Model Extension

```python
# api/models.py - Add to MathSection model (line ~978)

class MathSection(models.Model):
    # ... existing fields ...

    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to math section icon image (256x256 WebP recommended)"
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
```

#### 3.1.5 WritingSection Model Extension

```python
# api/models.py - Add to WritingSection model (line ~696)

class WritingSection(models.Model):
    # ... existing fields ...

    # Visual Enhancement Fields
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to writing section icon image (256x256 WebP recommended)"
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
```

### 3.2 Color Palette Constants

Add a new constants file for shared color definitions:

```python
# api/constants.py (new file)

# Duolingo-inspired color palette for icons
ICON_COLOR_CHOICES = [
    ('#58CC02', 'Green - Primary'),       # Main Duolingo green
    ('#1CB0F6', 'Blue - Skills'),         # Skill icons
    ('#FF9600', 'Orange - Practice'),     # Practice/review
    ('#FF4B4B', 'Red - Challenge'),       # Hard/challenge
    ('#CE82FF', 'Purple - Special'),      # Premium/special
    ('#FFD900', 'Yellow - Achievement'),  # Achievements/XP
]

# Default colors by category
DEFAULT_COLORS = {
    'reading': '#1CB0F6',   # Blue
    'writing': '#CE82FF',   # Purple
    'math': '#FF9600',      # Orange
}

# Default icon URLs by category (to be populated with actual URLs)
DEFAULT_ICONS = {
    'reading': None,   # Will be: https://storage.googleapis.com/{bucket}/icons/defaults/reading.webp
    'writing': None,   # Will be: https://storage.googleapis.com/{bucket}/icons/defaults/writing.webp
    'math': None,      # Will be: https://storage.googleapis.com/{bucket}/icons/defaults/math.webp
}
```

---

## 4. Data Architecture

### 4.1 GCS Storage Structure

```
{GS_BUCKET_NAME}/
  icons/
    lessons/
      {lesson_id}/
        icon.webp           # Master 256x256
        icon@2x.webp        # 128x128
        icon@1x.webp        # 64x64
    passages/
      {passage_id}/
        icon.webp
        icon@2x.webp
        icon@1x.webp
    headers/
      {header_id}/
        icon.webp
        icon@2x.webp
        icon@1x.webp
    math_sections/
      {section_id}/
        icon.webp
        icon@2x.webp
        icon@1x.webp
    writing_sections/
      {section_id}/
        icon.webp
        icon@2x.webp
        icon@1x.webp
    defaults/
      reading.webp          # Default reading icon
      reading@2x.webp
      reading@1x.webp
      writing.webp          # Default writing icon
      writing@2x.webp
      writing@1x.webp
      math.webp             # Default math icon
      math@2x.webp
      math@1x.webp
```

### 4.2 Icon URL Format

Icons will be stored with the master size (256x256) URL in the database. Mobile apps can request specific sizes by modifying the URL:

```
# Stored URL (master):
https://storage.googleapis.com/{bucket}/icons/lessons/{id}/icon.webp

# Requested URLs by density:
icon.webp      -> 256x256 (master, @4x)
icon@2x.webp   -> 128x128
icon@1x.webp   -> 64x64
```

### 4.3 Database Migration

```python
# api/migrations/XXXX_add_visual_enhancement_fields.py

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('api', 'previous_migration'),  # Replace with actual dependency
    ]

    operations = [
        # Lesson fields
        migrations.AddField(
            model_name='lesson',
            name='icon_url',
            field=models.URLField(
                blank=True,
                help_text='URL to lesson icon image (256x256 WebP recommended)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='lesson',
            name='icon_color',
            field=models.CharField(
                blank=True,
                help_text='Primary accent color for icon/UI (hex format, e.g., #58CC02)',
                max_length=7,
                null=True,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid hex color code (e.g., #58CC02)',
                    regex='^#[0-9A-Fa-f]{6}$'
                )],
            ),
        ),

        # Passage fields
        migrations.AddField(
            model_name='passage',
            name='icon_url',
            field=models.URLField(
                blank=True,
                help_text='URL to passage icon image (256x256 WebP recommended)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='passage',
            name='icon_color',
            field=models.CharField(
                blank=True,
                help_text='Primary accent color for icon/UI (hex format, e.g., #58CC02)',
                max_length=7,
                null=True,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid hex color code (e.g., #58CC02)',
                    regex='^#[0-9A-Fa-f]{6}$'
                )],
            ),
        ),

        # Header fields
        migrations.AddField(
            model_name='header',
            name='icon_url',
            field=models.URLField(
                blank=True,
                help_text='URL to header/unit icon image (256x256 WebP recommended)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='header',
            name='background_color',
            field=models.CharField(
                blank=True,
                help_text='Header background/accent color (hex format, e.g., #1CB0F6)',
                max_length=7,
                null=True,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid hex color code (e.g., #1CB0F6)',
                    regex='^#[0-9A-Fa-f]{6}$'
                )],
            ),
        ),

        # MathSection fields
        migrations.AddField(
            model_name='mathsection',
            name='icon_url',
            field=models.URLField(
                blank=True,
                help_text='URL to math section icon image (256x256 WebP recommended)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='mathsection',
            name='icon_color',
            field=models.CharField(
                blank=True,
                help_text='Primary accent color for icon/UI (hex format, e.g., #58CC02)',
                max_length=7,
                null=True,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid hex color code (e.g., #58CC02)',
                    regex='^#[0-9A-Fa-f]{6}$'
                )],
            ),
        ),

        # WritingSection fields
        migrations.AddField(
            model_name='writingsection',
            name='icon_url',
            field=models.URLField(
                blank=True,
                help_text='URL to writing section icon image (256x256 WebP recommended)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='writingsection',
            name='icon_color',
            field=models.CharField(
                blank=True,
                help_text='Primary accent color for icon/UI (hex format, e.g., #58CC02)',
                max_length=7,
                null=True,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid hex color code (e.g., #58CC02)',
                    regex='^#[0-9A-Fa-f]{6}$'
                )],
            ),
        ),
    ]
```

---

## 5. API Specifications

### 5.1 Serializer Updates

#### 5.1.1 HeaderSerializer

```python
# api/serializers.py - Update HeaderSerializer

class HeaderSerializer(serializers.ModelSerializer):
    """Serializer for headers"""
    effective_icon_url = serializers.SerializerMethodField()
    effective_background_color = serializers.SerializerMethodField()

    class Meta:
        model = Header
        fields = [
            'id', 'title', 'category', 'display_order',
            'icon_url', 'background_color',
            'effective_icon_url', 'effective_background_color'
        ]

    def get_effective_icon_url(self, obj):
        """Return icon_url or category-based default"""
        if obj.icon_url:
            return obj.icon_url
        from api.constants import DEFAULT_ICONS
        return DEFAULT_ICONS.get(obj.category)

    def get_effective_background_color(self, obj):
        """Return background_color or category-based default"""
        if obj.background_color:
            return obj.background_color
        from api.constants import DEFAULT_COLORS
        return DEFAULT_COLORS.get(obj.category, '#1CB0F6')
```

#### 5.1.2 PassageListSerializer

```python
# api/serializers.py - Update PassageListSerializer

class PassageListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    effective_icon_url = serializers.SerializerMethodField()
    effective_icon_color = serializers.SerializerMethodField()

    class Meta:
        model = Passage
        fields = [
            'id', 'title', 'content', 'difficulty', 'tier', 'is_diagnostic',
            'header', 'order_within_header',
            'icon_url', 'icon_color',
            'effective_icon_url', 'effective_icon_color',
            'question_count', 'attempt_count', 'attempt_summary',
            'created_at', 'updated_at'
        ]

    def get_effective_icon_url(self, obj):
        """Return icon_url or category-based default"""
        if obj.icon_url:
            return obj.icon_url
        from api.constants import DEFAULT_ICONS
        return DEFAULT_ICONS.get('reading')

    def get_effective_icon_color(self, obj):
        """Return icon_color or category-based default"""
        if obj.icon_color:
            return obj.icon_color
        from api.constants import DEFAULT_COLORS
        return DEFAULT_COLORS.get('reading', '#1CB0F6')

    # ... existing methods ...
```

#### 5.1.3 LessonListSerializer

```python
# api/serializers.py - Update LessonListSerializer

class LessonListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    header = HeaderSerializer(read_only=True)
    effective_icon_url = serializers.SerializerMethodField()
    effective_icon_color = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'lesson_id', 'title', 'difficulty', 'tier', 'lesson_type',
            'is_diagnostic', 'question_count', 'header', 'order_within_header',
            'icon_url', 'icon_color',
            'effective_icon_url', 'effective_icon_color',
            'created_at'
        ]

    def get_effective_icon_url(self, obj):
        """Return icon_url or category-based default"""
        if obj.icon_url:
            return obj.icon_url
        from api.constants import DEFAULT_ICONS
        return DEFAULT_ICONS.get(obj.lesson_type)

    def get_effective_icon_color(self, obj):
        """Return icon_color or category-based default"""
        if obj.icon_color:
            return obj.icon_color
        from api.constants import DEFAULT_COLORS
        return DEFAULT_COLORS.get(obj.lesson_type, '#58CC02')

    def get_question_count(self, obj):
        return obj.questions.count()
```

#### 5.1.4 MathSectionListSerializer

```python
# api/serializers.py - Update MathSectionListSerializer

class MathSectionListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    effective_icon_url = serializers.SerializerMethodField()
    effective_icon_color = serializers.SerializerMethodField()

    class Meta:
        model = MathSection
        fields = [
            'id', 'section_id', 'title', 'difficulty', 'tier',
            'header', 'order_within_header',
            'icon_url', 'icon_color',
            'effective_icon_url', 'effective_icon_color',
            'question_count', 'asset_count', 'attempt_count', 'attempt_summary',
            'created_at'
        ]

    def get_effective_icon_url(self, obj):
        """Return icon_url or category-based default"""
        if obj.icon_url:
            return obj.icon_url
        from api.constants import DEFAULT_ICONS
        return DEFAULT_ICONS.get('math')

    def get_effective_icon_color(self, obj):
        """Return icon_color or category-based default"""
        if obj.icon_color:
            return obj.icon_color
        from api.constants import DEFAULT_COLORS
        return DEFAULT_COLORS.get('math', '#FF9600')

    # ... existing methods ...
```

#### 5.1.5 WritingSectionListSerializer

```python
# api/serializers.py - Update WritingSectionListSerializer

class WritingSectionListSerializer(serializers.ModelSerializer):
    header = HeaderSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    selection_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    attempt_summary = serializers.SerializerMethodField()
    effective_icon_url = serializers.SerializerMethodField()
    effective_icon_color = serializers.SerializerMethodField()

    class Meta:
        model = WritingSection
        fields = [
            'id', 'title', 'difficulty', 'tier',
            'header', 'order_within_header',
            'icon_url', 'icon_color',
            'effective_icon_url', 'effective_icon_color',
            'question_count', 'selection_count',
            'attempt_count', 'attempt_summary',
            'created_at'
        ]

    def get_effective_icon_url(self, obj):
        """Return icon_url or category-based default"""
        if obj.icon_url:
            return obj.icon_url
        from api.constants import DEFAULT_ICONS
        return DEFAULT_ICONS.get('writing')

    def get_effective_icon_color(self, obj):
        """Return icon_color or category-based default"""
        if obj.icon_color:
            return obj.icon_color
        from api.constants import DEFAULT_COLORS
        return DEFAULT_COLORS.get('writing', '#CE82FF')

    # ... existing methods ...
```

### 5.2 API Response Examples

#### 5.2.1 Lesson List Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "lesson_id": "commas",
  "title": "Using Commas Correctly",
  "difficulty": "Medium",
  "tier": "free",
  "lesson_type": "writing",
  "is_diagnostic": false,
  "question_count": 5,
  "header": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "Punctuation",
    "category": "writing",
    "display_order": 10,
    "icon_url": "https://storage.googleapis.com/keuvi-app/icons/headers/660e.../icon.webp",
    "background_color": "#CE82FF",
    "effective_icon_url": "https://storage.googleapis.com/keuvi-app/icons/headers/660e.../icon.webp",
    "effective_background_color": "#CE82FF"
  },
  "order_within_header": 3,
  "icon_url": null,
  "icon_color": null,
  "effective_icon_url": "https://storage.googleapis.com/keuvi-app/icons/defaults/writing.webp",
  "effective_icon_color": "#CE82FF",
  "created_at": "2026-02-19T10:30:00Z"
}
```

---

## 6. Technology Decisions

### 6.1 Image Format: WebP

**Rationale**:
- Excellent compression (25-35% smaller than PNG)
- Full transparency support
- Supported on iOS 14+ and all Android versions
- Recommended by PREPARE phase research

### 6.2 Icon Sizes: Pre-generated Variants

**Rationale**:
- Simpler implementation than on-the-fly resizing
- Faster serving (no processing required)
- Lower infrastructure complexity
- Can migrate to imgproxy later if needed

**Sizes**:
- 256x256 (master/@4x for xxxhdpi Android)
- 128x128 (@2x for iOS Retina, xhdpi Android)
- 64x64 (@1x for standard displays)

### 6.3 Storage: GCS with Existing Infrastructure

**Rationale**:
- Already configured in `storage_backend.py`
- Uses existing bucket and credentials
- Consistent with current asset storage pattern

### 6.4 Default Icons: Category-Based Fallback

**Rationale**:
- Consistent UI even without custom icons
- Three default icons (reading, writing, math) cover all content
- Low maintenance (3 icons to design/generate)

---

## 7. Security Architecture

### 7.1 Upload Security

- **File Type Validation**: Only accept PNG, JPEG, WebP formats
- **File Size Limit**: Maximum 2MB per upload
- **Content-Type Verification**: Check magic bytes, not just extension
- **Filename Sanitization**: Generate UUID-based filenames, ignore user input

### 7.2 Access Control

- **Public Read**: Icons served with public URLs (no signed URLs needed)
- **Admin Write**: Only staff users can upload icons via admin
- **No User Uploads**: Users cannot upload custom icons (prevents moderation burden)

### 7.3 URL Validation

```python
# api/validators.py (new file or add to existing)

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.conf import settings

def validate_icon_url(value):
    """Validate that icon URL is from our GCS bucket or empty"""
    if not value:
        return

    url_validator = URLValidator()
    url_validator(value)  # Validates URL format

    bucket = getattr(settings, 'GS_BUCKET_NAME', '')
    allowed_prefixes = [
        f"https://storage.googleapis.com/{bucket}/icons/",
    ]

    if not any(value.startswith(prefix) for prefix in allowed_prefixes):
        raise ValidationError(
            f"Icon URL must be from the Keuvi GCS bucket. "
            f"Expected prefix: {allowed_prefixes[0]}"
        )
```

---

## 8. Admin Interface Changes

### 8.1 Icon Upload Widget

Create a custom admin widget for icon upload with preview:

```python
# api/admin_widgets.py (new file)

from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class IconUploadWidget(forms.ClearableFileInput):
    """Custom file input with image preview and color picker"""
    template_name = 'admin/widgets/icon_upload.html'

    def __init__(self, attrs=None, preview_url_field=None):
        self.preview_url_field = preview_url_field
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['preview_url'] = value if isinstance(value, str) else None
        return context


class ColorPickerWidget(forms.TextInput):
    """Color picker input with preview"""
    template_name = 'admin/widgets/color_picker.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'type': 'color',
            'style': 'width: 60px; height: 40px; padding: 2px; cursor: pointer;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
```

### 8.2 Admin Form Updates

```python
# api/admin.py - Add to existing admin classes

# Add to LessonAdmin fieldsets
fieldsets = (
    ('Basic Information', {
        'fields': ('id', 'lesson_id', 'title', 'lesson_type', 'is_diagnostic'),
    }),
    ('Visual Settings', {
        'fields': ('icon_url', 'icon_color'),
        'description': 'Icon URL and accent color for mobile display'
    }),
    # ... other fieldsets ...
)

# Similarly for PassageAdmin, HeaderAdmin, MathSectionAdmin, WritingSectionAdmin
```

### 8.3 Icon Upload Admin View

```python
# api/admin_views.py (new file or add to existing)

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from PIL import Image
import io
import tempfile
import os
from .storage_backend import upload_to_gcs

@staff_member_required
@require_POST
@csrf_protect
def upload_icon(request):
    """Handle icon upload, resize, and store in GCS"""
    if 'icon' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['icon']
    model_type = request.POST.get('model_type')  # lesson, passage, etc.
    model_id = request.POST.get('model_id')

    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/webp']
    if uploaded_file.content_type not in allowed_types:
        return JsonResponse({'error': 'Invalid file type. Use PNG, JPEG, or WebP'}, status=400)

    # Validate file size (2MB max)
    if uploaded_file.size > 2 * 1024 * 1024:
        return JsonResponse({'error': 'File too large. Maximum 2MB'}, status=400)

    try:
        # Open and process image
        img = Image.open(uploaded_file)

        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ('RGBA', 'P'):
            # Keep alpha for WebP
            pass

        # Resize to standard sizes
        sizes = [
            (256, 256, 'icon.webp'),
            (128, 128, 'icon@2x.webp'),
            (64, 64, 'icon@1x.webp'),
        ]

        urls = {}
        for width, height, filename in sizes:
            resized = img.copy()
            resized.thumbnail((width, height), Image.Resampling.LANCZOS)

            # Create a square canvas
            canvas = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            paste_x = (width - resized.size[0]) // 2
            paste_y = (height - resized.size[1]) // 2
            canvas.paste(resized, (paste_x, paste_y))

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
                canvas.save(tmp, 'WebP', quality=90)
                tmp_path = tmp.name

            # Upload to GCS
            gcs_key = f"icons/{model_type}s/{model_id}/{filename}"
            url = upload_to_gcs(tmp_path, gcs_key, content_type='image/webp')

            # Clean up
            os.unlink(tmp_path)

            if filename == 'icon.webp':
                urls['master'] = url

        return JsonResponse({'url': urls['master']})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### 8.4 Admin URL Configuration

```python
# api/urls.py - Add admin upload URL

from .admin_views import upload_icon

urlpatterns = [
    # ... existing patterns ...
    path('admin/upload-icon/', upload_icon, name='admin_upload_icon'),
]
```

---

## 9. Implementation Roadmap

### Phase 1: Database & Models (Backend Coder)
**Estimated effort**: 2-3 hours

1. Create `api/constants.py` with color palette
2. Add model fields to Lesson, Passage, Header, MathSection, WritingSection
3. Add hex color validator
4. Generate and run migration
5. Verify migration on local database

**Deliverables**:
- `api/constants.py`
- Updated `api/models.py`
- Migration file
- Passing model tests

### Phase 2: Serializers & API (Backend Coder)
**Estimated effort**: 2-3 hours

1. Update HeaderSerializer with icon fields
2. Update PassageListSerializer with icon fields
3. Update LessonListSerializer with icon fields
4. Update MathSectionListSerializer with icon fields
5. Update WritingSectionListSerializer with icon fields
6. Add `effective_icon_url` and `effective_icon_color` methods

**Deliverables**:
- Updated `api/serializers.py`
- API response tests

### Phase 3: Admin Interface (Backend Coder)
**Estimated effort**: 3-4 hours

1. Create admin widgets (ColorPickerWidget)
2. Add upload_icon admin view
3. Update admin fieldsets for all relevant models
4. Add icon preview in admin list views
5. Create admin templates for widgets

**Deliverables**:
- `api/admin_widgets.py`
- `api/admin_views.py` (or additions)
- Updated `api/admin.py`
- Admin templates in `templates/admin/widgets/`

### Phase 4: Default Icons (Design/Asset)
**Estimated effort**: 2-3 hours

1. Generate or source default icons (reading, writing, math)
2. Create all size variants (256x256, 128x128, 64x64)
3. Upload to GCS at `icons/defaults/`
4. Update `DEFAULT_ICONS` in constants.py with actual URLs

**Deliverables**:
- 3 default icons in 3 sizes each
- Updated constants with URLs

### Phase 5: Testing & Documentation
**Estimated effort**: 2-3 hours

1. Unit tests for model fields and validators
2. Integration tests for serializers
3. Admin interface manual testing
4. API documentation updates

**Deliverables**:
- Test files
- Updated API documentation

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration fails on production | Low | High | Test migration on staging first; migration is additive (nullable fields) |
| GCS upload errors | Low | Medium | Use existing, proven upload_to_gcs function; add error handling |
| Image processing failures | Medium | Low | Validate file type/size before processing; clear error messages |

### 10.2 Performance Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Slow icon loading on mobile | Medium | Medium | Pre-generate sizes; use CDN; set proper cache headers |
| Large API response size | Low | Low | Icon URLs are small strings; minimal impact on payload |

### 10.3 Security Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Malicious file upload | Low | High | Validate file type, size; admin-only upload; sanitize filenames |
| URL injection | Low | Medium | Validate URLs against allowed GCS prefixes |

---

## 11. Quality Checklist

Before implementation is complete, verify:

- [ ] All five models have icon_url and icon_color/background_color fields
- [ ] Migration runs successfully without data loss
- [ ] Serializers include both raw and effective icon/color fields
- [ ] API responses maintain backward compatibility (new fields are optional)
- [ ] Admin interface allows icon upload and color selection
- [ ] Default icons exist in GCS and constants are updated
- [ ] Hex color validation works correctly
- [ ] Icon URL validation restricts to GCS bucket
- [ ] Upload handles PNG, JPEG, and WebP formats
- [ ] Pre-generated sizes (256, 128, 64) are created on upload
- [ ] Error handling covers all failure modes
- [ ] Tests cover model, serializer, and admin functionality

---

## 12. Handoff Summary

**1. Produced**: `/Users/rishi/argosventures/satlingo_backend/docs/architecture/visual-enhancements-arch.md`

**2. Key decisions**:
- URLField for icon storage (not FileField)
- Nullable fields with computed `effective_*` fallbacks
- Pre-generated size variants (256, 128, 64)
- Three default icons (reading, writing, math)
- Hex color validation with RegexValidator

**3. Implementation order**:
1. Models & migration (foundation)
2. Serializers (API contract)
3. Admin interface (content management)
4. Default icons (user experience)
5. Testing (quality assurance)

**4. Dependencies on external work**:
- Default icons need to be designed/generated (Phase 4)
- Mobile apps will need updates to consume new API fields (separate work)

**5. Open decisions for implementer**:
- Exact admin template styling
- Whether to add icon preview in list_display

---

*Architecture complete. Ready for handoff to Code phase.*
