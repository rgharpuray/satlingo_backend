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


def extract_text_from_image(image_path):
    """Extract text from an image using OCR"""
    if not HAS_OCR:
        raise Exception("OCR libraries not installed. Install Pillow and pytesseract.")
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from image: {str(e)}")


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


def parse_passage_with_ai(extracted_text):
    """Use AI to parse extracted text into structured passage with questions"""
    if not HAS_OPENAI:
        raise Exception("OpenAI library not installed. Install openai package.")
    
    api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        raise Exception("OpenAI API key not configured")
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Extract a reading passage with questions from the following text. Return a JSON object with this exact structure:

{{
  "title": "Title of the passage",
  "content": "Full passage text",
  "difficulty": "Easy" or "Medium" or "Hard",
  "questions": [
    {{
      "text": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 0,
      "explanation": "Explanation of the correct answer",
      "order": 1
    }}
  ]
}}

Text to parse:
{extracted_text}

Return ONLY valid JSON, no markdown, no code blocks, no additional text."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at parsing SAT reading comprehension passages and questions. Extract structured data from text."},
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
        for q in parsed_data['questions']:
            if not all(field in q for field in ['text', 'options', 'correct_answer_index', 'order']):
                raise Exception("Question missing required fields")
            if not isinstance(q['options'], list) or len(q['options']) < 2:
                raise Exception("Question must have at least 2 options")
            if q['correct_answer_index'] < 0 or q['correct_answer_index'] >= len(q['options']):
                raise Exception("Invalid correct_answer_index")
        
        return parsed_data
    
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"AI parsing failed: {str(e)}")


def create_passage_from_parsed_data(parsed_data):
    """Create Passage, Questions, and Options from parsed data"""
    from .models import Passage, Question, QuestionOption
    
    # Create passage
    passage = Passage.objects.create(
        title=parsed_data['title'],
        content=parsed_data['content'],
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

