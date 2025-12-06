"""
Management command to backfill content_hash for existing passages.

Usage:
    python manage.py backfill_content_hash
"""
from django.core.management.base import BaseCommand
from api.models import Passage
from api.ingestion_utils import compute_content_hash


class Command(BaseCommand):
    help = 'Backfill content_hash for existing passages (for duplicate detection)'

    def handle(self, *args, **options):
        passages = Passage.objects.filter(content_hash__isnull=True)
        count = passages.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All passages already have content_hash'))
            return
        
        self.stdout.write(f'Backfilling content_hash for {count} passage(s)...')
        
        updated = 0
        for passage in passages:
            passage.content_hash = compute_content_hash(passage.content)
            passage.save(update_fields=['content_hash'])
            updated += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated} passage(s) with content_hash'))

