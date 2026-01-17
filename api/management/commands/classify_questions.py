"""
Management command to use AI to classify questions.
Iterates through LessonQuestions and Questions (passages) and assigns classifications.
"""
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Question, LessonQuestion, QuestionClassification
import openai


class Command(BaseCommand):
    help = 'Use AI to assign classifications to questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be classified without making changes',
        )
        parser.add_argument(
            '--only-unclassified',
            action='store_true',
            help='Only classify questions that have no classifications yet',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['lesson', 'passage', 'all'],
            default='all',
            help='Which type of questions to classify (lesson, passage, or all)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of questions to process',
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['reading', 'writing', 'math'],
            default=None,
            help='Only process questions from a specific category',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only_unclassified = options['only_unclassified']
        question_type = options['type']
        limit = options['limit']
        category_filter = options['category']

        # Load all classifications grouped by category
        classifications = QuestionClassification.objects.all()
        if classifications.count() == 0:
            self.stderr.write(self.style.ERROR('No classifications found. Please create some first.'))
            return

        # Build classification lookup by category
        self.classifications_by_category = {}
        for c in classifications:
            if c.category not in self.classifications_by_category:
                self.classifications_by_category[c.category] = []
            self.classifications_by_category[c.category].append({
                'id': str(c.id),
                'name': c.name,
            })

        self.stdout.write(f"Loaded {classifications.count()} classifications across {len(self.classifications_by_category)} categories")

        # Process LessonQuestions
        if question_type in ['lesson', 'all']:
            self.process_lesson_questions(dry_run, only_unclassified, limit, category_filter)

        # Process Questions (passages)
        if question_type in ['passage', 'all']:
            self.process_passage_questions(dry_run, only_unclassified, limit, category_filter)

    def get_category_for_lesson(self, lesson_question):
        """Determine the category based on the lesson type"""
        lesson = lesson_question.lesson
        # Use lesson_type field if available
        if hasattr(lesson, 'lesson_type') and lesson.lesson_type:
            return lesson.lesson_type
        # Check if it's linked via WritingLesson
        if hasattr(lesson, 'writing_lessons') and lesson.writing_lessons.exists():
            return 'writing'
        # Check if it's linked via MathLesson
        if hasattr(lesson, 'math_lessons') and lesson.math_lessons.exists():
            return 'math'
        # Default to writing for regular lessons (grammar/conventions)
        return 'writing'

    def get_category_for_passage(self, question):
        """Determine the category for passage questions - they're reading questions"""
        return 'reading'
    
    def extract_text_from_blocks(self, blocks):
        """Extract plain text from JSON block structures"""
        if not blocks:
            return ""
        
        if isinstance(blocks, str):
            return blocks
        
        if not isinstance(blocks, list):
            return str(blocks)
        
        text_parts = []
        for block in blocks:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                # Handle different block types
                block_type = block.get('type', '')
                
                if block_type == 'paragraph' or 'text' in block:
                    text_parts.append(block.get('text', ''))
                elif block_type == 'side_by_side':
                    # Extract from left/right
                    left = block.get('left', {})
                    right = block.get('right', {})
                    if isinstance(left, dict):
                        text_parts.append(left.get('text', ''))
                    if isinstance(right, dict):
                        text_parts.append(right.get('text', ''))
                elif 'content' in block:
                    content = block.get('content', '')
                    if isinstance(content, str):
                        text_parts.append(content)
                    elif isinstance(content, list):
                        text_parts.append(self.extract_text_from_blocks(content))
                else:
                    # Try to get any text-like field
                    for key in ['text', 'value', 'label', 'title']:
                        if key in block:
                            text_parts.append(str(block[key]))
                            break
        
        return ' '.join(filter(None, text_parts))

    def classify_with_ai(self, question_text, options_text, category, explanation_text=None):
        """Use OpenAI to classify a question"""
        available_classifications = self.classifications_by_category.get(category, [])
        if not available_classifications:
            return []

        classification_names = [c['name'] for c in available_classifications]
        
        prompt = f"""You are classifying SAT practice questions. Given the question below, identify which classification(s) it belongs to.

AVAILABLE CLASSIFICATIONS for {category.upper()}:
{json.dumps(classification_names, indent=2)}

QUESTION:
{question_text}

ANSWER OPTIONS:
{options_text}

{f"EXPLANATION: {explanation_text}" if explanation_text else ""}

INSTRUCTIONS:
- Return a JSON array of classification names that apply to this question
- A question can have 1 or more classifications
- Only use classifications from the list above
- Be specific - don't over-classify
- Return an empty array [] if none apply

RESPONSE (JSON array only):"""

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that classifies SAT questions. Respond only with a valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
            )
            
            result_text = response.choices[0].message.content.strip()
            # Clean up the response - remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('\n', 1)[1] if '\n' in result_text else result_text[3:]
                result_text = result_text.rsplit('```', 1)[0]
            
            classification_names = json.loads(result_text)
            
            # Map names back to classification objects
            matched = []
            for name in classification_names:
                for c in available_classifications:
                    if c['name'].lower() == name.lower():
                        matched.append(c)
                        break
            
            return matched
            
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"AI classification failed: {e}"))
            return []

    def process_lesson_questions(self, dry_run, only_unclassified, limit, category_filter):
        """Process LessonQuestion objects"""
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Processing Lesson Questions ==='))
        
        queryset = LessonQuestion.objects.select_related('lesson').prefetch_related('options', 'classifications')
        
        if only_unclassified:
            queryset = queryset.filter(classifications__isnull=True).distinct()
        
        if limit:
            queryset = queryset[:limit]
        
        total = queryset.count()
        self.stdout.write(f"Found {total} lesson questions to process")
        
        classified_count = 0
        skipped_count = 0
        
        for i, lq in enumerate(queryset):
            category = self.get_category_for_lesson(lq)
            
            if category_filter and category != category_filter:
                skipped_count += 1
                continue
            
            # Build question text from JSON blocks
            question_text = self.extract_text_from_blocks(lq.text) if lq.text else ""
            options_text = "\n".join([f"- {opt.text}" for opt in lq.options.all()])
            explanation_text = None
            if lq.explanation:
                if isinstance(lq.explanation, list):
                    explanation_text = self.extract_text_from_blocks(lq.explanation)
                else:
                    explanation_text = str(lq.explanation)
            
            self.stdout.write(f"\n[{i+1}/{total}] Lesson: {lq.lesson.title}, Q{lq.order}")
            self.stdout.write(f"  Category: {category}")
            self.stdout.write(f"  Question: {question_text[:100]}...")
            
            # Get AI classifications
            matched = self.classify_with_ai(question_text, options_text, category, explanation_text)
            
            if matched:
                names = [m['name'] for m in matched]
                self.stdout.write(self.style.SUCCESS(f"  -> Classifications: {names}"))
                
                if not dry_run:
                    # Get actual QuestionClassification objects and set them
                    classification_ids = [m['id'] for m in matched]
                    classifications = QuestionClassification.objects.filter(id__in=classification_ids)
                    lq.classifications.set(classifications)
                    classified_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"  -> No classifications matched"))
            
            # Rate limiting
            time.sleep(0.2)
        
        self.stdout.write(self.style.SUCCESS(f"\nLesson Questions: Classified {classified_count}, Skipped {skipped_count}"))

    def process_passage_questions(self, dry_run, only_unclassified, limit, category_filter):
        """Process Question objects (passage questions)"""
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Processing Passage Questions ==='))
        
        # Passage questions are always reading
        if category_filter and category_filter != 'reading':
            self.stdout.write("Skipping passage questions (filtered to non-reading category)")
            return
        
        queryset = Question.objects.select_related('passage').prefetch_related('options', 'classifications')
        
        if only_unclassified:
            queryset = queryset.filter(classifications__isnull=True).distinct()
        
        if limit:
            queryset = queryset[:limit]
        
        total = queryset.count()
        self.stdout.write(f"Found {total} passage questions to process")
        
        classified_count = 0
        
        for i, q in enumerate(queryset):
            category = 'reading'
            
            # Build question text
            question_text = q.text or ""
            options_text = "\n".join([f"- {opt.text}" for opt in q.options.all()])
            explanation_text = q.explanation
            
            # Include passage context
            passage_context = ""
            if q.passage:
                passage_context = f"[From passage: {q.passage.title}]\n"
            
            self.stdout.write(f"\n[{i+1}/{total}] {passage_context}Q{q.order}: {question_text[:80]}...")
            
            # Get AI classifications  
            matched = self.classify_with_ai(question_text, options_text, category, explanation_text)
            
            if matched:
                names = [m['name'] for m in matched]
                self.stdout.write(self.style.SUCCESS(f"  -> Classifications: {names}"))
                
                if not dry_run:
                    classification_ids = [m['id'] for m in matched]
                    classifications = QuestionClassification.objects.filter(id__in=classification_ids)
                    q.classifications.set(classifications)
                    classified_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"  -> No classifications matched"))
            
            # Rate limiting
            time.sleep(0.2)
        
        self.stdout.write(self.style.SUCCESS(f"\nPassage Questions: Classified {classified_count}"))
