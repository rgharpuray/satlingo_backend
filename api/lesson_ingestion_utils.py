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
    Supports assets (diagrams/images) for math lessons.
    """
    from .models import Lesson, LessonQuestion, LessonQuestionOption, LessonAsset, LessonQuestionAsset
    
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
        
        # Validate chunks structure
        if not isinstance(lesson_data['chunks'], list):
            raise ValueError("'chunks' must be an array")
        
        # Extract questions from chunks
        questions_data = []
        question_order = 0
        
        for idx, chunk in enumerate(lesson_data['chunks']):
            if not isinstance(chunk, dict):
                raise ValueError(f"Chunk at index {idx} must be an object, got {type(chunk).__name__}")
            
            if chunk.get('type') == 'question':
                question_order += 1
                prompt = chunk.get('prompt', '')
                choices = chunk.get('choices', [])
                
                if not prompt:
                    raise ValueError(f"Question chunk at index {idx} is missing 'prompt' field")
                if not choices or not isinstance(choices, list):
                    raise ValueError(f"Question chunk at index {idx} must have a non-empty 'choices' array")
                
                correct_index = chunk.get('correct_answer_index', 0)
                if not isinstance(correct_index, int) or correct_index < 0:
                    raise ValueError(f"Question chunk at index {idx} has invalid 'correct_answer_index' (must be non-negative integer)")
                if correct_index >= len(choices):
                    raise ValueError(f"Question chunk at index {idx} has 'correct_answer_index' ({correct_index}) that is out of range (choices length: {len(choices)})")
                
                questions_data.append({
                    'chunk_index': idx,
                    'order': question_order,
                    'text': prompt,
                    'choices': choices,
                    'correct_answer_index': correct_index,
                    'assets': chunk.get('assets', []),  # Include assets from chunk
                })
        
        ingestion.error_message = f'Step 2/3: Found {len(questions_data)} questions in chunks.'
        ingestion.save()
        
        # Step 3: Create lesson, assets, and questions
        ingestion.error_message = 'Step 3/3: Creating lesson, assets, and questions in database...'
        ingestion.save()
        
        # Check if lesson with this lesson_id already exists
        existing_lesson = Lesson.objects.filter(lesson_id=lesson_data['lesson_id']).first()
        
        if existing_lesson and ingestion.created_lesson != existing_lesson:
            # Update existing lesson
            lesson = existing_lesson
            lesson.title = lesson_data['title']
            lesson.chunks = lesson_data['chunks']
            lesson.content = _render_lesson_content(lesson_data['chunks'])
            # Update lesson_type if provided in JSON
            if 'lesson_type' in lesson_data:
                lesson.lesson_type = lesson_data['lesson_type']
            lesson.save()
            
            # Delete old questions and assets
            lesson.questions.all().delete()
            lesson.assets.all().delete()
        elif not ingestion.created_lesson:
            # Create new lesson
            lesson = Lesson.objects.create(
                lesson_id=lesson_data['lesson_id'],
                title=lesson_data['title'],
                chunks=lesson_data['chunks'],
                content=_render_lesson_content(lesson_data['chunks']),
                difficulty=lesson_data.get('difficulty', 'Medium'),
                tier=lesson_data.get('tier', 'free'),
                lesson_type=lesson_data.get('lesson_type', 'reading'),  # Support lesson_type in JSON
            )
        else:
            lesson = ingestion.created_lesson
        
        # Process shared assets (for math lessons with diagrams)
        assets_map = {}  # Map asset_id to LessonAsset object
        shared_assets = lesson_data.get('shared_assets', [])
        if shared_assets:
            for asset_data in shared_assets:
                asset_id = asset_data.get('asset_id')
                if not asset_id:
                    continue
                
                asset = LessonAsset.objects.create(
                    lesson=lesson,
                    asset_id=asset_id,
                    type=asset_data.get('type', 'image'),
                    s3_url=asset_data.get('s3_url', ''),
                )
                assets_map[asset_id] = asset
        
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
            
            # Link assets to question if specified
            question_assets = q_data.get('assets', [])
            if question_assets:
                for asset_id in question_assets:
                    if asset_id in assets_map:
                        LessonQuestionAsset.objects.create(
                            question=question,
                            asset=assets_map[asset_id],
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

