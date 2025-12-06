"""
Management command to export parsed ingestion data in a simple, importable format.

This exports the AI-parsed data (parsed_data) from completed ingestions,
which can then be easily imported to create passages without re-processing.

Usage:
    python manage.py export_ingestions                    # Export all completed ingestions
    python manage.py export_ingestions --output passages.json
    python manage.py export_ingestions --ingestion <id>   # Export specific ingestion
"""
from django.core.management.base import BaseCommand
from api.models import PassageIngestion
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Export parsed ingestion data in a simple format for easy passage creation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingestion',
            type=str,
            help='Export a specific ingestion by ID (UUID)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='ingestions_export.json',
            help='Output file path (default: ingestions_export.json)',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['completed', 'processing', 'failed', 'pending', 'all'],
            default='all',
            help='Export ingestions with specific status. Use "all" to export any with parsed_data (default: all)',
        )

    def handle(self, *args, **options):
        ingestion_id = options.get('ingestion')
        output_file = options.get('output')
        status_filter = options.get('status', 'completed')

        # Get ingestions to export
        if ingestion_id:
            try:
                ingestions = [PassageIngestion.objects.get(id=ingestion_id)]
            except PassageIngestion.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Ingestion {ingestion_id} not found'))
                return
        else:
            if status_filter == 'all':
                # Export ALL ingestions that have parsed_data (regardless of status)
                ingestions = PassageIngestion.objects.exclude(parsed_data__isnull=True).exclude(parsed_data={}).order_by('created_at')
            else:
                ingestions = PassageIngestion.objects.filter(status=status_filter).order_by('created_at')

        # Filter to only those with parsed_data (double-check, though query should handle it)
        ingestions_with_data = [i for i in ingestions if i.parsed_data]

        if not ingestions_with_data:
            self.stdout.write(self.style.WARNING(f'No ingestions with parsed_data found (status: {status_filter})'))
            return

        self.stdout.write(f'Exporting {len(ingestions_with_data)} ingestion(s) to {output_file}...')

        # Export format: simple array of parsed_data objects
        export_data = {
            'export_date': datetime.now().isoformat(),
            'export_format_version': '1.0',
            'description': 'Parsed passage data ready for import - each entry can create one passage',
            'ingestions': []
        }

        for ingestion in ingestions_with_data:
            entry = {
                'ingestion_id': str(ingestion.id),
                'file_name': ingestion.file_name,
                'file_type': ingestion.file_type,
                'created_at': ingestion.created_at.isoformat() if ingestion.created_at else None,
                'parsed_data': ingestion.parsed_data  # This is the ready-to-use data
            }
            export_data['ingestions'].append(entry)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f'✓ Exported {len(ingestions_with_data)} ingestion(s) to {output_file}\n'
            f'  Each entry contains parsed_data ready to create passages.'
        ))

