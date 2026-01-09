"""
Utilities for converting passage documents to JSON using GPT
"""
import json
import os
from django.conf import settings
from .ingestion_utils import (
    extract_text_from_document, extract_text_from_pdf,
    extract_text_from_docx, extract_text_from_txt,
    HAS_OPENAI, HAS_PDF, HAS_DOCX
)


def get_passage_schema_prompt():
    """Get the passage JSON schema prompt for GPT"""
    return """# Passage JSON Schema

This document describes the expected JSON format for passage ingestion. Use this schema when converting reading passages into JSON format for the system.

## Root Structure

```json
{
  "title": "string (required, passage title)",
  "content": "string (required, full passage text)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "questions": [ /* array of question objects (required) */ ]
}
```

## Question Structure

Questions are multiple choice questions about the passage.

```json
{
  "text": "What is the main idea of the passage?",  // REQUIRED
  "options": [  // REQUIRED - must be an array with exactly 4 options
    "Option A text",
    "Option B text",
    "Option C text",
    "Option D text"
  ],
  "correct_answer_index": 2,  // REQUIRED - integer index (0-based) of correct answer, must be 0-3
  "order": 1,  // REQUIRED - integer, question order (1-based)
  "explanation": "This is the correct answer because..."  // optional
}
```

## Complete Example

```json
{
  "title": "The History of Coffee",
  "content": "Coffee has a rich history that spans centuries. Originating in Ethiopia, coffee spread throughout the Middle East and eventually to Europe and the Americas. Today, it is one of the most consumed beverages in the world.",
  "difficulty": "Medium",
  "tier": "free",
  "questions": [
    {
      "text": "According to the passage, where did coffee originate?",
      "options": [
        "The Middle East",
        "Ethiopia",
        "Europe",
        "The Americas"
      ],
      "correct_answer_index": 1,
      "order": 1,
      "explanation": "The passage states that coffee originated in Ethiopia."
    },
    {
      "text": "What is the main topic of the passage?",
      "options": [
        "The health benefits of coffee",
        "The history of coffee",
        "How to brew coffee",
        "Coffee prices around the world"
      ],
      "correct_answer_index": 1,
      "order": 2,
      "explanation": "The passage focuses on the historical spread of coffee."
    }
  ]
}
```

## Important Notes

1. **Content Format**: The `content` field should contain the FULL passage text. Preserve paragraph breaks and formatting.

2. **Question Requirements**:
   - Each question MUST have exactly 4 options (A, B, C, D)
   - `correct_answer_index` must be 0, 1, 2, or 3 (corresponding to the 4 options)
   - `order` should start at 1 and increment for each question
   - All options must be non-empty strings

3. **Required Fields**:
   - Root level: `title`, `content`, `questions`
   - Question: `text`, `options`, `correct_answer_index`, `order`

4. **Optional Fields**:
   - Root level: `difficulty` (defaults to "Medium"), `tier` (defaults to "free")
   - Question: `explanation`

5. **Default Values**:
   - `difficulty`: "Medium"
   - `tier`: "free"

## Conversion Guidelines

When converting a passage document to this format:
1. Extract the full passage text (preserve paragraph structure)
2. Identify all questions and their answer choices
3. Ensure each question has exactly 4 options
4. Number questions sequentially (order: 1, 2, 3, ...)
5. Identify the correct answer for each question (correct_answer_index: 0-3)
6. Optionally add explanations for each question

## Validation Requirements

The system will validate:
- `title` is present and non-empty
- `content` is present and non-empty
- `questions` is an array with at least one question
- Each question has `text`, `options` (exactly 4 items), `correct_answer_index` (0-3), and `order`
- All option strings are non-empty

-------

Can we do the same process of json generation for the following ATTACHED DOCUMENT"""


def convert_document_to_passage_json(file_path, file_name):
    """
    Convert a document (PDF, DOCX, TXT) to passage JSON using GPT.
    
    Args:
        file_path: Path to the uploaded file
        file_name: Original filename
        
    Returns:
        dict: Parsed passage JSON data
        
    Raises:
        Exception: If conversion fails
    """
    if not HAS_OPENAI:
        raise Exception("OpenAI library not installed. Install openai package.")
    
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise Exception("OpenAI API key not configured")
    
    # Determine file type and extract text
    file_ext = os.path.splitext(file_name)[1].lower()
    
    if file_ext == '.pdf':
        if not HAS_PDF:
            raise Exception("PDF processing library not installed. Install pdf2image and poppler.")
        extracted_text = extract_text_from_pdf(file_path)
    elif file_ext in ['.docx', '.doc']:
        if not HAS_DOCX:
            raise Exception("DOCX processing library not installed. Install python-docx.")
        extracted_text = extract_text_from_docx(file_path)
    elif file_ext == '.txt':
        extracted_text = extract_text_from_txt(file_path)
    else:
        raise Exception(f"Unsupported file type: {file_ext}. Supported types: .pdf, .docx, .txt")
    
    if not extracted_text or not extracted_text.strip():
        raise Exception("No text could be extracted from the document. The file may be empty or corrupted.")
    
    # Call GPT to convert to JSON
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    schema_prompt = get_passage_schema_prompt()
    user_prompt = f"{schema_prompt}\n\nDocument content:\n\n{extracted_text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for better JSON generation
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that converts passage documents into structured JSON format. Always return valid JSON that matches the schema exactly. Do not include any markdown code blocks or explanations - return ONLY the raw JSON object."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent JSON output
            response_format={"type": "json_object"}  # Force JSON response
        )
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    
    # Extract JSON from response
    json_text = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present (though response_format should prevent this)
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    elif json_text.startswith("```"):
        json_text = json_text[3:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()
    
    # Parse JSON
    try:
        passage_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise Exception(f"GPT returned invalid JSON: {str(e)}\n\nResponse was: {json_text[:500]}")
    
    # Validate basic structure
    if not isinstance(passage_data, dict):
        raise ValueError("GPT returned invalid JSON: expected an object")
    if 'title' not in passage_data:
        raise ValueError("GPT returned JSON missing 'title' field")
    if 'content' not in passage_data:
        raise ValueError("GPT returned JSON missing 'content' field")
    if 'questions' not in passage_data:
        raise ValueError("GPT returned JSON missing 'questions' field")
    if not isinstance(passage_data['questions'], list):
        raise ValueError("GPT returned JSON with 'questions' that is not an array")
    if len(passage_data['questions']) == 0:
        raise ValueError("GPT returned JSON with empty 'questions' array")
    
    # Validate each question
    for idx, q in enumerate(passage_data['questions']):
        if not isinstance(q, dict):
            raise ValueError(f"Question {idx + 1} is not an object")
        if 'text' not in q:
            raise ValueError(f"Question {idx + 1} missing 'text' field")
        if 'options' not in q:
            raise ValueError(f"Question {idx + 1} missing 'options' field")
        if not isinstance(q['options'], list):
            raise ValueError(f"Question {idx + 1} 'options' is not an array")
        if len(q['options']) != 4:
            raise ValueError(f"Question {idx + 1} must have exactly 4 options, found {len(q['options'])}")
        if 'correct_answer_index' not in q:
            raise ValueError(f"Question {idx + 1} missing 'correct_answer_index' field")
        if not isinstance(q['correct_answer_index'], int):
            raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be an integer")
        if q['correct_answer_index'] < 0 or q['correct_answer_index'] >= 4:
            raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be 0-3, found {q['correct_answer_index']}")
        if 'order' not in q:
            raise ValueError(f"Question {idx + 1} missing 'order' field")
        # Validate option strings
        for opt_idx, option in enumerate(q['options']):
            if not isinstance(option, str) or not option.strip():
                raise ValueError(f"Question {idx + 1}, Option {opt_idx + 1} is empty or invalid")
    
    return passage_data














