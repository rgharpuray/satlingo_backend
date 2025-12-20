"""
Utilities for ingesting passages from images, PDFs, and Google Drive files
"""
import os
import json
from django.conf import settings

# Optional imports - handle gracefully if not installed
try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

try:
    from pdf2image import convert_from_path
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def extract_text_from_image(image_path):
    """Extract text from an image using OCR - preserves line breaks and paragraph structure"""
    if not HAS_OCR:
        raise Exception("OCR libraries not installed. Install Pillow and pytesseract.")
    try:
        image = Image.open(image_path)
        # Use pytesseract config to preserve structure
        # psm 6 = Assume a single uniform block of text (better for paragraphs)
        # psm 11 = Sparse text (better for questions with options)
        # Try psm 6 first for better paragraph detection
        text = pytesseract.image_to_string(image, config='--psm 6')
        # Clean up but preserve paragraph breaks (double newlines)
        # Remove excessive whitespace but keep meaningful line breaks
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)
                prev_empty = False
            else:
                # Only add empty line if previous line wasn't empty (preserve paragraph breaks)
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
        return '\n'.join(cleaned_lines).strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from image: {str(e)}")


def extract_text_from_multiple_images(image_paths):
    """Extract and combine text from multiple images (screenshots of the same document)"""
    if not HAS_OCR:
        raise Exception("OCR libraries not installed. Install Pillow and pytesseract.")
    
    text_parts = []
    for image_path in image_paths:
        try:
            text = extract_text_from_image(image_path)
            if text:
                text_parts.append(text)
        except Exception as e:
            # Log error but continue with other images
            print(f"Warning: Failed to extract text from {image_path}: {str(e)}")
    
    if not text_parts:
        raise Exception("Failed to extract text from any images")
    
    # Combine text parts with separator
    # The AI will handle deduplication of overlapping content
    return "\n\n---SCREENSHOT BREAK---\n\n".join(text_parts)


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file"""
    if not HAS_PDF or not HAS_OCR:
        raise Exception("PDF processing libraries not installed. Install pdf2image, Pillow, and pytesseract.")
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        text_parts = []
        
        for image in images:
            text = pytesseract.image_to_string(image)
            text_parts.append(text.strip())
        
        return "\n\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_docx(docx_path):
    """Extract text from a .docx or .doc file"""
    if not HAS_DOCX:
        raise Exception("python-docx library not installed. Install python-docx package.")
    try:
        # Check if it's actually a .doc file (older format)
        if docx_path.lower().endswith('.doc') and not docx_path.lower().endswith('.docx'):
            # .doc files are not supported by python-docx
            # Suggest converting to .docx or using OCR
            raise Exception("Legacy .doc files are not directly supported. Please convert to .docx format or use a screenshot/PDF instead.")
        
        doc = Document(docx_path)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:  # Only add non-empty paragraphs
                paragraphs.append(text)
        return "\n\n".join(paragraphs)
    except Exception as e:
        raise Exception(f"Failed to extract text from document: {str(e)}")


def extract_text_from_txt(txt_path):
    """Extract text from a .txt file"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        # If all encodings fail, try with error handling
        with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Failed to extract text from TXT: {str(e)}")


def extract_text_from_document(file_path, file_type):
    """Extract text from a document file based on file type"""
    if file_type == 'docx':
        return extract_text_from_docx(file_path)
    elif file_type == 'txt':
        return extract_text_from_txt(file_path)
    elif file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'image':
        return extract_text_from_image(file_path)
    else:
        raise Exception(f"Unsupported file type for direct text extraction: {file_type}")


def parse_passage_with_ai(extracted_text, is_multiple_screenshots=False):
    """Use AI to parse extracted text into structured passage with questions
    
    Args:
        extracted_text: Text extracted from OCR
        is_multiple_screenshots: If True, indicates text comes from multiple screenshots of the same document
    """
    if not HAS_OPENAI:
        raise Exception("OpenAI library not installed. Install openai package.")
    
    api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        raise Exception("OpenAI API key not configured")
    
    try:
        client = OpenAI(api_key=api_key)
        
        context_note = ""
        if is_multiple_screenshots:
            # Check if text contains document breaks (from actual documents) or screenshot breaks
            if "---DOCUMENT BREAK---" in extracted_text:
                context_note = """
IMPORTANT: The text below comes from multiple document files (Word docs, text files, etc.) of the same passage. 
- Documents may have overlapping content - deduplicate and combine intelligently
- The passage and questions may be split across different files
- Infer the complete passage and all questions from the combined documents
- Text between "---DOCUMENT BREAK---" markers indicates different files
- Combine overlapping sections and reconstruct the full document structure

"""
            else:
                context_note = """
IMPORTANT: The text below comes from multiple screenshots of the same Google Doc/document. 
- Screenshots may have overlapping content - deduplicate and combine intelligently
- The passage and questions may be split across different screenshots
- Infer the complete passage and all questions from the combined screenshots
- Text between "---SCREENSHOT BREAK---" markers indicates different screenshots
- Combine overlapping sections and reconstruct the full document structure

"""
        
        prompt = f"""{context_note}Extract a reading passage with questions from the following text. Return a JSON object with this exact structure:

{{
  "title": "Title of the passage",
  "content": "Full passage text (complete, deduplicated if from multiple screenshots). PRESERVE ALL PARAGRAPH BREAKS - use \\n\\n to separate paragraphs.",
  "difficulty": "Easy" or "Medium" or "Hard",
  "questions": [
    {{
      "text": "Question text",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_answer_index": 0,
      "explanation": "Explanation of the correct answer",
      "order": 1
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
1. PRESERVE PARAGRAPH BREAKS: In the "content" field, use \\n\\n (double newline) to separate paragraphs. Do NOT remove line breaks or merge paragraphs.
2. ANSWER CHOICES: Each question MUST have exactly 4 options (A, B, C, D). Extract the full text of each option, including any letter prefix (A., B., etc.) if present, but store only the option text without the letter prefix in the options array.
3. CORRECT ANSWER: The correct_answer_index should be 0 for option A, 1 for option B, 2 for option C, 3 for option D.
4. QUESTION ORDER: Number questions in order starting from 1.

Text to parse:
{extracted_text}

Return ONLY valid JSON, no markdown, no code blocks, no additional text."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at parsing SAT reading comprehension passages and questions. Extract structured data from text. CRITICALLY IMPORTANT: Preserve all paragraph breaks in passage content using \\n\\n, and ensure each question has exactly 4 answer options (A, B, C, D) with correct_answer_index matching the option position (0=A, 1=B, 2=C, 3=D)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        
        # Parse JSON
        parsed_data = json.loads(content)
        
        # Validate structure
        required_fields = ['title', 'content', 'difficulty', 'questions']
        if not all(field in parsed_data for field in required_fields):
            raise Exception("AI response missing required fields")
        
        # Validate questions
        if not isinstance(parsed_data['questions'], list) or len(parsed_data['questions']) == 0:
            raise Exception("No questions found in parsed data")
        
        # Validate each question
        for idx, q in enumerate(parsed_data['questions']):
            if not all(field in q for field in ['text', 'options', 'correct_answer_index', 'order']):
                raise Exception(f"Question {idx + 1} missing required fields")
            if not isinstance(q['options'], list):
                raise Exception(f"Question {idx + 1} options must be a list")
            if len(q['options']) != 4:
                raise Exception(f"Question {idx + 1} must have exactly 4 options (A, B, C, D), found {len(q['options'])}")
            if q['correct_answer_index'] < 0 or q['correct_answer_index'] >= len(q['options']):
                raise Exception(f"Question {idx + 1} has invalid correct_answer_index: {q['correct_answer_index']} (must be 0-3)")
            # Ensure options are non-empty strings
            for opt_idx, option in enumerate(q['options']):
                if not isinstance(option, str) or not option.strip():
                    raise Exception(f"Question {idx + 1}, Option {opt_idx + 1} is empty or invalid")
        
        return parsed_data
    
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"AI parsing failed: {str(e)}")


def create_passage_from_parsed_data(parsed_data):
    """Create Passage, Questions, and Options from parsed data"""
    from .models import Passage, Question, QuestionOption
    
    # Normalize content: convert literal \n strings to actual newlines
    content = parsed_data['content']
    if isinstance(content, str):
        # Handle cases where AI might return literal \n strings
        # First handle double backslash (\\n -> \n)
        content = content.replace('\\\\n', '\n')
        # Then handle single backslash (\n -> newline)
        content = content.replace('\\n', '\n')
    
    # Create passage
    passage = Passage.objects.create(
        title=parsed_data['title'],
        content=content,
        difficulty=parsed_data.get('difficulty', 'Medium')
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
        for idx, option_text in enumerate(q_data['options']):
            QuestionOption.objects.create(
                question=question,
                text=option_text,
                order=idx
            )
    
    return passage


def process_ingestion(ingestion):
    """Process an ingestion: extract text, parse with AI, create passage - ensures only ONE passage per ingestion"""
    # Prevent duplicate processing
    ingestion.refresh_from_db()
    if ingestion.status == 'processing':
        # Check if it's been processing too long (might be stuck)
        # If error_message contains progress, it's actively processing
        if not ingestion.error_message or 'Step' not in ingestion.error_message:
            # Might be stuck, allow reprocessing
            pass
        else:
            # Already processing, skip
            return
    if ingestion.status == 'completed' and ingestion.created_passage:
        # Already completed with a passage, skip to prevent duplicates
        return
    
    ingestion.status = 'processing'
    ingestion.error_message = 'Step 1/4: Starting processing...'
    ingestion.save()
    
    try:
        # Check if we have multiple files (screenshots of the same document)
        file_paths = ingestion.file_paths if hasattr(ingestion, 'file_paths') and ingestion.file_paths else []
        is_multiple_screenshots = len(file_paths) > 1
        
        # Step 2: Extract text from file(s)
        ingestion.error_message = f'Step 2/4: Extracting text from {ingestion.file_type} file(s)...'
        ingestion.save()
        
        if ingestion.file_type == 'image':
            if is_multiple_screenshots:
                # Multiple screenshots - combine them
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} images...'
                ingestion.save()
                extracted_text = extract_text_from_multiple_images(file_paths)
            else:
                # Single image
                extracted_text = extract_text_from_image(ingestion.file_path)
        elif ingestion.file_type == 'pdf':
            extracted_text = extract_text_from_pdf(ingestion.file_path)
        elif ingestion.file_type == 'docx':
            # For documents, if multiple files, combine them
            if is_multiple_screenshots:
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} document files...'
                ingestion.save()
                text_parts = []
                for idx, file_path in enumerate(file_paths, 1):
                    ingestion.error_message = f'Step 2/4: Processing document {idx}/{len(file_paths)}...'
                    ingestion.save()
                    text = extract_text_from_docx(file_path)
                    if text:
                        text_parts.append(text)
                extracted_text = "\n\n---DOCUMENT BREAK---\n\n".join(text_parts)
            else:
                extracted_text = extract_text_from_docx(ingestion.file_path)
        elif ingestion.file_type == 'txt':
            # For text files, if multiple files, combine them
            if is_multiple_screenshots:
                ingestion.error_message = f'Step 2/4: Extracting text from {len(file_paths)} text files...'
                ingestion.save()
                text_parts = []
                for idx, file_path in enumerate(file_paths, 1):
                    ingestion.error_message = f'Step 2/4: Processing text file {idx}/{len(file_paths)}...'
                    ingestion.save()
                    text = extract_text_from_txt(file_path)
                    if text:
                        text_parts.append(text)
                extracted_text = "\n\n---DOCUMENT BREAK---\n\n".join(text_parts)
            else:
                extracted_text = extract_text_from_txt(ingestion.file_path)
        else:
            raise Exception(f"Unsupported file type: {ingestion.file_type}")
        
        ingestion.extracted_text = extracted_text
        ingestion.error_message = f'Step 2/4: Text extraction complete. Extracted {len(extracted_text)} characters.'
        ingestion.save()
        
        # Step 3: Parse with AI - pass context about multiple screenshots
        ingestion.error_message = 'Step 3/4: Parsing text with AI to extract passage and questions...'
        ingestion.save()
        parsed_data = parse_passage_with_ai(extracted_text, is_multiple_screenshots=is_multiple_screenshots)
        
        ingestion.error_message = f'Step 3/4: AI parsing complete. Found {len(parsed_data.get("questions", []))} questions.'
        ingestion.save()
        
        # Step 4: Create passage
        ingestion.error_message = 'Step 4/4: Creating passage and questions in database...'
        ingestion.save()
        
        # Ensure only ONE passage is created per ingestion
        # If a passage already exists, don't create another
        if not ingestion.created_passage:
            # Create passage - this function creates exactly ONE passage
            passage = create_passage_from_parsed_data(parsed_data)
            ingestion.created_passage = passage
        
        ingestion.status = 'completed'
        ingestion.error_message = f'✓ Successfully created passage "{parsed_data.get("title", "Untitled")}" with {len(parsed_data.get("questions", []))} questions.'
        ingestion.save()
        
    except Exception as e:
        ingestion.status = 'failed'
        ingestion.error_message = f'✗ Error at {ingestion.error_message if "Step" in str(ingestion.error_message) else "processing"}: {str(e)}'
        ingestion.save()
        raise

