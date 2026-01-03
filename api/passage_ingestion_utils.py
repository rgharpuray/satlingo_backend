"""
Utilities for processing passage ingestion from JSON data
"""
from django.db import transaction
from .models import Passage, Question, QuestionOption


def process_passage_ingestion(ingestion):
    """
    Process a passage ingestion from parsed JSON data.
    
    Args:
        ingestion: PassageIngestion instance with parsed_data populated
        
    Raises:
        Exception: If processing fails
    """
    if not ingestion.parsed_data:
        raise ValueError("Cannot process ingestion: parsed_data is empty. File should have been converted to JSON first.")
    
    parsed_data = ingestion.parsed_data
    
    # Validate required fields
    if not isinstance(parsed_data, dict):
        raise ValueError("parsed_data must be a dictionary")
    
    required_fields = ['title', 'content', 'questions']
    for field in required_fields:
        if field not in parsed_data:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(parsed_data['questions'], list):
        raise ValueError("'questions' must be an array")
    
    if len(parsed_data['questions']) == 0:
        raise ValueError("'questions' array cannot be empty")
    
    # Validate questions
    for idx, q_data in enumerate(parsed_data['questions']):
        if not isinstance(q_data, dict):
            raise ValueError(f"Question {idx + 1} must be an object")
        
        required_q_fields = ['text', 'options', 'correct_answer_index', 'order']
        for field in required_q_fields:
            if field not in q_data:
                raise ValueError(f"Question {idx + 1} missing required field: {field}")
        
        if not isinstance(q_data['options'], list):
            raise ValueError(f"Question {idx + 1} 'options' must be an array")
        
        if len(q_data['options']) != 4:
            raise ValueError(f"Question {idx + 1} must have exactly 4 options, found {len(q_data['options'])}")
        
        if not isinstance(q_data['correct_answer_index'], int):
            raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be an integer")
        
        if q_data['correct_answer_index'] < 0 or q_data['correct_answer_index'] >= 4:
            raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be 0-3, found {q_data['correct_answer_index']}")
        
        # Validate option strings
        for opt_idx, option in enumerate(q_data['options']):
            if not isinstance(option, str) or not option.strip():
                raise ValueError(f"Question {idx + 1}, Option {opt_idx + 1} is empty or invalid")
    
    # Create passage and questions in a transaction
    with transaction.atomic():
        # Normalize content: convert literal \n strings to actual newlines
        content = parsed_data['content']
        if isinstance(content, str):
            # Handle cases where AI might return literal \n strings
            content = content.replace('\\\\n', '\n')
            content = content.replace('\\n', '\n')
        
        # Create passage
        passage = Passage.objects.create(
            title=parsed_data['title'],
            content=content,
            difficulty=parsed_data.get('difficulty', 'Medium'),
            tier=parsed_data.get('tier', 'free')
        )
        
        # Create questions and options
        for q_data in parsed_data['questions']:
            question = Question.objects.create(
                passage=passage,
                text=q_data['text'],
                correct_answer_index=q_data['correct_answer_index'],
                explanation=q_data.get('explanation', ''),
                order=q_data['order']
            )
            
            # Create options
            for opt_idx, option_text in enumerate(q_data['options']):
                QuestionOption.objects.create(
                    question=question,
                    text=option_text,
                    order=opt_idx
                )
        
        # Link the passage to the ingestion
        ingestion.created_passage = passage
        ingestion.status = 'completed'
        ingestion.error_message = f'Successfully created passage with {len(parsed_data["questions"])} questions.'
        ingestion.save()
    
    return passage







