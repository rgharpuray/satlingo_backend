"""
Utilities for converting writing section documents to JSON using GPT
"""
import json
import os
import re
from django.conf import settings
from .ingestion_utils import (
    extract_text_from_document, extract_text_from_pdf,
    extract_text_from_docx, extract_text_from_txt,
    HAS_OPENAI, HAS_PDF, HAS_DOCX
)


def get_writing_schema_prompt():
    """Get the writing section JSON schema prompt for GPT"""
    return """# Writing Section JSON Schema

This document describes the expected JSON format for writing section ingestion. Writing sections are similar to reading passages but include underlined text selections with numbers.

## Root Structure

```json
{
  "title": "string (required, section title)",
  "content": "string (required, full passage text with underlined selections marked)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "selections": [ /* array of selection objects (required) */ ],
  "questions": [ /* array of question objects (required) */ ]
}
```

## Selection Structure

Each selection represents underlined text with a number. In the document, these appear as "[1] of, famous inventor" where "famous inventor" is underlined.

```json
{
  "number": 1,  // REQUIRED - integer, the number shown (e.g., [1])
  "start_char": 150,  // REQUIRED - integer, start character position in content (0-based)
  "end_char": 168,  // REQUIRED - integer, end character position (exclusive)
  "selected_text": "famous inventor"  // REQUIRED - the actual underlined text
}
```

## Question Structure

Questions are multiple choice questions about the writing section.

```json
{
  "text": "Which choice best fits the context?",  // REQUIRED
  "choices": [  // REQUIRED - must be a non-empty array
    "NO CHANGE",
    "of, the famous inventor",
    "of the famous inventor",
    "of, famous inventor"
  ],
  "correct_answer_index": 2,  // optional, integer index (0-based) of correct answer, defaults to 0
  "selection_number": 1,  // optional, the selection number this question refers to (if any)
  "explanation": "The correct answer removes the unnecessary comma."  // optional
}
```

## Complete Example

```json
{
  "title": "Writing Practice Passage 1",
  "content": "The story of [1] of, famous inventor Thomas Edison is well known. He invented the light bulb and many other devices that changed the world.",
  "difficulty": "Medium",
  "tier": "free",
  "selections": [
    {
      "number": 1,
      "start_char": 15,
      "end_char": 33,
      "selected_text": "of, famous inventor"
    }
  ],
  "questions": [
    {
      "text": "Which choice best fits the context?",
      "choices": [
        "NO CHANGE",
        "of, the famous inventor",
        "of the famous inventor",
        "of, famous inventor"
      ],
      "correct_answer_index": 2,
      "selection_number": 1,
      "explanation": "The correct answer removes the unnecessary comma."
    }
  ]
}
```

## Important Notes

1. **Content Format**: The `content` field should contain the FULL passage text WITHOUT the [1], [2] markers. The markers are just indicators - remove them from the content. For example, if the document shows "[1] of, famous inventor", the content should include "of, famous inventor" (without the [1] marker), and the selection should point to that text.

2. **Selection Positions**: `start_char` and `end_char` are 0-based character positions in the `content` string (AFTER removing the [1], [2] markers). The `selected_text` must match EXACTLY the text at those positions in the content. 
   - Example: If content is "The son of, famous inventor, Immanuel Nobel" and "famous inventor" is underlined with [1], then:
     - `selected_text`: "famous inventor"
     - `start_char`: 11 (position of 'f' in "famous")
     - `end_char`: 28 (position after 'r' in "inventor")

3. **Finding Underlined Text**: When you see "[1] of, famous inventor" in the document:
   - The number [1] is just a marker - DO NOT include it in content
   - "of, famous inventor" or just "famous inventor" (depending on what's actually underlined) is the selected text
   - Find where this exact text appears in the full passage content
   - Calculate the character positions accurately

4. **Question-Selection Link**: If a question refers to a specific selection, use `selection_number` to link them.

5. **Required Fields**:
   - Root level: `title`, `content`, `selections`, `questions`
   - Selection: `number`, `start_char`, `end_char`, `selected_text`
   - Question: `text`, `choices`

6. **Optional Fields**:
   - Root level: `difficulty`, `tier`
   - Question: `correct_answer_index` (defaults to 0), `selection_number`, `explanation`

## Conversion Guidelines

When converting a document with underlined text and numbers:
1. Extract the full passage text and REMOVE all [1], [2], [3] markers from the content
2. Identify all underlined text with their associated numbers
3. For each underlined selection:
   - Extract the number from the marker (e.g., [1] → number: 1)
   - Find the EXACT text that is underlined (this is the selected_text)
   - Find where this exact text appears in the cleaned content (without markers)
   - Calculate start_char and end_char positions (0-based, end_char is exclusive)
   - Verify: content.substring(start_char, end_char) === selected_text
4. Extract all questions and their answer choices
5. Link questions to selections using `selection_number` if applicable

## Critical: Character Position Accuracy

The `start_char` and `end_char` values MUST be accurate. After generating the JSON:
- Verify that content[start_char:end_char] exactly matches selected_text
- Count characters carefully - spaces, punctuation, and all characters count
- The positions are 0-based (first character is at position 0)
- end_char is exclusive (points to the character AFTER the selection)

-------

Can we do the same process of json generation for the following ATTACHED DOCUMENT"""


def convert_document_to_writing_json(file_path, file_name):
    """
    Convert a document (PDF, DOCX, TXT) to writing section JSON using GPT.
    
    Args:
        file_path: Path to the uploaded file
        file_name: Original filename
        
    Returns:
        dict: Parsed writing section JSON data
        
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
    
    schema_prompt = get_writing_schema_prompt()
    user_prompt = f"{schema_prompt}\n\nDocument content:\n\n{extracted_text}"
    
    try:
        response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that converts writing section documents into structured JSON format. 

CRITICAL INSTRUCTIONS:
1. The document contains passages with underlined text marked with numbers like [1], [2], [3]
2. Remove ALL [1], [2], [3] markers from the content field - they are just indicators, not part of the text
3. For each selection, find the EXACT underlined text in the cleaned content (without the markers)
4. Calculate start_char and end_char positions accurately (0-based, end_char is exclusive)
5. Verify: content[start_char:end_char] must exactly equal selected_text
6. Always return valid JSON that matches the schema exactly
7. Do not include any markdown code blocks or explanations - return ONLY the raw JSON object"""
                    },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    
    # Extract JSON from response
    json_text = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    elif json_text.startswith("```"):
        json_text = json_text[3:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()
    
    # Parse JSON
    try:
        writing_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise Exception(f"GPT returned invalid JSON: {str(e)}\n\nResponse was: {json_text[:500]}")
    
    # Validate basic structure
    if not isinstance(writing_data, dict):
        raise ValueError("GPT returned invalid JSON: expected an object")
    if 'title' not in writing_data:
        raise ValueError("GPT returned JSON missing 'title' field")
    if 'content' not in writing_data:
        raise ValueError("GPT returned JSON missing 'content' field")
    if 'selections' not in writing_data:
        raise ValueError("GPT returned JSON missing 'selections' field")
    if 'questions' not in writing_data:
        raise ValueError("GPT returned JSON missing 'questions' field")
    if not isinstance(writing_data['selections'], list):
        raise ValueError("GPT returned JSON with 'selections' that is not an array")
    if not isinstance(writing_data['questions'], list):
        raise ValueError("GPT returned JSON with 'questions' that is not an array")
    
    # Post-process: Fix common issues with selections
    content = writing_data['content']
    
    # Remove any remaining [1], [2], etc. markers from content if GPT missed them
    import re
    content_cleaned = re.sub(r'\[\d+\]\s*', '', content)
    if content_cleaned != content:
        # Content had markers - update it and fix selection positions
        writing_data['content'] = content_cleaned
        content = content_cleaned
        
        # Recalculate positions for all selections
        for sel in writing_data['selections']:
            selected_text = sel.get('selected_text', '')
            if selected_text:
                # Find the selected text in the cleaned content
                pos = content.find(selected_text)
                if pos != -1:
                    sel['start_char'] = pos
                    sel['end_char'] = pos + len(selected_text)
                else:
                    # Try to find a close match (case-insensitive, whitespace-tolerant)
                    selected_lower = selected_text.lower().strip()
                    content_lower = content.lower()
                    pos = content_lower.find(selected_lower)
                    if pos != -1:
                        # Found a match - use the actual text from content
                        actual_text = content[pos:pos + len(selected_text)]
                        sel['selected_text'] = actual_text
                        sel['start_char'] = pos
                        sel['end_char'] = pos + len(actual_text)
    
    # Validate and fix selection positions - be more aggressive about fixing
    for sel in writing_data['selections']:
        selected_text = sel.get('selected_text', '').strip()
        start_char = sel.get('start_char')
        end_char = sel.get('end_char')
        number = sel.get('number')
        
        # Skip obviously wrong selected_text (like "paragraph 3" which is metadata, not actual text)
        if selected_text and len(selected_text) < 3:
            # Too short, probably wrong
            selected_text = ''
        if selected_text and ('paragraph' in selected_text.lower() or 'section' in selected_text.lower()):
            # Looks like metadata, not actual text
            selected_text = ''
        
        if selected_text and start_char is not None and end_char is not None:
            # Verify the positions match
            if start_char >= 0 and end_char <= len(content) and start_char < end_char:
                actual_text = content[start_char:end_char]
                if actual_text != selected_text:
                    # Try to find the correct position - search more broadly
                    search_start = max(0, start_char - 200)
                    search_end = min(len(content), start_char + 200)
                    search_area = content[search_start:search_end]
                    
                    pos = search_area.find(selected_text)
                    if pos != -1:
                        sel['start_char'] = search_start + pos
                        sel['end_char'] = search_start + pos + len(selected_text)
                    else:
                        # Try case-insensitive search in broader area
                        selected_lower = selected_text.lower().strip()
                        content_lower = content.lower()
                        search_area_lower = content_lower[search_start:search_end]
                        pos = search_area_lower.find(selected_lower)
                        if pos != -1:
                            # Use the actual text from content at this position
                            actual_pos = search_start + pos
                            actual_text = content[actual_pos:actual_pos + len(selected_text)]
                            sel['selected_text'] = actual_text
                            sel['start_char'] = actual_pos
                            sel['end_char'] = actual_pos + len(actual_text)
                        else:
                            # Last resort: search entire content
                            pos = content_lower.find(selected_lower)
                            if pos != -1:
                                actual_text = content[pos:pos + len(selected_text)]
                                sel['selected_text'] = actual_text
                                sel['start_char'] = pos
                                sel['end_char'] = pos + len(actual_text)
                            else:
                                # Can't find it - remove this selection or use position-based text
                                if start_char < len(content) and end_char <= len(content):
                                    # Use whatever text is at the position GPT gave us
                                    actual_text_at_pos = content[start_char:end_char].strip()
                                    if len(actual_text_at_pos) > 0:
                                        sel['selected_text'] = actual_text_at_pos
                                    else:
                                        # Invalid selection - mark for removal
                                        sel['_invalid'] = True
                                else:
                                    sel['_invalid'] = True
        
        # If we still don't have valid selected_text, try to infer from context
        if not sel.get('selected_text') or sel.get('selected_text', '').strip() == '':
            if start_char is not None and end_char is not None and start_char < len(content) and end_char <= len(content):
                # Use text at the given position
                inferred_text = content[start_char:end_char].strip()
                if len(inferred_text) > 0:
                    sel['selected_text'] = inferred_text
                else:
                    sel['_invalid'] = True
            else:
                sel['_invalid'] = True
    
    # Remove invalid selections
    writing_data['selections'] = [sel for sel in writing_data['selections'] if not sel.get('_invalid', False)]
    
    # Validate questions exist and are not empty
    if not writing_data.get('questions') or len(writing_data['questions']) == 0:
        # GPT didn't generate questions - that's okay, we'll just have an empty list
        writing_data['questions'] = []
    
    return writing_data

