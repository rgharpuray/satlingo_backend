"""
Utilities for ingesting writing sections from documents/JSON files
"""
import json
from django.db import transaction
from django.utils import timezone


def process_writing_ingestion(ingestion):
    """
    Process a writing section ingestion from JSON file.
    Creates a WritingSection with selections and questions.
    """
    from .models import WritingSection, WritingSectionSelection, WritingSectionQuestion, WritingSectionQuestionOption
    
    try:
        ingestion.status = 'processing'
        ingestion.error_message = 'Step 1/3: Loading JSON data...'
        ingestion.save()
        
        # Load JSON data
        if not ingestion.parsed_data:
            # Try to load from file if parsed_data is empty
            # Only try to read as JSON if it's actually a JSON file
            import os
            file_ext = os.path.splitext(ingestion.file_path)[1].lower()
            if file_ext == '.json':
                try:
                    with open(ingestion.file_path, 'r', encoding='utf-8') as f:
                        ingestion.parsed_data = json.load(f)
                        ingestion.save()
                except UnicodeDecodeError:
                    # Try with error handling for non-UTF-8 files
                    with open(ingestion.file_path, 'r', encoding='utf-8', errors='replace') as f:
                        ingestion.parsed_data = json.load(f)
                        ingestion.save()
            else:
                # For non-JSON files (PDF, DOCX, etc.), they should have been converted to JSON by GPT
                # If parsed_data is still empty, the GPT conversion must have failed
                raise ValueError(
                    f"Cannot process non-JSON file ({file_ext}). "
                    f"The file should have been converted to JSON using GPT first. "
                    f"Please check the ingestion error message for GPT conversion details."
                )
        
        writing_data = ingestion.parsed_data
        
        # Validate required fields
        if 'title' not in writing_data:
            raise ValueError("Missing required field: title")
        if 'content' not in writing_data:
            raise ValueError("Missing required field: content")
        if 'selections' not in writing_data:
            raise ValueError("Missing required field: selections")
        if 'questions' not in writing_data:
            raise ValueError("Missing required field: questions")
        
        ingestion.error_message = 'Step 2/3: Processing selections and questions...'
        ingestion.save()
        
        # Validate selections structure
        if not isinstance(writing_data['selections'], list):
            raise ValueError("'selections' must be an array")
        
        # Validate questions structure
        if not isinstance(writing_data['questions'], list):
            raise ValueError("'questions' must be an array")
        
        # Step 3: Create writing section, selections, and questions
        ingestion.error_message = 'Step 3/3: Creating writing section in database...'
        ingestion.save()
        
        # Check if writing section with this title already exists (or use a unique identifier if provided)
        existing_section = None
        if 'id' in writing_data:
            existing_section = WritingSection.objects.filter(id=writing_data['id']).first()
        
        if existing_section and ingestion.created_writing_section != existing_section:
            # Update existing section
            section = existing_section
            section.title = writing_data['title']
            section.content = writing_data['content']
            section.difficulty = writing_data.get('difficulty', 'Medium')
            section.tier = writing_data.get('tier', 'free')
            section.save()
            
            # Delete old selections and questions
            section.selections.all().delete()
            section.questions.all().delete()
        elif not ingestion.created_writing_section:
            # Create new section
            section = WritingSection.objects.create(
                title=writing_data['title'],
                content=writing_data['content'],
                difficulty=writing_data.get('difficulty', 'Medium'),
                tier=writing_data.get('tier', 'free'),
            )
        else:
            section = ingestion.created_writing_section
        
        # Create selections
        for sel_data in writing_data['selections']:
            if not isinstance(sel_data, dict):
                ingestion.error_message = f'Warning: Selection is not an object, skipping.'
                ingestion.save()
                continue
            
            number = sel_data.get('number')
            start_char = sel_data.get('start_char')
            end_char = sel_data.get('end_char')
            selected_text = sel_data.get('selected_text', '').strip()
            
            if number is None:
                ingestion.error_message = f'Warning: Selection missing number, skipping.'
                ingestion.save()
                continue
            if start_char is None or end_char is None:
                ingestion.error_message = f'Warning: Selection {number} missing positions, skipping.'
                ingestion.save()
                continue
            
            # Validate and fix positions
            if start_char < 0:
                start_char = 0
            if end_char <= start_char:
                ingestion.error_message = f'Warning: Selection {number} has invalid positions, skipping.'
                ingestion.save()
                continue
            if end_char > len(section.content):
                end_char = len(section.content)
            if start_char >= len(section.content):
                ingestion.error_message = f'Warning: Selection {number} start position out of bounds, skipping.'
                ingestion.save()
                continue
            
            # Check if text matches - if not, try to fix it
            actual_text = section.content[start_char:end_char]
            if actual_text != selected_text:
                # Try to find the selected_text in the content near the given position
                search_start = max(0, start_char - 100)
                search_end = min(len(section.content), start_char + 100)
                search_area = section.content[search_start:search_end]
                
                pos = search_area.find(selected_text)
                if pos != -1:
                    # Found it! Update positions
                    start_char = search_start + pos
                    end_char = start_char + len(selected_text)
                    actual_text = selected_text
                else:
                    # Try case-insensitive search
                    selected_lower = selected_text.lower()
                    search_area_lower = section.content[search_start:search_end].lower()
                    pos = search_area_lower.find(selected_lower)
                    if pos != -1:
                        start_char = search_start + pos
                        end_char = start_char + len(selected_text)
                        actual_text = section.content[start_char:end_char]
                        selected_text = actual_text  # Use the actual text from content
                    else:
                        # Can't find it - use whatever text is at the position
                        if len(actual_text.strip()) > 0:
                            selected_text = actual_text.strip()
                            ingestion.error_message = f'Warning: Selection {number} text not found, using text at position.'
                            ingestion.save()
                        else:
                            ingestion.error_message = f'Warning: Selection {number} has no valid text, skipping.'
                            ingestion.save()
                            continue
            
            try:
                WritingSectionSelection.objects.create(
                    writing_section=section,
                    number=number,
                    start_char=start_char,
                    end_char=end_char,
                    selected_text=selected_text,
                )
            except Exception as e:
                ingestion.error_message = f'Warning: Failed to create selection {number}: {str(e)}, skipping.'
                ingestion.save()
                continue
        
        # Create questions
        questions_created = 0
        for q_idx, q_data in enumerate(writing_data.get('questions', [])):
            if not isinstance(q_data, dict):
                ingestion.error_message = f'Warning: Question at index {q_idx} is not an object, skipping.'
                ingestion.save()
                continue
            
            text = q_data.get('text', '').strip()
            choices = q_data.get('choices', [])
            correct_answer_index = q_data.get('correct_answer_index', 0)
            selection_number = q_data.get('selection_number')
            
            if not text:
                ingestion.error_message = f'Warning: Question at index {q_idx} missing text, skipping.'
                ingestion.save()
                continue
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                ingestion.error_message = f'Warning: Question at index {q_idx} has no choices, skipping.'
                ingestion.save()
                continue
            if not isinstance(correct_answer_index, int) or correct_answer_index < 0:
                ingestion.error_message = f'Warning: Question at index {q_idx} has invalid correct_answer_index, defaulting to 0.'
                ingestion.save()
                correct_answer_index = 0
            if correct_answer_index >= len(choices):
                ingestion.error_message = f'Warning: Question at index {q_idx} has correct_answer_index out of range, defaulting to 0.'
                ingestion.save()
                correct_answer_index = 0
            
            try:
                question = WritingSectionQuestion.objects.create(
                    writing_section=section,
                    text=text,
                    correct_answer_index=correct_answer_index,
                    explanation=q_data.get('explanation'),
                    order=questions_created + 1,
                    selection_number=selection_number,
                )
                
                # Create options
                for opt_idx, choice_text in enumerate(choices):
                    WritingSectionQuestionOption.objects.create(
                        question=question,
                        text=str(choice_text).strip(),
                        order=opt_idx,
                    )
                
                questions_created += 1
            except Exception as e:
                ingestion.error_message = f'Warning: Failed to create question at index {q_idx}: {str(e)}, skipping.'
                ingestion.save()
                continue
        
        ingestion.created_writing_section = section
        ingestion.status = 'completed'
        ingestion.error_message = f'✓ Successfully created writing section "{section.title}" with {len(writing_data["selections"])} selections and {questions_created} questions.'
        ingestion.save()
        
    except Exception as e:
        import traceback
        ingestion.status = 'failed'
        ingestion.error_message = f'✗ Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
        ingestion.save()
        raise

