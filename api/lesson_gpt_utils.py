"""
Utilities for converting lesson documents to JSON using GPT
"""
import json
import os
from django.conf import settings
from .ingestion_utils import (
    extract_text_from_document, extract_text_from_pdf,
    extract_text_from_docx, extract_text_from_txt,
    HAS_OPENAI, HAS_PDF, HAS_DOCX
)


def get_lesson_schema_prompt():
    """Get the lesson JSON schema prompt for GPT"""
    return """# Lesson JSON Schema
This document describes the expected JSON format for lesson ingestion. Use this schema when converting lessons into JSON format for the system.

## Root Structure
```json
{
  "lesson_id": "string (required, unique identifier, e.g., 'commas')",
  "title": "string (required, lesson title)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "chunks": [ /* array of chunk objects (required) */ ]
}
```

## Chunk Types
The `chunks` array contains objects that represent different types of content. Each chunk must have a `type` field. The following chunk types are supported:

### 1. Header
Creates a heading at various levels.
```json
{
  "type": "header",
  "level": 1,  // integer, 1-6 (1 = largest, 6 = smallest)
  "text": "Section Title"
}
```

### 2. Paragraph
Regular paragraph text.
```json
{
  "type": "paragraph",
  "text": "This is a paragraph of explanatory text."
}
```

### 3. Example
Displays an example sentence or phrase in a highlighted box.
```json
{
  "type": "example",
  "text": "I had to buy apples, bananas, and cucumbers."
}
```

### 4. Example (Correct)
Shows a correct example with a green checkmark.
```json
{
  "type": "example_correct",
  "text": "I knew all of the subjects on the test, so I was sure to get an A."
}
```

### 5. Example (Incorrect)
Shows an incorrect example with a red X.
```json
{
  "type": "example_incorrect",
  "text": "I knew every subject on the test, I was sure to get an A."
}
```

### 6. Question
Multiple choice question embedded in the lesson. Questions are extracted and stored separately for tracking.
```json
{
  "type": "question",
  "question_type": "multiple_choice",  // optional, currently only multiple_choice is supported
  "prompt": "I did my laundry made my bed and performed my nightly breathing exercises.",  // REQUIRED
  "choices": [  // REQUIRED - must be a non-empty array
    "NO CHANGE",
    "I did, my laundry, made, my bed, and performed, my nightly breathing exercises.",
    "I did my laundry, made my bed, and performed my nightly breathing exercises.",
    "I did, my laundry, made my bed, and performed my nightly breathing exercises."
  ],
  "correct_answer_index": 2  // optional, integer index (0-based) of correct answer, defaults to 0 if not provided. If provided, must be >= 0 and < length of choices array
}
```
**Important:** 
- `prompt` is **REQUIRED** - the question will fail validation if missing
- `choices` is **REQUIRED** - must be a non-empty array, or validation will fail
- `correct_answer_index` is optional. If not provided, defaults to 0 (first choice). If provided, must be a valid index (0-based) within the choices array, otherwise validation will fail.

### 7. List
Ordered list (numbered).
```json
{
  "type": "list",
  "items": [
    "First item",
    "Second item",
    "Third item"
  ]
}
```

### 8. Bullet List
Unordered list (bullets).
```json
{
  "type": "bullet_list",
  "items": [
    "Item one",
    "Item two",
    "Item three"
  ]
}
```

### 9. Rule
Highlights an important rule or principle.
```json
{
  "type": "rule",
  "text": "We can never connect two independent clauses together with just a comma."
}
```

### 10. Definition
Term and definition pair.
```json
{
  "type": "definition",
  "term": "Independent Clause",
  "text": "A clause that has a subject, a verb, and a fully fleshed out thought. It can stand alone as its own sentence."
}
```

### 11. Note
Informational note.
```json
{
  "type": "note",
  "text": "This is an important note to remember."
}
```

### 12. Warning
Warning or caution.
```json
{
  "type": "warning",
  "text": "Be careful not to confuse this with similar concepts."
}
```

### 13. Summary
Summary section.
```json
{
  "type": "summary",
  "text": "In summary, commas are used in three main ways: lists, dependent clauses, and independent clauses."
}
```

## Important Notes
1. **Order Matters**: Chunks are rendered in the order they appear in the array. Questions are embedded inline where they appear in the chunks.
2. **Question Extraction**: Questions are automatically extracted from question chunks and stored separately for tracking purposes. The `chunk_index` field tracks which chunk the question came from.
3. **Required Fields**:
   - Root level: `lesson_id`, `title`, `chunks`
   - Each chunk: `type` (must be a string)
   - Each chunk must be an object (not a string, number, or null)
   - Header chunks: `level` (integer 1-6), `text` (string)
   - Paragraph/Example/Rule/Note/Warning/Summary chunks: `text` (string)
   - Question chunks: `prompt` (string, non-empty), `choices` (array, non-empty)
   - List/Bullet List chunks: `items` (array)
   - Definition chunks: `term` (string), `text` (string)
4. **Optional Fields**:
   - Root level: `difficulty`, `tier`
   - Question chunks: `question_type`, `correct_answer_index`
5. **Default Values**:
   - `difficulty`: "Medium"
   - `tier`: "free"
   - `correct_answer_index`: 0 (first choice)

## Conversion Guidelines
When converting lesson content to this format:
1. **Break content into logical chunks** (paragraphs, examples, questions, etc.)
2. **Use appropriate chunk types** for different content:
   - Headers for section titles (use appropriate level: 1 for main title, 2 for major sections, 3 for subsections)
   - Paragraphs for explanatory text
   - Examples for sample sentences
   - Questions for practice problems
3. **Maintain the natural flow** of the lesson - chunks are rendered in order
4. **Embed questions inline** where they appear in the content
5. **Ensure all required fields are present**:
   - Every chunk must have a `type` field
   - Question chunks MUST have both `prompt` and `choices` (non-empty)
   - If `correct_answer_index` is provided for questions, ensure it's a valid index (0 to length-1)
6. **Validate structure**:
   - `chunks` must be an array
   - Each chunk must be an object (not a primitive value)
   - Question `choices` must be an array with at least one item
7. **Use consistent formatting** and structure

## Validation Errors
The system will catch and report these errors:
- Missing required root fields (`lesson_id`, `title`, `chunks`)
- `chunks` is not an array
- Chunk is not an object
- Question chunk missing `prompt` field
- Question chunk missing or empty `choices` array
- Question `correct_answer_index` is out of bounds (>= choices length or < 0)
- Invalid JSON syntax

If validation fails, the error message will indicate exactly what's wrong and where.

-------

Can we do the same process of json generation for the following ATTACHED DOCUMENT"""


def convert_document_to_lesson_json(file_path, file_name):
    """
    Convert a document (PDF, DOCX, TXT) to lesson JSON using GPT.
    
    Args:
        file_path: Path to the uploaded file
        file_name: Original filename
        
    Returns:
        dict: Parsed lesson JSON data
        
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
    
    schema_prompt = get_lesson_schema_prompt()
    user_prompt = f"{schema_prompt}\n\nDocument content:\n\n{extracted_text}"
    
    try:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o for better JSON generation
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that converts lesson documents into structured JSON format. Always return valid JSON that matches the schema exactly. Do not include any markdown code blocks or explanations - return ONLY the raw JSON object."
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
        lesson_data = json.loads(json_text)
        
        # Validate basic structure
        if not isinstance(lesson_data, dict):
            raise ValueError("GPT returned invalid JSON: expected an object")
        if 'lesson_id' not in lesson_data:
            raise ValueError("GPT returned JSON missing 'lesson_id' field")
        if 'title' not in lesson_data:
            raise ValueError("GPT returned JSON missing 'title' field")
        if 'chunks' not in lesson_data:
            raise ValueError("GPT returned JSON missing 'chunks' field")
        if not isinstance(lesson_data['chunks'], list):
            raise ValueError("GPT returned JSON with 'chunks' that is not an array")
        
        return lesson_data
        
    except json.JSONDecodeError as e:
        raise Exception(f"GPT returned invalid JSON: {str(e)}\n\nResponse was: {json_text[:500]}")
    except Exception as e:
        raise Exception(f"Failed to convert document to JSON using GPT: {str(e)}")

