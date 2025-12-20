"""
Utilities for ingesting lessons from JSON files
"""
import json
from django.db import transaction
from django.utils import timezone


def process_lesson_ingestion(ingestion):
    """
    Process a lesson ingestion from JSON file.
    Creates a Lesson with questions extracted from chunks.
    """
    from .models import Lesson, LessonQuestion, LessonQuestionOption
    
    try:
        ingestion.status = 'processing'
        ingestion.error_message = 'Step 1/3: Loading JSON data...'
        ingestion.save()
        
        # Load JSON data
        if not ingestion.parsed_data:
            # Try to load from file if parsed_data is empty
            with open(ingestion.file_path, 'r', encoding='utf-8') as f:
                ingestion.parsed_data = json.load(f)
                ingestion.save()
        
        lesson_data = ingestion.parsed_data
        
        # Validate required fields
        if 'lesson_id' not in lesson_data:
            raise ValueError("Missing required field: lesson_id")
        if 'title' not in lesson_data:
            raise ValueError("Missing required field: title")
        if 'chunks' not in lesson_data:
            raise ValueError("Missing required field: chunks")
        
        ingestion.error_message = 'Step 2/3: Processing chunks and extracting questions...'
        ingestion.save()
        
        # Extract questions from chunks
        questions_data = []
        question_order = 0
        
        for idx, chunk in enumerate(lesson_data['chunks']):
            if chunk.get('type') == 'question':
                question_order += 1
                questions_data.append({
                    'chunk_index': idx,
                    'order': question_order,
                    'text': chunk.get('prompt', ''),
                    'choices': chunk.get('choices', []),
                    'correct_answer_index': chunk.get('correct_answer_index', 0),
                })
        
        ingestion.error_message = f'Step 2/3: Found {len(questions_data)} questions in chunks.'
        ingestion.save()
        
        # Step 3: Create lesson and questions
        ingestion.error_message = 'Step 3/3: Creating lesson and questions in database...'
        ingestion.save()
        
        # Check if lesson with this lesson_id already exists
        existing_lesson = Lesson.objects.filter(lesson_id=lesson_data['lesson_id']).first()
        
        if existing_lesson and ingestion.created_lesson != existing_lesson:
            # Update existing lesson
            lesson = existing_lesson
            lesson.title = lesson_data['title']
            lesson.chunks = lesson_data['chunks']
            lesson.content = _render_lesson_content(lesson_data['chunks'])
            lesson.save()
            
            # Delete old questions
            lesson.questions.all().delete()
        elif not ingestion.created_lesson:
            # Create new lesson
            lesson = Lesson.objects.create(
                lesson_id=lesson_data['lesson_id'],
                title=lesson_data['title'],
                chunks=lesson_data['chunks'],
                content=_render_lesson_content(lesson_data['chunks']),
                difficulty=lesson_data.get('difficulty', 'Medium'),
                tier=lesson_data.get('tier', 'free'),
            )
        else:
            lesson = ingestion.created_lesson
        
        # Create questions
        for q_data in questions_data:
            question = LessonQuestion.objects.create(
                lesson=lesson,
                text=q_data['text'],
                correct_answer_index=q_data['correct_answer_index'],
                order=q_data['order'],
                chunk_index=q_data['chunk_index'],
            )
            
            # Create options
            for opt_idx, choice_text in enumerate(q_data['choices']):
                LessonQuestionOption.objects.create(
                    question=question,
                    text=choice_text,
                    order=opt_idx,
                )
        
        ingestion.created_lesson = lesson
        ingestion.status = 'completed'
        ingestion.error_message = f'✓ Successfully created lesson "{lesson.title}" with {len(questions_data)} questions.'
        ingestion.save()
        
    except Exception as e:
        import traceback
        ingestion.status = 'failed'
        ingestion.error_message = f'✗ Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
        ingestion.save()
        raise


def _render_lesson_content(chunks):
    """
    Render chunks into a flat text content for display/search.
    This creates a readable version of the lesson content.
    """
    content_parts = []
    
    for chunk in chunks:
        chunk_type = chunk.get('type', '')
        
        if chunk_type == 'header':
            level = chunk.get('level', 1)
            text = chunk.get('text', '')
            content_parts.append(f"{'#' * level} {text}\n")
        
        elif chunk_type == 'paragraph':
            text = chunk.get('text', '')
            content_parts.append(f"{text}\n\n")
        
        elif chunk_type == 'example':
            text = chunk.get('text', '')
            content_parts.append(f"Example: {text}\n\n")
        
        elif chunk_type == 'example_correct':
            text = chunk.get('text', '')
            content_parts.append(f"✓ Correct: {text}\n\n")
        
        elif chunk_type == 'example_incorrect':
            text = chunk.get('text', '')
            content_parts.append(f"✗ Incorrect: {text}\n\n")
        
        elif chunk_type == 'rule':
            text = chunk.get('text', '')
            content_parts.append(f"Rule: {text}\n\n")
        
        elif chunk_type == 'definition':
            term = chunk.get('term', '')
            text = chunk.get('text', '')
            content_parts.append(f"{term}: {text}\n\n")
        
        elif chunk_type in ['list', 'bullet_list']:
            items = chunk.get('items', [])
            prefix = '- ' if chunk_type == 'bullet_list' else '1. '
            for item in items:
                content_parts.append(f"{prefix}{item}\n")
            content_parts.append("\n")
        
        elif chunk_type == 'question':
            prompt = chunk.get('prompt', '')
            content_parts.append(f"Question: {prompt}\n")
            choices = chunk.get('choices', [])
            for idx, choice in enumerate(choices):
                content_parts.append(f"  {chr(65 + idx)}. {choice}\n")
            content_parts.append("\n")
        
        elif chunk_type == 'note':
            text = chunk.get('text', '')
            content_parts.append(f"Note: {text}\n\n")
        
        elif chunk_type == 'warning':
            text = chunk.get('text', '')
            content_parts.append(f"Warning: {text}\n\n")
        
        elif chunk_type == 'summary':
            text = chunk.get('text', '')
            content_parts.append(f"Summary: {text}\n\n")
    
    return ''.join(content_parts).strip()

