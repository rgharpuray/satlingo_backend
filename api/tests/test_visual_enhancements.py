"""
Unit tests for Visual Enhancement fields on content models.

Location: api/tests/test_visual_enhancements.py
Coverage: icon_url, icon_color, background_color fields and effective_* serializer methods.
"""

import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError

from api.models import Header, Passage, Lesson, MathSection, WritingSection
from api.serializers import (
    HeaderSerializer,
    PassageListSerializer,
    LessonListSerializer,
    MathSectionListSerializer,
    WritingSectionListSerializer,
)
from api.constants import DEFAULT_COLORS, DEFAULT_ICONS


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
        """Default icons should be defined for all content categories."""
        self.assertIn('reading', DEFAULT_ICONS)
        self.assertIn('writing', DEFAULT_ICONS)
        self.assertIn('math', DEFAULT_ICONS)

    def test_default_icons_are_urls(self):
        """All default icons should be valid URLs."""
        for category, url in DEFAULT_ICONS.items():
            self.assertTrue(
                url.startswith('https://'),
                f"Icon URL for {category} should start with https://: {url}"
            )


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

    def test_header_accepts_valid_icon_url(self):
        """Header should accept valid icon URLs."""
        header = Header(
            title='Test',
            category='reading',
            icon_url='https://storage.googleapis.com/bucket/icons/test.webp'
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

    def test_effective_icon_url_returns_default_when_null(self):
        """effective_icon_url should return default when icon_url is null."""
        header = Header(title='Test', category='reading', icon_url=None)
        serializer = HeaderSerializer(header)
        data = serializer.data

        self.assertIsNone(data['icon_url'])
        self.assertEqual(data['effective_icon_url'], DEFAULT_ICONS.get('reading'))

    def test_effective_icon_url_returns_custom_when_set(self):
        """effective_icon_url should return custom value when icon_url is set."""
        custom_url = 'https://example.com/custom-icon.webp'
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
        """Each category should return its own default colors/icons."""
        categories = ['reading', 'writing', 'math']
        for category in categories:
            header = Header(title='Test', category=category)
            serializer = HeaderSerializer(header)
            data = serializer.data

            self.assertEqual(
                data['effective_icon_url'],
                DEFAULT_ICONS.get(category),
                f"Effective icon URL mismatch for {category}"
            )
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
    """Test PassageListSerializer visual enhancement fields."""

    def test_serializer_includes_icon_fields(self):
        """PassageListSerializer should include icon fields."""
        passage = Passage(title='Test', content='Content')
        serializer = PassageListSerializer(passage)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_effective_fields_return_reading_defaults(self):
        """Passage effective fields should return reading category defaults."""
        passage = Passage(title='Test', content='Content')
        serializer = PassageListSerializer(passage)
        data = serializer.data

        self.assertEqual(data['effective_icon_url'], DEFAULT_ICONS.get('reading'))
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('reading'))

    def test_effective_fields_return_custom_values(self):
        """effective fields should return custom values when set."""
        custom_url = 'https://example.com/passage-icon.webp'
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
    """Test LessonListSerializer visual enhancement fields."""

    def test_serializer_includes_icon_fields(self):
        """LessonListSerializer should include icon fields."""
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='writing')
        serializer = LessonListSerializer(lesson)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

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

            self.assertEqual(
                data['effective_icon_url'],
                DEFAULT_ICONS.get(lesson_type),
                f"Effective icon URL mismatch for lesson_type={lesson_type}"
            )
            self.assertEqual(
                data['effective_icon_color'],
                DEFAULT_COLORS.get(lesson_type),
                f"Effective icon color mismatch for lesson_type={lesson_type}"
            )

    def test_custom_values_override_defaults(self):
        """Custom icon values should override defaults."""
        custom_url = 'https://example.com/lesson.webp'
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
    """Test MathSectionListSerializer visual enhancement fields."""

    def test_serializer_includes_icon_fields(self):
        """MathSectionListSerializer should include icon fields."""
        section = MathSection(section_id='test', title='Test')
        serializer = MathSectionListSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_effective_fields_return_math_defaults(self):
        """MathSection effective fields should return math category defaults."""
        section = MathSection(section_id='test', title='Test')
        serializer = MathSectionListSerializer(section)
        data = serializer.data

        self.assertEqual(data['effective_icon_url'], DEFAULT_ICONS.get('math'))
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('math'))


class WritingSectionVisualEnhancementTests(TestCase):
    """Test WritingSection model visual enhancement fields."""

    def test_writingsection_has_icon_fields(self):
        """WritingSection should have icon_url and icon_color fields."""
        section = WritingSection(title='Test', content='Test content')
        self.assertTrue(hasattr(section, 'icon_url'))
        self.assertTrue(hasattr(section, 'icon_color'))


class WritingSectionSerializerTests(TestCase):
    """Test WritingSectionListSerializer visual enhancement fields."""

    def test_serializer_includes_icon_fields(self):
        """WritingSectionListSerializer should include icon fields."""
        section = WritingSection(title='Test', content='Test content')
        serializer = WritingSectionListSerializer(section)
        data = serializer.data

        self.assertIn('icon_url', data)
        self.assertIn('icon_color', data)
        self.assertIn('effective_icon_url', data)
        self.assertIn('effective_icon_color', data)

    def test_effective_fields_return_writing_defaults(self):
        """WritingSection effective fields should return writing category defaults."""
        section = WritingSection(title='Test', content='Test content')
        serializer = WritingSectionListSerializer(section)
        data = serializer.data

        self.assertEqual(data['effective_icon_url'], DEFAULT_ICONS.get('writing'))
        self.assertEqual(data['effective_icon_color'], DEFAULT_COLORS.get('writing'))


class IconUrlMaxLengthTests(TestCase):
    """Test icon_url max_length constraints."""

    def test_icon_url_accepts_500_char_url(self):
        """icon_url should accept URLs up to 500 characters."""
        # Create a URL that's exactly 500 characters
        base_url = 'https://storage.googleapis.com/bucket/icons/'
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

        # Should return fallback color #1CB0F6
        self.assertEqual(data['effective_background_color'], '#1CB0F6')

    def test_lesson_unknown_lesson_type_uses_fallback_color(self):
        """Unknown lesson_type should use fallback color."""
        lesson = Lesson(lesson_id='test', title='Test', lesson_type='writing')
        # Override lesson_type after creation to simulate edge case
        lesson.lesson_type = 'unknown'
        serializer = LessonListSerializer(lesson)
        data = serializer.data

        # Should return fallback color #58CC02
        self.assertEqual(data['effective_icon_color'], '#58CC02')

    def test_empty_icon_url_string_treated_as_none(self):
        """Empty string icon_url should still use default (effective_icon_url)."""
        header = Header(title='Test', category='reading', icon_url='')
        serializer = HeaderSerializer(header)
        data = serializer.data

        # Empty string is falsy, so effective should return default
        self.assertEqual(data['effective_icon_url'], DEFAULT_ICONS.get('reading'))
