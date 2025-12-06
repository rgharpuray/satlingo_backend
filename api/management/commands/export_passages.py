"""
Management command to export processed passages for syncing to production.

Usage:
    python manage.py export_passages                    # Export all passages
    python manage.py export_passages --ingestion <id>   # Export passages from specific ingestion
    python manage.py export_passages --output passages.json
"""
from django.core.management.base import BaseCommand
from api.models import Passage, PassageIngestion
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Export processed passages to JSON for syncing to production'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingestion',
            type=str,
            help='Export passages created from a specific ingestion ID',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='passages_export.json',
            help='Output file path (default: passages_export.json)',
        )
        parser.add_argument(
            '--include-questions',
            action='store_true',
            default=True,
            help='Include questions and options (default: True)',
        )

    def handle(self, *args, **options):
        ingestion_id = options.get('ingestion')
        output_file = options.get('output')
        include_questions = options.get('include_questions', True)

        # Get passages to export
        if ingestion_id:
            try:
                ingestion = PassageIngestion.objects.get(id=ingestion_id)
                if not ingestion.created_passage:
                    self.stdout.write(self.style.ERROR(f'Ingestion {ingestion_id} has no created passage'))
                    return
                passages = [ingestion.created_passage]
            except PassageIngestion.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Ingestion {ingestion_id} not found'))
                return
        else:
            passages = Passage.objects.all().order_by('created_at')

        self.stdout.write(f'Exporting {passages.count()} passage(s) to {output_file}...')

        # Serialize passages
        export_data = {
            'export_date': datetime.now().isoformat(),
            'passages': []
        }

        for passage in passages:
            passage_data = {
                'id': str(passage.id),
                'title': passage.title,
                'content': passage.content,
                'difficulty': passage.difficulty,
                'tier': passage.tier,
                'created_at': passage.created_at.isoformat() if passage.created_at else None,
            }

            if include_questions:
                passage_data['questions'] = []
                for question in passage.questions.all().order_by('order'):
                    question_data = {
                        'order': question.order,
                        'text': question.text,
                        'correct_answer_index': question.correct_answer_index,
                        'explanation': question.explanation or '',
                        'options': []
                    }
                    for option in question.options.all().order_by('order'):
                        question_data['options'].append({
                            'order': option.order,
                            'text': option.text,
                        })
                    passage_data['questions'].append(question_data)

            export_data['passages'].append(passage_data)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f'✓ Exported {passages.count()} passage(s) to {output_file}'))

