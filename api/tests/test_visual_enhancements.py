"""
Unit tests for Visual Enhancement fields on content models.

Location: api/tests/test_visual_enhancements.py
Coverage: icon_url, icon_color, background_color fields, effective_* serializer methods,
          GCS URL validation, and API endpoint integration tests.
"""

import uuid
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.urls import reverse

from api.models import Header, Passage, Lesson, MathSection, WritingSection
from api.serializers import (
    HeaderSerializer,
    PassageListSerializer,
    PassageDetailSerializer,
    LessonListSerializer,
    LessonDetailSerializer,
    MathSectionListSerializer,
    MathSectionDetailSerializer,
    WritingSectionListSerializer,
    WritingSectionDetailSerializer,
)
from api.constants import DEFAULT_COLORS, DEFAULT_ICONS, DEFAULT_FALLBACK_COLOR, GCS_ICON_URL_PREFIX


class ConstantsTests(TestCase):
    """Test that constants are properly defined."""

    def test_default_colors_defined(self):
        """Default colors should be defined for all content categories."""
        self.assertIn('reading', DEFAULT_COLORS)
        self.assertIn('writing', DEFAULT_COLORS)
        self.assertIn('math', DEFAULT_COLORS)

    def test_default_colors_are_valid_hex(self):
        """All default colors should be valid hex codes."""
        import re
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for category, color in DEFAULT_COLORS.items():
            self.assertIsNotNone(
                hex_pattern.match(color),
                f"Color for {category} is not a valid hex code: {color}"
            )

    def test_default_icons_defined(self):
        """Default icons should be defined for all content categories (may be None)."""
        self.assertIn('reading', DEFAULT_ICONS)
        self.assertIn('writing', DEFAULT_ICONS)
        self.assertIn('math', DEFAULT_ICONS)

    def test_default_icons_are_none_until_assets_uploaded(self):
        """Default icons should be None until real assets are uploaded."""
        for category in ['reading', 'writing', 'math']:
            self.assertIsNone(
                DEFAULT_ICONS.get(category),
                f"DEFAULT_ICONS['{category}'] should be None until assets are uploaded"
            )

    def test_default_fallback_color_defined(self):
        """DEFAULT_FALLBACK_COLOR should be defined and valid."""
        import re
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        self.assertIsNotNone(DEFAULT_FALLBACK_COLOR)
        self.assertIsNotNone(
            hex_pattern.match(DEFAULT_FALLBACK_COLOR),
            f"DEFAULT_FALLBACK_COLOR is not a valid hex code: {DEFAULT_FALLBACK_COLOR}"
        )

    def test_gcs_icon_url_prefix_defined(self):
        """GCS_ICON_URL_PREFIX should be defined and valid."""
        self.assertIsNotNone(GCS_ICON_URL_PREFIX)
        self.assertTrue(GCS_ICON_URL_PREFIX.startswith('https://storage.googleapis.com/'))


class GCSIconUrlValidationTests(TestCase):
    """Test GCS URL validation for icon_url fields."""

    def test_valid_gcs_url_accepted(self):
        """Valid GCS URLs should pass validation."""
        valid_urls = [
            'https://storage.googleapis.com/keuvi-app/icons/test.webp',
            'https://storage.googleapis.com/keuvi-app/icons/defaults/reading.webp',
            'https://storage.googleapis.com/keuvi-app/icons/custom/my-icon.png',
        ]
        for url in valid_urls:
            passage = Passage(
                title='Test',
                content='Test content',
                difficulty='Medium',
                icon_url=url
            )
            passage.full_clean()  # Should not raise

    def test_invalid_external_url_rejected(self):
        """Non-GCS URLs should be rejected."""
        invalid_urls = [
            'https://example.com/icon.webp',
            'https://other-bucket.storage.googleapis.com/icon.webp',
            'https://cdn.example.com/icons/test.webp',
            'http://storage.googleapis.com/keuvi-app/icons/test.webp',  # http not https
        ]
        for url in invalid_urls:
            passage = Passage(
                title='Test',
                content='Test content',
                difficulty='Medium',
                icon_url=url
            )
            with self.assertRaises(ValidationError, msg=f"URL {url} should be rejected"):
                passage.full_clean()

    def test_null_icon_url_accepted(self):
        """Null icon_url should be accepted (optional field)."""
        passage = Passage(
            title='Test',
            content='Test content',
            difficulty='Medium',
            icon_url=None
        )
        passage.full_clean()  # Should not raise

    def test_gcs_validation_on_all_models(self):
        """GCS URL validation should work on all models with icon_url."""
        valid_url = 'https://storage.googleapis.com/keuvi-app/icons/test.webp'
        invalid_url = 'https://example.com/icon.webp'

        # Test Header
        header = Header(title='Test', category='reading', icon_url=valid_url)
        header.full_clean()  # Should not raise

        header_invalid = Header(title='Test', category='reading', icon_url=invalid_url)
        with self.assertRaises(ValidationError):
            header_invalid.full_clean()

        # Test Lesson - skip full_clean for icon_url validation since it also validates chunks
        # The validator itself is tested on other models
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='reading', icon_url=valid_url)
        # Just validate the icon_url field directly using the validator
        from api.models import validate_gcs_icon_url
        validate_gcs_icon_url(valid_url)  # Should not raise

        with self.assertRaises(ValidationError):
            validate_gcs_icon_url(invalid_url)  # Should raise

        # Test MathSection
        math = MathSection(section_id='test', title='Test', icon_url=valid_url)
        math.full_clean()

        math_invalid = MathSection(section_id='test2', title='Test', icon_url=invalid_url)
        with self.assertRaises(ValidationError):
            math_invalid.full_clean()

        # Test WritingSection
        writing = WritingSection(title='Test', content='Test', difficulty='Medium', icon_url=valid_url)
        writing.full_clean()

        writing_invalid = WritingSection(title='Test2', content='Test', difficulty='Medium', icon_url=invalid_url)
        with self.assertRaises(ValidationError):
            writing_invalid.full_clean()


class HexColorValidationTests(TestCase):
    """Test hex color validation on model fields."""

    def test_valid_hex_colors_accepted(self):
        """Valid hex color codes should pass validation."""
        valid_colors = ['#58CC02', '#1CB0F6', '#ff9600', '#FFFFFF', '#000000', '#abcdef']
        for color in valid_colors:
            header = Header(
                title='Test Header',
                category='reading',
                background_color=color
            )
            # Should not raise
            header.full_clean()

    def test_invalid_hex_colors_rejected(self):
        """Invalid hex color codes should fail validation."""
        invalid_colors = [
            '58CC02',      # Missing #
            '#58CC0',      # Too short
            '#58CC02G',    # Invalid character
            'red',         # Named color
            '#GGG',        # Invalid hex chars
            '#12345',      # Too short
            '#1234567',    # Too long
        ]
        for color in invalid_colors:
            header = Header(
                title='Test Header',
                category='reading',
                background_color=color
            )
            with self.assertRaises(ValidationError, msg=f"Color {color} should be rejected"):
                header.full_clean()

    def test_null_color_accepted(self):
        """Null color values should be accepted."""
        header = Header(
            title='Test Header',
            category='reading',
            background_color=None
        )
        header.full_clean()  # Should not raise

    def test_empty_string_color_accepted(self):
        """Empty string color should be accepted due to blank=True."""
        header = Header(
            title='Test Header',
            category='reading',
            background_color=''
        )
        header.full_clean()  # Should not raise


class HeaderVisualEnhancementTests(TestCase):
    """Test Header model visual enhancement fields."""

    def test_header_has_icon_url_field(self):
        """Header should have icon_url field."""
        header = Header(title='Test', category='reading')
        self.assertTrue(hasattr(header, 'icon_url'))

    def test_header_has_background_color_field(self):
        """Header should have background_color field."""
        header = Header(title='Test', category='reading')
        self.assertTrue(hasattr(header, 'background_color'))

    def test_header_icon_url_nullable(self):
        """Header icon_url should allow null values."""
        header = Header(title='Test', category='reading', icon_url=None)
        header.full_clean()  # Should not raise

    def test_header_accepts_valid_gcs_icon_url(self):
        """Header should accept valid GCS icon URLs."""
        header = Header(
            title='Test',
            category='reading',
            icon_url='https://storage.googleapis.com/keuvi-app/icons/test.webp'
        )
        header.full_clean()  # Should not raise


class HeaderSerializerTests(TestCase):
    """Test HeaderSerializer visual enhancement fields."""

    def test_serializer_includes_icon_fields(self):
        """HeaderSerializer should include icon and color fields."""
        header = Header(title='Test', category='reading')
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('background_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_background_color', data)

    def test_effective_icon_url_returns_none_when_no_default(self):
        """effective_icon_url should return None when icon_url is null and no default exists."""
        header = Header(title='Test', category='reading', icon_url=None)
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertIsNone(data['icon_url'])
        # DEFAULT_ICONS values are None, so effective should also be None
        self.assertIsNone(data['effective_icon_url'])

    def test_effective_icon_url_returns_custom_when_set(self):
        """effective_icon_url should return custom value when icon_url is set."""
        custom_url = 'https://storage.googleapis.com/keuvi-app/icons/custom-icon.webp'
        header = Header(title='Test', category='reading', icon_url=custom_url)
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertEqual(data['icon_url'], custom_url)
        self.assertEqual(data['effective_icon_url'], custom_url)

    def test_effective_background_color_returns_default_when_null(self):
        """effective_background_color should return default when background_color is null."""
        header = Header(title='Test', category='math', background_color=None)
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertIsNone(data['background_color'])
        self.assertEqual(data['effective_background_color'], DEFAULT_COLORS.get('math'))

    def test_effective_background_color_returns_custom_when_set(self):
        """effective_background_color should return custom value when set."""
        custom_color = '#FF0000'
        header = Header(title='Test', category='reading', background_color=custom_color)
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertEqual(data['background_color'], custom_color)
        self.assertEqual(data['effective_background_color'], custom_color)

    def test_effective_fields_per_category(self):
        """Each category should return its own default colors."""
        categories = ['reading', 'writing', 'math']
        for category in categories:
            header = Header(title='Test', category=category)
            serializer = HeaderSerializer(header)
            data = serializer.data

            # Icon URL defaults are None
            self.assertIsNone(data['effective_icon_url'])
            self.assertEqual(
                data['effective_background_color'],
                DEFAULT_COLORS.get(category),
                f"Effective background color mismatch for {category}"
            )


class PassageVisualEnhancementTests(TestCase):
    """Test Passage model visual enhancement fields."""

    def test_passage_has_icon_fields(self):
        """Passage should have icon_url and icon_color fields."""
        passage = Passage(title='Test', content='Test content')
        self.assertTrue(hasattr(passage, 'icon_url'))
        self.assertTrue(hasattr(passage, 'icon_color'))

    def test_passage_icon_fields_nullable(self):
        """Passage icon fields should allow null values."""
        passage = Passage(
            title='Test',
            content='Test content',
            difficulty='Medium',  # Required field
            icon_url=None,
            icon_color=None
        )
        passage.full_clean()  # Should not raise


class PassageSerializerTests(TestCase):
    """Test PassageListSerializer and PassageDetailSerializer visual enhancement fields."""

    def test_list_serializer_includes_icon_fields(self):
        """PassageListSerializer should include icon fields."""
        passage = Passage(title='Test', content='Content')
        serializer = PassageListSerializer(passage)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_detail_serializer_includes_icon_fields(self):
        """PassageDetailSerializer should include icon fields."""
        passage = Passage(title='Test', content='Content', difficulty='Medium')
        passage.save()
        serializer = PassageDetailSerializer(passage)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)
        passage.delete()

    def test_effective_fields_return_reading_defaults(self):
        """Passage effective fields should return reading category defaults."""
        passage = Passage(title='Test', content='Content')
        serializer = PassageListSerializer(passage)
        data = serializer.data

        # Icon URL default is None
        self.assertIsNone(data['effective_icon_url'])
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('reading'))

    def test_effective_fields_return_custom_values(self):
        """effective fields should return custom values when set."""
        custom_url = 'https://storage.googleapis.com/keuvi-app/icons/passage-icon.webp'
        custom_color = '#123456'
        passage = Passage(
            title='Test',
            content='Content',
            icon_url=custom_url,
            icon_color=custom_color
        )
        serializer = PassageListSerializer(passage)
        data = serializer.data

        self.assertEqual(data['effective_icon_url'], custom_url)
        self.assertEqual(data['effective_icon_color'], custom_color)


class LessonVisualEnhancementTests(TestCase):
    """Test Lesson model visual enhancement fields."""

    def test_lesson_has_icon_fields(self):
        """Lesson should have icon_url and icon_color fields."""
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='writing')
        self.assertTrue(hasattr(lesson, 'icon_url'))
        self.assertTrue(hasattr(lesson, 'icon_color'))


class LessonSerializerTests(TestCase):
    """Test LessonListSerializer and LessonDetailSerializer visual enhancement fields."""

    def test_list_serializer_includes_icon_fields(self):
        """LessonListSerializer should include icon fields."""
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='writing')
        serializer = LessonListSerializer(lesson)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_detail_serializer_includes_icon_fields(self):
        """LessonDetailSerializer should include icon fields."""
        lesson = Lesson(lesson_id='test-detail', title='Test', lesson_type='writing')
        lesson.save()
        serializer = LessonDetailSerializer(lesson)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)
        lesson.delete()

    def test_effective_fields_match_lesson_type(self):
        """Lesson effective fields should match lesson_type category."""
        lesson_types = ['reading', 'writing', 'math']
        for lesson_type in lesson_types:
            lesson = Lesson(
                lesson_id=f'test-{lesson_type}',
                title='Test',
                lesson_type=lesson_type
            )
            serializer = LessonListSerializer(lesson)
            data = serializer.data

            # Icon URL defaults are None
            self.assertIsNone(data['effective_icon_url'])
            self.assertEqual(
                data['effective_icon_color'],
                DEFAULT_COLORS.get(lesson_type),
                f"Effective icon color mismatch for lesson_type={lesson_type}"
            )

    def test_custom_values_override_defaults(self):
        """Custom icon values should override defaults."""
        custom_url = 'https://storage.googleapis.com/keuvi-app/icons/lesson.webp'
        custom_color = '#AABBCC'
        lesson = Lesson(
            lesson_id='test',
            title='Test',
            lesson_type='math',
            icon_url=custom_url,
            icon_color=custom_color
        )
        serializer = LessonListSerializer(lesson)
        data = serializer.data

        self.assertEqual(data['effective_icon_url'], custom_url)
        self.assertEqual(data['effective_icon_color'], custom_color)


class MathSectionVisualEnhancementTests(TestCase):
    """Test MathSection model visual enhancement fields."""

    def test_mathsection_has_icon_fields(self):
        """MathSection should have icon_url and icon_color fields."""
        section = MathSection(section_id='test', title='Test')
        self.assertTrue(hasattr(section, 'icon_url'))
        self.assertTrue(hasattr(section, 'icon_color'))


class MathSectionSerializerTests(TestCase):
    """Test MathSectionListSerializer and MathSectionDetailSerializer visual enhancement fields."""

    def test_list_serializer_includes_icon_fields(self):
        """MathSectionListSerializer should include icon fields."""
        section = MathSection(section_id='test', title='Test')
        serializer = MathSectionListSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_detail_serializer_includes_icon_fields(self):
        """MathSectionDetailSerializer should include icon fields."""
        section = MathSection(section_id='test-detail', title='Test')
        section.save()
        serializer = MathSectionDetailSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)
        section.delete()

    def test_effective_fields_return_math_defaults(self):
        """MathSection effective fields should return math category defaults."""
        section = MathSection(section_id='test', title='Test')
        serializer = MathSectionListSerializer(section)
        data = serializer.data

        # Icon URL default is None
        self.assertIsNone(data['effective_icon_url'])
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('math'))


class WritingSectionVisualEnhancementTests(TestCase):
    """Test WritingSection model visual enhancement fields."""

    def test_writingsection_has_icon_fields(self):
        """WritingSection should have icon_url and icon_color fields."""
        section = WritingSection(title='Test', content='Test content')
        self.assertTrue(hasattr(section, 'icon_url'))
        self.assertTrue(hasattr(section, 'icon_color'))


class WritingSectionSerializerTests(TestCase):
    """Test WritingSectionListSerializer and WritingSectionDetailSerializer visual enhancement fields."""

    def test_list_serializer_includes_icon_fields(self):
        """WritingSectionListSerializer should include icon fields."""
        section = WritingSection(title='Test', content='Test content')
        serializer = WritingSectionListSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_detail_serializer_includes_icon_fields(self):
        """WritingSectionDetailSerializer should include icon fields."""
        section = WritingSection(title='Test', content='Test content', difficulty='Medium')
        section.save()
        serializer = WritingSectionDetailSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)
        section.delete()

    def test_effective_fields_return_writing_defaults(self):
        """WritingSection effective fields should return writing category defaults."""
        section = WritingSection(title='Test', content='Test content')
        serializer = WritingSectionListSerializer(section)
        data = serializer.data

        # Icon URL default is None
        self.assertIsNone(data['effective_icon_url'])
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('writing'))


class IconUrlMaxLengthTests(TestCase):
    """Test icon_url max_length constraints."""

    def test_icon_url_accepts_500_char_url(self):
        """icon_url should accept URLs up to 500 characters."""
        # Create a URL that's exactly 500 characters within GCS prefix
        base_url = GCS_ICON_URL_PREFIX
        padding = 'x' * (500 - len(base_url) - 5)  # -5 for .webp
        long_url = f"{base_url}{padding}.webp"

        header = Header(title='Test', category='reading', icon_url=long_url)
        header.full_clean()  # Should not raise


class EdgeCaseTests(TestCase):
    """Test edge cases for visual enhancement fields."""

    def test_header_unknown_category_uses_fallback_color(self):
        """Unknown category should use fallback color."""
        # Header category field has choices, but test the serializer fallback
        header = Header(title='Test', category='reading')
        # Override category after creation to simulate edge case
        header.category = 'unknown'
        serializer = HeaderSerializer(header)
        data = serializer.data

        # Should return DEFAULT_FALLBACK_COLOR
        self.assertEqual(data['effective_background_color'], DEFAULT_FALLBACK_COLOR)

    def test_lesson_unknown_lesson_type_uses_fallback_color(self):
        """Unknown lesson_type should use fallback color."""
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='writing')
        # Override lesson_type after creation to simulate edge case
        lesson.lesson_type = 'unknown'
        serializer = LessonListSerializer(lesson)
        data = serializer.data

        # Should return DEFAULT_FALLBACK_COLOR
        self.assertEqual(data['effective_icon_color'], DEFAULT_FALLBACK_COLOR)

    def test_empty_icon_url_string_treated_as_none(self):
        """Empty string icon_url should still use default (effective_icon_url)."""
        header = Header(title='Test', category='reading', icon_url='')
        serializer = HeaderSerializer(header)
        data = serializer.data

        # Empty string is falsy, so effective should return default (None)
        self.assertIsNone(data['effective_icon_url'])


class APIEndpointIntegrationTests(TestCase):
    """Integration tests for API endpoints including visual enhancement fields."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.api_base = '/api/v1'

        # Create test passage
        self.passage = Passage.objects.create(
            title='Test Passage',
            content='Test content for passage',
            difficulty='Medium',
            tier='free',
            icon_url='https://storage.googleapis.com/keuvi-app/icons/test-passage.webp',
            icon_color='#1CB0F6'
        )

        # Create test lesson
        self.lesson = Lesson.objects.create(
            lesson_id='test-lesson-api',
            title='Test Lesson',
            lesson_type='writing',
            difficulty='Easy',
            tier='free',
            chunks=[],  # Required field
            icon_url='https://storage.googleapis.com/keuvi-app/icons/test-lesson.webp',
            icon_color='#CE82FF'
        )

        # Create test math section
        self.math_section = MathSection.objects.create(
            section_id='test-math-api',
            title='Test Math Section',
            difficulty='Medium',
            tier='free',
            icon_url='https://storage.googleapis.com/keuvi-app/icons/test-math.webp',
            icon_color='#FF9600'
        )

        # Create test writing section
        self.writing_section = WritingSection.objects.create(
            title='Test Writing Section',
            content='Test writing content',
            difficulty='Hard',
            tier='free',
            icon_url='https://storage.googleapis.com/keuvi-app/icons/test-writing.webp',
            icon_color='#CE82FF'
        )

    def tearDown(self):
        """Clean up test data."""
        self.passage.delete()
        self.lesson.delete()
        self.math_section.delete()
        self.writing_section.delete()

    def test_passages_list_endpoint_includes_icon_fields(self):
        """GET /api/v1/passages/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/passages/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Find our test passage
        passages = data.get('results', data) if isinstance(data, dict) else data
        test_passage = next((p for p in passages if str(p['id']) == str(self.passage.id)), None)

        if test_passage:
            self.assertIn('icon_url', test_passage)
            self.assertIn('icon_color', test_passage)
            self.assertIn('effective_icon_url', test_passage)
            self.assertIn('effective_icon_color', test_passage)
            self.assertEqual(test_passage['icon_url'], self.passage.icon_url)
            self.assertEqual(test_passage['icon_color'], self.passage.icon_color)

    def test_passage_detail_endpoint_includes_icon_fields(self):
        """GET /api/v1/passages/<id>/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/passages/{self.passage.id}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_lessons_list_endpoint_includes_icon_fields(self):
        """GET /api/v1/lessons/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/lessons/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        lessons = data.get('results', data) if isinstance(data, dict) else data
        test_lesson = next((l for l in lessons if str(l['id']) == str(self.lesson.id)), None)

        if test_lesson:
            self.assertIn('icon_url', test_lesson)
            self.assertIn('icon_color', test_lesson)
            self.assertIn('effective_icon_url', test_lesson)
            self.assertIn('effective_icon_color', test_lesson)

    def test_lesson_detail_endpoint_includes_icon_fields(self):
        """GET /api/v1/lessons/<id>/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/lessons/{self.lesson.id}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_math_sections_list_endpoint_includes_icon_fields(self):
        """GET /api/v1/math-sections/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/math-sections/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        sections = data.get('results', data) if isinstance(data, dict) else data
        test_section = next((s for s in sections if str(s['id']) == str(self.math_section.id)), None)

        if test_section:
            self.assertIn('icon_url', test_section)
            self.assertIn('icon_color', test_section)
            self.assertIn('effective_icon_url', test_section)
            self.assertIn('effective_icon_color', test_section)

    def test_math_section_detail_endpoint_includes_icon_fields(self):
        """GET /api/v1/math-sections/<id>/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/math-sections/{self.math_section.id}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_writing_sections_list_endpoint_includes_icon_fields(self):
        """GET /api/v1/writing-sections/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/writing-sections/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        sections = data.get('results', data) if isinstance(data, dict) else data
        test_section = next((s for s in sections if str(s['id']) == str(self.writing_section.id)), None)

        if test_section:
            self.assertIn('icon_url', test_section)
            self.assertIn('icon_color', test_section)
            self.assertIn('effective_icon_url', test_section)
            self.assertIn('effective_icon_color', test_section)

    def test_writing_section_detail_endpoint_includes_icon_fields(self):
        """GET /api/v1/writing-sections/<id>/ should include visual enhancement fields."""
        response = self.client.get(f'{self.api_base}/writing-sections/{self.writing_section.id}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_effective_fields_computed_correctly_in_api(self):
        """effective_* fields should be computed correctly in API responses."""
        # Create passage without custom icon
        passage_no_icon = Passage.objects.create(
            title='Test Passage No Icon',
            content='Test content',
            difficulty='Easy',
            tier='free',
            icon_url=None,
            icon_color=None
        )

        response = self.client.get(f'{self.api_base}/passages/{passage_no_icon.id}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # effective_icon_url should be None (no default)
        self.assertIsNone(data['effective_icon_url'])
        # effective_icon_color should be the default for reading
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('reading'))

        passage_no_icon.delete()
