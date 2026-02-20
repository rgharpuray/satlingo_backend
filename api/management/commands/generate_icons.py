"""
Generate Duolingo-style icons for content items using DALL-E 3.

Location: api/management/commands/generate_icons.py
Summary: Management command that generates visual icons for Lessons, Passages,
         MathSections, WritingSections, and Headers using OpenAI's DALL-E 3 API.
         Icons are converted to WebP format and uploaded to GCS.
Usage:
  python manage.py generate_icons --dry-run              # Preview what would be generated
  python manage.py generate_icons --limit 5              # Generate 5 icons
  python manage.py generate_icons --model lesson         # Only generate for lessons
  python manage.py generate_icons --category math        # Only math category
  python manage.py generate_icons                        # Generate all missing icons

Requires: OPENAI_API_KEY environment variable
Cost: ~$0.04 per icon (DALL-E 3 256x256)
"""
import os
import io
import time
import tempfile
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from api.models import Lesson, Passage, MathSection, WritingSection, Header
from api.storage_backend import upload_to_gcs
from api.constants import DEFAULT_COLORS


# Try to import optional dependencies
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# DALL-E prompt template for generating Duolingo-style icons
ICON_PROMPT_TEMPLATE = """
Minimalist educational icon for "{title}", Duolingo-style, rounded shapes,
vibrant {color} accent on white background, simple 2D vector art,
no text, no shadows, no gradients, flat design, 256x256, centered composition
""".strip().replace('\n', ' ')


# Map model types to their category determination
MODEL_CATEGORY_MAP = {
    'lesson': lambda item: item.lesson_type,  # reading, writing, or math
    'passage': lambda item: 'reading',
    'math_section': lambda item: 'math',
    'writing_section': lambda item: 'writing',
    'header': lambda item: item.category,
}

# Model class references
MODEL_CLASSES = {
    'lesson': Lesson,
    'passage': Passage,
    'math_section': MathSection,
    'writing_section': WritingSection,
    'header': Header,
}


class Command(BaseCommand):
    help = 'Generate Duolingo-style icons for content items using DALL-E 3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be generated without making API calls or changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of icons to generate (useful for testing)',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['lesson', 'passage', 'math_section', 'writing_section', 'header', 'all'],
            default='all',
            help='Which content model to generate icons for',
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['reading', 'writing', 'math'],
            default=None,
            help='Only process items from a specific category',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate icons even if they already exist',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API calls in seconds (default: 1.0 for rate limiting)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        model_filter = options['model']
        category_filter = options['category']
        force = options['force']
        delay = options['delay']

        # Check dependencies (always needed)
        if not HAS_PIL:
            self.stderr.write(self.style.ERROR('Pillow is required. Install with: pip install Pillow'))
            return

        if not HAS_OPENAI:
            self.stderr.write(self.style.ERROR('OpenAI is required. Install with: pip install openai'))
            return

        # Collect items to process first (can be done without API key)
        items_to_process = []
        models_to_process = [model_filter] if model_filter != 'all' else MODEL_CLASSES.keys()

        for model_name in models_to_process:
            model_class = MODEL_CLASSES[model_name]
            get_category = MODEL_CATEGORY_MAP[model_name]

            # Build queryset
            queryset = model_class.objects.all()

            # Filter by existing icon_url (unless force)
            if not force:
                queryset = queryset.filter(icon_url__isnull=True) | queryset.filter(icon_url='')

            # For headers, also check background_color since that's what we set
            if model_name == 'header' and not force:
                queryset = model_class.objects.filter(icon_url__isnull=True) | model_class.objects.filter(icon_url='')

            for item in queryset:
                category = get_category(item)

                # Apply category filter if specified
                if category_filter and category != category_filter:
                    continue

                items_to_process.append({
                    'model': model_name,
                    'model_class': model_class,
                    'item': item,
                    'category': category,
                    'title': item.title,
                    'id': str(item.id),
                })

        # Apply limit
        if limit:
            items_to_process = items_to_process[:limit]

        if not items_to_process:
            self.stdout.write(self.style.SUCCESS('No items need icon generation.'))
            return

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Icon Generation Summary ==='))
        self.stdout.write(f'Total items to process: {len(items_to_process)}')

        # Count by model
        model_counts = {}
        for item in items_to_process:
            model_counts[item['model']] = model_counts.get(item['model'], 0) + 1
        for model_name, count in model_counts.items():
            self.stdout.write(f'  {model_name}: {count}')

        # Estimate cost
        estimated_cost = len(items_to_process) * 0.04
        self.stdout.write(f'Estimated cost: ${estimated_cost:.2f}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Would generate icons for:'))
            for i, item_info in enumerate(items_to_process[:20]):
                color = DEFAULT_COLORS.get(item_info['category'], '#58CC02')
                self.stdout.write(
                    f"  {i+1}. [{item_info['model']}] {item_info['title'][:50]} "
                    f"(category: {item_info['category']}, color: {color})"
                )
            if len(items_to_process) > 20:
                self.stdout.write(f'  ... and {len(items_to_process) - 20} more')
            return

        # Check API key (only needed for actual generation, not dry-run)
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            self.stderr.write(self.style.ERROR('OPENAI_API_KEY not found in settings or environment'))
            return

        # Check GCS configuration (required for uploads)
        if not getattr(settings, 'GS_BUCKET_NAME', None):
            self.stderr.write(self.style.ERROR('GS_BUCKET_NAME not configured'))
            return

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=api_key)

        # Process items
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Generating Icons ==='))

        # Use tqdm if available
        iterator = items_to_process
        if HAS_TQDM:
            iterator = tqdm(items_to_process, desc='Generating icons')

        success_count = 0
        error_count = 0

        for item_info in iterator:
            try:
                result = self.generate_icon_for_item(item_info, delay)
                if result:
                    success_count += 1
                    if not HAS_TQDM:
                        self.stdout.write(
                            self.style.SUCCESS(f"  [OK] {item_info['model']}: {item_info['title'][:40]}")
                        )
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                if not HAS_TQDM:
                    self.stderr.write(
                        self.style.ERROR(f"  [ERROR] {item_info['model']}: {item_info['title'][:40]} - {e}")
                    )
                else:
                    tqdm.write(f"[ERROR] {item_info['title'][:40]}: {e}")

        # Final summary
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Results ==='))
        self.stdout.write(self.style.SUCCESS(f'Successfully generated: {success_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))

    def generate_icon_for_item(self, item_info, delay):
        """
        Generate an icon for a single item using DALL-E 3.

        1. Generate image with DALL-E
        2. Download the image
        3. Convert to WebP
        4. Upload to GCS
        5. Update the database

        Returns True on success, False on failure.
        """
        model_name = item_info['model']
        item = item_info['item']
        category = item_info['category']
        title = item_info['title']
        item_id = item_info['id']

        # Get category color
        color_hex = DEFAULT_COLORS.get(category, '#58CC02')
        color_name = self._hex_to_color_name(color_hex)

        # Build prompt
        prompt = ICON_PROMPT_TEMPLATE.format(title=title, color=color_name)

        # Generate image with DALL-E 3
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",  # DALL-E 3 minimum is 1024x1024
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
        except openai.RateLimitError as e:
            self.stderr.write(self.style.WARNING(f"Rate limited, waiting 60s: {e}"))
            time.sleep(60)
            # Retry once
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
        except openai.APIError as e:
            self.stderr.write(self.style.ERROR(f"OpenAI API error: {e}"))
            return False

        # Download the image
        try:
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            image_data = img_response.content
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Failed to download image: {e}"))
            return False

        # Convert to WebP and resize to 256x256
        try:
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGBA')  # Ensure RGBA for transparency support
            img = img.resize((256, 256), Image.Resampling.LANCZOS)

            # Save to temp file as WebP
            with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp_file:
                img.save(tmp_file, format='WEBP', quality=90)
                tmp_path = tmp_file.name
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to process image: {e}"))
            return False

        # Upload to GCS
        gcs_key = f"icons/{model_name}/{item_id}/icon.webp"
        try:
            icon_url = upload_to_gcs(tmp_path, gcs_key, content_type='image/webp')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to upload to GCS: {e}"))
            os.unlink(tmp_path)
            return False
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Update the database
        try:
            with transaction.atomic():
                item.icon_url = icon_url
                # Header uses background_color, other models use icon_color
                if model_name == 'header':
                    item.background_color = color_hex
                    item.save(update_fields=['icon_url', 'background_color', 'updated_at'])
                else:
                    item.icon_color = color_hex
                    item.save(update_fields=['icon_url', 'icon_color', 'updated_at'])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to update database: {e}"))
            return False

        # Rate limiting delay
        time.sleep(delay)

        return True

    def _hex_to_color_name(self, hex_color):
        """
        Convert hex color to a descriptive color name for the prompt.
        """
        color_map = {
            '#58CC02': 'bright green',
            '#1CB0F6': 'sky blue',
            '#FF9600': 'vibrant orange',
            '#FF4B4B': 'coral red',
            '#CE82FF': 'soft purple',
            '#FFD900': 'golden yellow',
        }
        return color_map.get(hex_color.upper(), hex_color)
