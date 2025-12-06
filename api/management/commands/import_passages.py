"""
Management command to import parsed ingestion data and create passages.

This reads the exported JSON file and creates passages from the parsed_data
without needing to re-process files or use AI.

Usage:
    python manage.py import_passages passages.json
    python manage.py import_passages ingestions_export.json --dry-run  # Preview without creating
"""
from django.core.management.base import BaseCommand, CommandError
from api.models import Passage, Question, QuestionOption
from api.ingestion_utils import create_passage_from_parsed_data, find_duplicate_passage
import json
import os


class Command(BaseCommand):
    help = 'Import parsed ingestion data and create passages (no processing needed)'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            type=str,
            help='JSON file to import (from export_ingestions command)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without actually creating passages',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options.get('dry_run', False)

        if not os.path.exists(file_path):
            raise CommandError(f'File not found: {file_path}')

        # Read JSON file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {str(e)}')

        # Validate structure
        if 'ingestions' not in data:
            raise CommandError('Invalid format: missing "ingestions" array')

        ingestions = data['ingestions']
        if not ingestions:
            self.stdout.write(self.style.WARNING('No ingestions found in file'))
            return

        self.stdout.write(f'Found {len(ingestions)} ingestion(s) to import')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No passages will be created\n'))

        success_count = 0
        skip_count = 0
        fail_count = 0

        for idx, entry in enumerate(ingestions, 1):
            ingestion_id = entry.get('ingestion_id', 'unknown')
            file_name = entry.get('file_name', 'unknown')
            parsed_data = entry.get('parsed_data')

            if not parsed_data:
                self.stdout.write(self.style.WARNING(f'[{idx}/{len(ingestions)}] Skipping {file_name} - no parsed_data'))
                skip_count += 1
                continue

            self.stdout.write(f'\n[{idx}/{len(ingestions)}] {file_name}')
            self.stdout.write(f'  Title: {parsed_data.get("title", "N/A")}')
            self.stdout.write(f'  Questions: {len(parsed_data.get("questions", []))}')

            if dry_run:
                self.stdout.write('  → Would create passage (DRY RUN)')
                success_count += 1
                continue

            try:
                # Validate parsed_data structure
                required_fields = ['title', 'content', 'difficulty', 'questions']
                if not all(field in parsed_data for field in required_fields):
                    raise Exception('Missing required fields in parsed_data')

                # Create passage using the same function as processing (checks for duplicates)
                passage, is_new = create_passage_from_parsed_data(parsed_data, check_duplicates=True)
                
                if is_new:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created passage: {passage.title} (ID: {passage.id})'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Duplicate - linked to existing: {passage.title} (ID: {passage.id})'))
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {str(e)}'))
                fail_count += 1
                continue

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN - Would create: {success_count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Successfully created: {success_count}'))
        if skip_count > 0:
            self.stdout.write(self.style.WARNING(f'⊘ Skipped: {skip_count}'))
        if fail_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {fail_count}'))
        self.stdout.write('='*60)

