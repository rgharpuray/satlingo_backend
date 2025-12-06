"""
Management command to process passage ingestions locally.

Usage:
    python manage.py process_ingestions                    # Process all pending
    python manage.py process_ingestions --id <uuid>        # Process specific ingestion
    python manage.py process_ingestions --failed           # Re-process failed
    python manage.py process_ingestions --all              # Process all (pending + failed)
"""
from django.core.management.base import BaseCommand, CommandError
from api.models import PassageIngestion
from api.ingestion_utils import process_ingestion
import sys


class Command(BaseCommand):
    help = 'Process passage ingestions locally (for development/testing before production)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=str,
            help='Process a specific ingestion by ID (UUID)',
        )
        parser.add_argument(
            '--failed',
            action='store_true',
            help='Re-process all failed ingestions',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all pending and failed ingestions',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'failed', 'processing', 'completed'],
            help='Process ingestions with specific status',
        )

    def handle(self, *args, **options):
        ingestion_id = options.get('id')
        process_failed = options.get('failed', False)
        process_all = options.get('all', False)
        status_filter = options.get('status')

        # Determine which ingestions to process
        if ingestion_id:
            try:
                ingestions = [PassageIngestion.objects.get(id=ingestion_id)]
                self.stdout.write(self.style.SUCCESS(f'Processing ingestion: {ingestion_id}'))
            except PassageIngestion.DoesNotExist:
                raise CommandError(f'Ingestion with ID {ingestion_id} not found')
        elif process_all:
            ingestions = PassageIngestion.objects.filter(
                status__in=['pending', 'failed']
            ).order_by('created_at')
            self.stdout.write(self.style.SUCCESS(f'Processing {ingestions.count()} ingestions (pending + failed)'))
        elif process_failed:
            ingestions = PassageIngestion.objects.filter(status='failed').order_by('created_at')
            self.stdout.write(self.style.SUCCESS(f'Re-processing {ingestions.count()} failed ingestions'))
        elif status_filter:
            ingestions = PassageIngestion.objects.filter(status=status_filter).order_by('created_at')
            self.stdout.write(self.style.SUCCESS(f'Processing {ingestions.count()} ingestions with status: {status_filter}'))
        else:
            # Default: process pending
            ingestions = PassageIngestion.objects.filter(status='pending').order_by('created_at')
            self.stdout.write(self.style.SUCCESS(f'Processing {ingestions.count()} pending ingestions'))

        if not ingestions:
            self.stdout.write(self.style.WARNING('No ingestions to process'))
            return

        # Process each ingestion
        success_count = 0
        fail_count = 0

        for i, ingestion in enumerate(ingestions, 1):
            self.stdout.write(f'\n[{i}/{ingestions.count()}] Processing: {ingestion.file_name} (ID: {ingestion.id})')
            self.stdout.write(f'  Status: {ingestion.status}')
            self.stdout.write(f'  Type: {ingestion.file_type}')
            
            if not ingestion.file_path:
                self.stdout.write(self.style.ERROR('  ✗ No file path - skipping'))
                fail_count += 1
                continue

            try:
                # Reset status if failed
                if ingestion.status == 'failed':
                    ingestion.status = 'pending'
                    ingestion.error_message = None
                    ingestion.save()

                # Process in foreground (not background thread)
                self.stdout.write('  → Starting processing...')
                process_ingestion(ingestion)
                
                # Refresh from DB to get updated status
                ingestion.refresh_from_db()
                
                if ingestion.status == 'completed':
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Completed! Created passage: {ingestion.created_passage.title if ingestion.created_passage else "N/A"}'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed: {ingestion.error_message or "Unknown error"}'))
                    fail_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                fail_count += 1
                # Continue processing other ingestions
                continue

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully processed: {success_count}'))
        if fail_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {fail_count}'))
        self.stdout.write('='*60)

