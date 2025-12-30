"""
Utilities for processing math section ingestion from JSON data
"""
from django.db import transaction
from .models import MathSection, MathAsset, MathQuestion, MathQuestionOption, MathQuestionAsset


def process_math_ingestion(ingestion):
    """
    Process a math section ingestion from parsed JSON data.
    
    Args:
        ingestion: MathSectionIngestion instance with parsed_data populated
        
    Raises:
        Exception: If processing fails
    """
    if not ingestion.parsed_data:
        raise ValueError("Cannot process ingestion: parsed_data is empty. File should have been converted to JSON first.")
    
    parsed_data = ingestion.parsed_data
    
    # Validate required fields
    if not isinstance(parsed_data, dict):
        raise ValueError("parsed_data must be a dictionary")
    
    required_fields = ['section_id', 'title', 'questions']
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
        
        required_q_fields = ['question_id', 'prompt', 'choices', 'explanation']
        for field in required_q_fields:
            if field not in q_data:
                raise ValueError(f"Question {idx + 1} missing required field: {field}")
        
        if not isinstance(q_data['choices'], list) or len(q_data['choices']) == 0:
            raise ValueError(f"Question {idx + 1} 'choices' must be a non-empty array")
        
        if not isinstance(q_data['explanation'], list):
            raise ValueError(f"Question {idx + 1} 'explanation' must be an array")
        
        # Validate explanation blocks
        for exp_idx, exp_block in enumerate(q_data['explanation']):
            if not isinstance(exp_block, dict):
                raise ValueError(f"Question {idx + 1}, Explanation block {exp_idx + 1} must be an object")
            if 'type' not in exp_block:
                raise ValueError(f"Question {idx + 1}, Explanation block {exp_idx + 1} missing 'type' field")
            exp_type = exp_block['type']
            if exp_type == 'paragraph' or exp_type == 'note' or exp_type == 'example':
                if 'text' not in exp_block:
                    raise ValueError(f"Question {idx + 1}, Explanation block {exp_idx + 1} (type: {exp_type}) missing 'text' field")
            elif exp_type == 'equation':
                if 'latex' not in exp_block:
                    raise ValueError(f"Question {idx + 1}, Explanation block {exp_idx + 1} (type: equation) missing 'latex' field")
            else:
                raise ValueError(f"Question {idx + 1}, Explanation block {exp_idx + 1} has invalid type: {exp_type}")
        
        if 'correct_answer_index' in q_data:
            if not isinstance(q_data['correct_answer_index'], int):
                raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be an integer")
            if q_data['correct_answer_index'] < 0 or q_data['correct_answer_index'] >= len(q_data['choices']):
                raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be 0-{len(q_data['choices'])-1}")
    
    # Validate assets if present
    asset_ids = set()
    if 'shared_assets' in parsed_data and isinstance(parsed_data['shared_assets'], list):
        for idx, asset_data in enumerate(parsed_data['shared_assets']):
            if not isinstance(asset_data, dict):
                raise ValueError(f"Asset {idx + 1} must be an object")
            required_asset_fields = ['asset_id', 'type', 's3_url']
            for field in required_asset_fields:
                if field not in asset_data:
                    raise ValueError(f"Asset {idx + 1} missing required field: {field}")
            asset_ids.add(asset_data['asset_id'])
    
    # Validate asset references in questions
    for idx, q_data in enumerate(parsed_data['questions']):
        if 'assets' in q_data and isinstance(q_data['assets'], list):
            for asset_id in q_data['assets']:
                if asset_id not in asset_ids:
                    raise ValueError(f"Question {idx + 1} references asset '{asset_id}' which does not exist in shared_assets")
    
    # Create math section and related objects in a transaction
    with transaction.atomic():
        # Create math section
        math_section = MathSection.objects.create(
            section_id=parsed_data['section_id'],
            title=parsed_data['title'],
            difficulty=parsed_data.get('difficulty', 'Medium'),
            tier=parsed_data.get('tier', 'free')
        )
        
        # Create assets
        asset_map = {}  # Map asset_id to MathAsset object
        if 'shared_assets' in parsed_data and isinstance(parsed_data['shared_assets'], list):
            for asset_data in parsed_data['shared_assets']:
                asset = MathAsset.objects.create(
                    math_section=math_section,
                    asset_id=asset_data['asset_id'],
                    type=asset_data.get('type', 'image'),
                    s3_url=asset_data['s3_url']
                )
                asset_map[asset_data['asset_id']] = asset
        
        # Create questions and options
        for order, q_data in enumerate(parsed_data['questions'], start=1):
            question = MathQuestion.objects.create(
                math_section=math_section,
                question_id=q_data['question_id'],
                prompt=q_data['prompt'],
                correct_answer_index=q_data.get('correct_answer_index', 0),
                explanation=q_data['explanation'],  # Store as JSON
                order=order
            )
            
            # Create options
            for opt_idx, option_text in enumerate(q_data['choices']):
                MathQuestionOption.objects.create(
                    question=question,
                    text=option_text,
                    order=opt_idx
                )
            
            # Link assets to question
            if 'assets' in q_data and isinstance(q_data['assets'], list):
                for asset_id in q_data['assets']:
                    if asset_id in asset_map:
                        MathQuestionAsset.objects.create(
                            question=question,
                            asset=asset_map[asset_id]
                        )
        
        # Link the math section to the ingestion
        ingestion.created_math_section = math_section
        ingestion.status = 'completed'
        ingestion.error_message = f'Successfully created math section with {len(parsed_data["questions"])} questions and {len(asset_map)} assets.'
        ingestion.save()
    
    return math_section



