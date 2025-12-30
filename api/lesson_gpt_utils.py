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

# Check for boto3 (AWS SDK for S3)
try:
    import boto3
    from botocore.exceptions import ClientError
    from boto3.exceptions import S3UploadFailedError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    S3UploadFailedError = None


def upload_lesson_asset_to_s3(image_path, asset_id, lesson_id):
    """
    Upload an image file to S3 for a lesson asset.
    
    Args:
        image_path: Local path to the image file
        asset_id: Unique identifier for the asset (e.g., 'diagram-1')
        lesson_id: ID of the lesson (e.g., 'proportions')
        
    Returns:
        str: Public S3 URL
        
    Raises:
        Exception: If upload fails or S3 is not configured
    """
    if not HAS_BOTO3:
        raise Exception("boto3 not installed. Install boto3 for S3 uploads: pip install boto3")
    
    # Get S3 configuration from settings
    aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    aws_storage_bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    aws_s3_region_name = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
    
    if not all([aws_access_key_id, aws_secret_access_key, aws_storage_bucket_name]):
        raise Exception("S3 not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_STORAGE_BUCKET_NAME in settings.")
    
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_s3_region_name
    )
    
    # Determine file extension
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in ['.png', '.jpg', '.jpeg', '.svg', '.gif']:
        file_ext = '.png'  # Default to PNG
    
    # Create S3 key (path in bucket) - use lessons/ prefix
    s3_key = f"lessons/{lesson_id}/{asset_id}{file_ext}"
    
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise Exception(f"Image file does not exist: {image_path}")
        
        # Try uploading with ACL first (for buckets with ACL enabled)
        try:
            s3_client.upload_file(
                image_path,
                aws_storage_bucket_name,
                s3_key,
                ExtraArgs={'ACL': 'public-read'}  # Make file publicly readable
            )
        except (ClientError, S3UploadFailedError) as acl_error:
            # If ACL fails (bucket might have ACLs disabled), try without ACL
            # The bucket policy should make it public instead
            if isinstance(acl_error, ClientError):
                error_code = acl_error.response.get('Error', {}).get('Code', '')
                error_message = acl_error.response.get('Error', {}).get('Message', '')
            else:
                # S3UploadFailedError wraps the original error
                error_code = 'AccessControlListNotSupported' if 'ACL' in str(acl_error) else 'Unknown'
                error_message = str(acl_error)
            
            if 'AccessControlListNotSupported' in error_code or 'ACL' in error_message:
                # Upload without ACL - rely on bucket policy for public access
                s3_client.upload_file(
                    image_path,
                    aws_storage_bucket_name,
                    s3_key
                )
            else:
                # Re-raise if it's a different error
                raise
        
        # Construct public URL
        if aws_s3_region_name == 'us-east-1':
            s3_url = f"https://{aws_storage_bucket_name}.s3.amazonaws.com/{s3_key}"
        else:
            s3_url = f"https://{aws_storage_bucket_name}.s3.{aws_s3_region_name}.amazonaws.com/{s3_key}"
        
        return s3_url
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise Exception(f"Failed to upload image to S3 (Error: {error_code}): {error_message}")
    except Exception as e:
        raise Exception(f"Failed to upload image to S3: {str(e)}")


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
  "shared_assets": [ /* optional array of asset objects for diagrams/images (for math lessons) */ ],
  "chunks": [ /* array of chunk objects (required) */ ]
}
```

## Shared Assets (Optional - for math lessons with diagrams)
If the lesson contains diagrams or images, include them in the `shared_assets` array:
```json
{
  "shared_assets": [
    {
      "asset_id": "diagram-1",
      "type": "image",
      "s3_url": "https://s3.amazonaws.com/bucket/diagram-1.png"
    }
  ]
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
  "correct_answer_index": 2,  // optional, integer index (0-based) of correct answer, defaults to 0 if not provided. If provided, must be >= 0 and < length of choices array
  "assets": ["diagram-1"]  // optional, array of asset_id strings from shared_assets (for math questions with diagrams)
}
```
**Important:** 
- `prompt` is **REQUIRED** - the question will fail validation if missing
- `choices` is **REQUIRED** - must be a non-empty array, or validation will fail
- `correct_answer_index` is optional. If not provided, defaults to 0 (first choice). If provided, must be a valid index (0-based) within the choices array, otherwise validation will fail.
- `assets` is optional. If the question references a diagram/image from `shared_assets`, include the `asset_id` in this array.

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

### 14. Page Break
Creates a page break for pagination. When the document contains "NEW PAGE" markers, insert a page_break chunk at that location. The frontend will split the lesson into separate pages at these points.
```json
{
  "type": "page_break"
}
```
**Important:**
- If you encounter "NEW PAGE", "---NEW PAGE---", "NEW PAGE---", or similar page break markers in the document, create a `page_break` chunk at that location.
- Page breaks should be inserted as separate chunks, not as part of other chunk types.
- The first page starts automatically, so you don't need a page_break at the very beginning.

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
    
    # Extract diagrams from document (for math lessons)
    from .math_gpt_utils import extract_diagrams_from_document, upload_image_to_s3
    diagrams = extract_diagrams_from_document(file_path, file_name)
    
    # Upload diagrams to S3 and create a mapping of asset_id to S3 URL
    diagram_s3_map = {}  # Maps asset_id to S3 URL
    temp_dir = None
    
    # Create a temporary lesson_id for organizing uploads
    # Sanitize: remove colons, special chars, and limit length
    temp_lesson_id = os.path.splitext(file_name)[0].replace(' ', '-').replace(':', '-').replace('/', '-').replace('\\', '-').lower()[:50]
    
    if diagrams:
        import shutil
        aws_storage_bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        
        for diagram in diagrams:
            try:
                # Upload to S3 (using lesson path instead of math-section path)
                s3_url = upload_image_to_s3(
                    diagram['image_path'],
                    diagram['asset_id'],
                    f"lessons/{temp_lesson_id}"  # Use lessons/ prefix for lessons
                )
                diagram_s3_map[diagram['asset_id']] = s3_url
                print(f"✓ Uploaded diagram {diagram['asset_id']} to S3: {s3_url}")
            except Exception as e:
                error_msg = f"✗ Failed to upload diagram {diagram['asset_id']} to S3: {str(e)}"
                print(error_msg)
                # Log the error but continue with other diagrams
                # We'll still include the diagram in the JSON but with a placeholder URL
                diagram_s3_map[diagram['asset_id']] = f"https://s3.amazonaws.com/{aws_storage_bucket_name}/lessons/{temp_lesson_id}/{diagram['asset_id']}.png"
                continue
        
        # Store temp_dir for cleanup later
        if diagrams and len(diagrams) > 0:
            temp_dir = os.path.dirname(diagrams[0]['image_path'])
    
    # Call GPT to convert to JSON
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    schema_prompt = get_lesson_schema_prompt()
    
    # Add diagram instructions if we extracted diagrams
    diagram_instructions = ""
    if diagrams and len(diagrams) > 0:
        asset_ids = [d['asset_id'] for d in diagrams]
        diagram_instructions = f"""
    
## CRITICAL: Diagram Handling Instructions

The backend has extracted {len(diagrams)} diagram(s) from the document. You MUST use these exact asset_ids.

EXTRACTED DIAGRAMS:
"""
        for idx, diagram in enumerate(diagrams, 1):
            s3_url = diagram_s3_map.get(diagram['asset_id'], f"https://s3.amazonaws.com/bucket/lessons/{temp_lesson_id}/{diagram['asset_id']}.png")
            page_info = f" (Page {diagram['page_num']})" if diagram.get('page_num') else ""
            diagram_instructions += f"{idx}. asset_id: \"{diagram['asset_id']}\"{page_info}\n   s3_url: \"{s3_url}\"\n"
        
        diagram_instructions += f"""

MANDATORY REQUIREMENTS:
1. You MUST include ALL {len(diagrams)} diagram(s) in the shared_assets array using the EXACT asset_ids listed above
2. Use the EXACT s3_url values provided above for each asset_id
3. **CRITICAL: Match diagrams to questions intelligently** - For each question chunk, analyze which diagram(s) belong to it:
   - Read the question text carefully - does it reference a diagram, figure, graph, or visual element?
   - Check the document context - which diagram appears near or with this question?
   - Consider the question content - does it ask about something shown in a diagram?
   - Look at the order - diagrams are extracted in document order, questions appear in document order
   - **Match by proximity**: If a diagram appears right before or after a question in the document, they likely belong together
   - **Match by content**: If a question asks "What is shown in the diagram?" or references visual elements, include the nearest diagram
   - **Match by context**: If multiple questions share a diagram, include that asset_id in all relevant question chunks
4. For each question chunk that needs a diagram, include the asset_id(s) in the question chunk's "assets" array
5. **Be precise**: Only include asset_ids for diagrams that actually relate to that specific question

IMPORTANT: 
- DO NOT create new asset_ids - only use the ones listed above: {', '.join(asset_ids)}
- DO NOT use placeholder URLs - use the actual s3_url values provided
- DO NOT guess randomly - analyze the document content to match diagrams to questions correctly
- Every question that clearly references or needs a diagram MUST have an "assets" array with the appropriate asset_id(s)
- If a diagram doesn't clearly belong to any question, you can still include it in shared_assets but don't link it to questions

Example structure:
```json
{{
  "shared_assets": [
    {{
      "asset_id": "{diagrams[0]['asset_id'] if diagrams else 'diagram-1'}",
      "type": "image",
      "s3_url": "{diagram_s3_map.get(diagrams[0]['asset_id'], '') if diagrams else ''}"
    }}
  ],
  "chunks": [
    {{
      "type": "question",
      "prompt": "What is shown in the diagram?",
      "assets": ["{diagrams[0]['asset_id'] if diagrams else 'diagram-1'}"],
      "choices": ["Option A", "Option B", "Option C", "Option D"],
      ...
    }}
  ]
}}
```
"""
    
    # Add page break instructions
    page_break_instructions = """
## Page Break Handling
If the document contains "NEW PAGE" markers (or variations like "---NEW PAGE---", "NEW PAGE---", "---NEW PAGE", etc.), you MUST create a `page_break` chunk at that location. This will split the lesson into separate pages in the frontend with Previous/Next navigation.

Example: If you see "---NEW PAGE---" in the document, insert:
```json
{"type": "page_break"}
```
at that location in the chunks array.

The first page starts automatically, so you don't need a page_break at the very beginning of the document.
"""
    
    user_prompt = f"{schema_prompt}{diagram_instructions}{page_break_instructions}\n\nDocument content:\n\n{extracted_text}"
    
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
        
        # Validate and update shared_assets if we extracted diagrams
        if diagrams and len(diagrams) > 0:
            # Ensure shared_assets array exists
            if 'shared_assets' not in lesson_data:
                lesson_data['shared_assets'] = []
            elif not isinstance(lesson_data['shared_assets'], list):
                lesson_data['shared_assets'] = []
            
            # Get all extracted asset_ids
            extracted_asset_ids = {d['asset_id'] for d in diagrams}
            
            # Get asset_ids that GPT included
            gpt_asset_ids = {asset.get('asset_id') for asset in lesson_data['shared_assets'] if asset.get('asset_id')}
            
            # Check if all extracted diagrams are included
            missing_assets = extracted_asset_ids - gpt_asset_ids
            if missing_assets:
                # Add missing assets automatically
                for diagram in diagrams:
                    if diagram['asset_id'] in missing_assets:
                        s3_url = diagram_s3_map.get(diagram['asset_id'])
                        if s3_url:
                            lesson_data['shared_assets'].append({
                                'asset_id': diagram['asset_id'],
                                'type': 'image',
                                's3_url': s3_url
                            })
                            print(f"Warning: GPT did not include extracted diagram '{diagram['asset_id']}', adding it automatically")
            
            # Update all assets with actual S3 URLs
            for asset in lesson_data['shared_assets']:
                asset_id = asset.get('asset_id')
                if asset_id in diagram_s3_map:
                    asset['s3_url'] = diagram_s3_map[asset_id]
        
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
        
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

