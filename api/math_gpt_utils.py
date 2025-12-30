"""
Utilities for converting math section documents to JSON using GPT
Includes S3 upload for diagrams
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

# Check for boto3 (AWS SDK for S3)
try:
    import boto3
    from botocore.exceptions import ClientError
    from boto3.exceptions import S3UploadFailedError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    S3UploadFailedError = None


def get_math_schema_prompt():
    """Get the math section JSON schema prompt for GPT"""
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'MATH_SECTION_JSON_SCHEMA.md')
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to inline schema if file not found
        return """# Math Section JSON Schema

This document describes the expected JSON format for math section ingestion.

## Root Structure
```json
{
  "section_id": "string (required, unique identifier)",
  "title": "string (required, section title)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "shared_assets": [ /* array of asset objects (optional) */ ],
  "questions": [ /* array of question objects (required) */ ]
}
```

## Asset Structure
```json
{
  "asset_id": "diagram-1",
  "type": "image",
  "s3_url": "https://s3.amazonaws.com/bucket/path/to/diagram.png"
}
```

## Question Structure
```json
{
  "question_id": "q1",
  "prompt": "What is the value of x?",
  "choices": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer_index": 1,
  "assets": ["diagram-1"],
  "explanation": [
    {"type": "paragraph", "text": "Explanation text"},
    {"type": "equation", "latex": "x = 5"}
  ]
}
```

For full schema details, see MATH_SECTION_JSON_SCHEMA.md"""


def upload_image_to_s3(image_path, asset_id, math_section_id):
    """
    Upload an image file to S3.
    
    Args:
        image_path: Local path to the image file
        asset_id: Unique identifier for the asset
        math_section_id: ID of the math section (for organizing in S3)
        
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
    
    # Create S3 key (path in bucket)
    # Use lessons/ prefix directly (same as lesson assets) to work with bucket policy
    # Support both math-sections and lessons paths for backwards compatibility
    if math_section_id.startswith('lessons/'):
        s3_key = f"{math_section_id}/{asset_id}{file_ext}"
    else:
        # Use lessons/ prefix directly (not lessons/math-sections/) to match bucket policy
        # This ensures it works the same way as lesson assets
        s3_key = f"lessons/{math_section_id}/{asset_id}{file_ext}"
    
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
            print(f"Uploaded {s3_key} with ACL")
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
            
            print(f"ACL upload failed ({error_code}): {error_message}")
            
            if 'AccessControlListNotSupported' in error_code or 'ACL' in error_message:
                # Upload without ACL - rely on bucket policy for public access
                print(f"Retrying upload without ACL...")
                s3_client.upload_file(
                    image_path,
                    aws_storage_bucket_name,
                    s3_key
                )
                print(f"Note: Uploaded {s3_key} without ACL (bucket ACLs disabled, using bucket policy)")
            else:
                # Re-raise if it's a different error
                raise
        
        # Construct public URL - URL encode the key to handle special characters like #
        from urllib.parse import quote
        encoded_key = quote(s3_key, safe='/')
        if aws_s3_region_name == 'us-east-1':
            s3_url = f"https://{aws_storage_bucket_name}.s3.amazonaws.com/{encoded_key}"
        else:
            s3_url = f"https://{aws_storage_bucket_name}.s3.{aws_s3_region_name}.amazonaws.com/{encoded_key}"
        
        print(f"Successfully uploaded {s3_key} to S3: {s3_url}")
        return s3_url
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise Exception(f"Failed to upload image to S3 (Error: {error_code}): {error_message}")
    except Exception as e:
        raise Exception(f"Failed to upload image to S3: {str(e)}")


def extract_diagrams_from_document(file_path, file_name):
    """
    Extract diagrams/images from a document.
    
    Args:
        file_path: Path to the document
        file_name: Original filename
        
    Returns:
        list: List of dicts with {'asset_id': str, 'image_path': str, 'page_num': int (for PDFs)}
    """
    import tempfile
    import shutil
    
    file_ext = os.path.splitext(file_name)[1].lower()
    extracted_images = []
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        if file_ext == '.pdf':
            # Use PyMuPDF (fitz) to extract images from PDF
            try:
                import fitz  # PyMuPDF
            except ImportError:
                # Fallback to pdf2image if PyMuPDF not available
                try:
                    from pdf2image import convert_from_path
                    from PIL import Image
                    
                    # Convert PDF pages to images
                    images = convert_from_path(file_path)
                    for page_num, image in enumerate(images, start=1):
                        image_path = os.path.join(temp_dir, f"page_{page_num}.png")
                        image.save(image_path, 'PNG')
                        extracted_images.append({
                            'asset_id': f'diagram-page-{page_num}',
                            'image_path': image_path,
                            'page_num': page_num
                        })
                    return extracted_images
                except ImportError:
                    raise Exception("Neither PyMuPDF nor pdf2image available. Install one: pip install PyMuPDF or pip install pdf2image")
            
            # Use PyMuPDF (fitz) for better image extraction
            doc = fitz.open(file_path)
            image_count = 0
            print(f"📄 Processing PDF with {len(doc)} page(s)...")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                print(f"  Page {page_num + 1}: Found {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Save image to temp file
                        image_path = os.path.join(temp_dir, f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}")
                        with open(image_path, "wb") as img_file:
                            img_file.write(image_bytes)
                        
                        extracted_images.append({
                            'asset_id': f'diagram-page-{page_num + 1}-img-{img_index + 1}',
                            'image_path': image_path,
                            'page_num': page_num + 1
                        })
                        image_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to extract image {img_index} from page {page_num + 1}: {str(e)}")
                        continue
            
            doc.close()
            print(f"✅ Extracted {len(extracted_images)} image(s) from PDF")
            
        elif file_ext == '.docx':
            # Use python-docx to extract images
            try:
                from docx import Document
                import zipfile
                
                # DOCX files are ZIP archives, extract images from them
                doc = Document(file_path)
                docx_zip = zipfile.ZipFile(file_path, 'r')
                print(f"📄 Processing DOCX file...")
                
                # Extract all images from the document
                image_count = 0
                seen_images = set()  # Track unique images to avoid duplicates
                
                # Method 1: Extract from relationships
                for rel in doc.part.rels.values():
                    if "image" in rel.target_ref or rel.target_ref.startswith("media/"):
                        # Get the actual path in the ZIP file
                        # target_ref might be relative, need to construct full path
                        zip_path = rel.target_ref
                        if not zip_path.startswith("word/"):
                            zip_path = f"word/{zip_path}"
                        
                        # Skip if we've already processed this image
                        if zip_path in seen_images:
                            continue
                        seen_images.add(zip_path)
                        
                        try:
                            # Read binary data from ZIP
                            image_data = docx_zip.read(zip_path)
                        except KeyError:
                            # Try without word/ prefix
                            try:
                                zip_path = rel.target_ref
                                image_data = docx_zip.read(zip_path)
                            except KeyError:
                                # Try with media/ prefix
                                try:
                                    zip_path = f"word/media/{os.path.basename(rel.target_ref)}"
                                    image_data = docx_zip.read(zip_path)
                                except KeyError:
                                    print(f"Warning: Could not find image at {rel.target_ref}, skipping")
                                    continue
                        
                        image_count += 1
                        
                        # Determine image extension from the file
                        ext = os.path.splitext(zip_path)[1].lower()
                        if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']:
                            ext = '.png'  # Default to PNG
                        
                        image_path = os.path.join(temp_dir, f"image_{image_count}{ext}")
                        
                        # Write binary data
                        with open(image_path, 'wb') as img_file:
                            img_file.write(image_data)
                        
                        extracted_images.append({
                            'asset_id': f'diagram-{image_count}',
                            'image_path': image_path,
                            'page_num': None
                        })
                
                # Method 2: Also check word/media/ directory directly for any missed images
                try:
                    for zip_info in docx_zip.namelist():
                        if zip_info.startswith("word/media/") and zip_info not in seen_images:
                            # Check if it's an image file
                            ext = os.path.splitext(zip_info)[1].lower()
                            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']:
                                try:
                                    image_data = docx_zip.read(zip_info)
                                    image_count += 1
                                    image_path = os.path.join(temp_dir, f"image_{image_count}{ext}")
                                    
                                    with open(image_path, 'wb') as img_file:
                                        img_file.write(image_data)
                                    
                                    extracted_images.append({
                                        'asset_id': f'diagram-{image_count}',
                                        'image_path': image_path,
                                        'page_num': None
                                    })
                                    seen_images.add(zip_info)
                                except Exception as e:
                                    print(f"Warning: Failed to extract image {zip_info}: {str(e)}")
                                    continue
                except Exception as e:
                    print(f"Warning: Error scanning media directory: {str(e)}")
                
                docx_zip.close()
                print(f"✅ Extracted {len(extracted_images)} image(s) from DOCX")
                
            except ImportError:
                raise Exception("python-docx library not installed. Install: pip install python-docx")
        
        return extracted_images
        
    except Exception as e:
        # Clean up temp directory on error
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to extract diagrams from document: {str(e)}")


def convert_document_to_math_json(file_path, file_name):
    """
    Convert a document (PDF, DOCX, TXT) to math section JSON using GPT.
    This function handles diagram extraction and S3 upload.
    
    Args:
        file_path: Path to the uploaded file
        file_name: Original filename
        
    Returns:
        dict: Parsed math section JSON data
        
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
    elif file_ext == '.docx':
        if not HAS_DOCX:
            raise Exception("DOCX processing library not installed. Install python-docx.")
        extracted_text = extract_text_from_docx(file_path)
    elif file_ext == '.doc':
        # Legacy .doc files are not supported by python-docx
        raise Exception("Legacy .doc files are not directly supported. Please convert to .docx format, PDF, or use a screenshot instead. You can convert .doc to .docx using Microsoft Word or LibreOffice.")
    elif file_ext == '.txt':
        extracted_text = extract_text_from_txt(file_path)
    else:
        raise Exception(f"Unsupported file type: {file_ext}. Supported types: .pdf, .docx, .txt")
    
    if not extracted_text or not extracted_text.strip():
        raise Exception("No text could be extracted from the document. The file may be empty or corrupted.")
    
    # Extract diagrams from document
    print(f"🔍 Extracting diagrams from {file_name}...")
    diagrams = extract_diagrams_from_document(file_path, file_name)
    print(f"📊 Found {len(diagrams)} diagram(s) in document")
    
    # Upload diagrams to S3 and create a mapping of asset_id to S3 URL
    diagram_s3_map = {}  # Maps asset_id to S3 URL
    temp_dir = None
    
    # Create a temporary section_id for organizing uploads (will be replaced with actual section_id later)
    temp_section_id = os.path.splitext(file_name)[0].replace(' ', '-').lower()[:50]
    
    if diagrams:
        print(f"📤 Starting S3 uploads for {len(diagrams)} diagram(s)...")
        import shutil
        aws_storage_bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        
        for diagram in diagrams:
            try:
                # Upload to S3
                s3_url = upload_image_to_s3(
                    diagram['image_path'],
                    diagram['asset_id'],
                    temp_section_id
                )
                diagram_s3_map[diagram['asset_id']] = s3_url
                print(f"✓ Uploaded diagram {diagram['asset_id']} to S3: {s3_url}")
            except Exception as e:
                error_msg = f"✗ Failed to upload diagram {diagram['asset_id']} to S3: {str(e)}"
                print(error_msg)
                # Log the error but continue with other diagrams
                # We'll still include the diagram in the JSON but with a placeholder URL
                diagram_s3_map[diagram['asset_id']] = f"https://s3.amazonaws.com/{aws_storage_bucket_name}/lessons/{temp_section_id}/{diagram['asset_id']}.png"
                continue
        
        # Clean up temporary extracted images
        if diagrams and len(diagrams) > 0:
            temp_dir = os.path.dirname(diagrams[0]['image_path'])
        
        print(f"✅ S3 upload complete. Successfully uploaded {len(diagram_s3_map)}/{len(diagrams)} diagram(s)")
    else:
        print("ℹ️  No diagrams found in document, skipping S3 upload")
    
    # Call GPT to convert to JSON
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    schema_prompt = get_math_schema_prompt()
    
    # Add instructions about diagrams
    diagram_instructions = ""
    
    if diagrams and len(diagrams) > 0:
        # We have extracted diagrams, provide their asset_ids to GPT
        asset_ids = [d['asset_id'] for d in diagrams]
        diagram_instructions = f"""
    
## CRITICAL: Diagram Handling Instructions

The backend has extracted {len(diagrams)} diagram(s) from the document. You MUST use these exact asset_ids.

EXTRACTED DIAGRAMS:
"""
        for idx, diagram in enumerate(diagrams, 1):
            s3_url = diagram_s3_map.get(diagram['asset_id'], f"https://s3.amazonaws.com/bucket/lessons/{temp_section_id}/{diagram['asset_id']}.png")
            page_info = f" (Page {diagram['page_num']})" if diagram.get('page_num') else ""
            diagram_instructions += f"{idx}. asset_id: \"{diagram['asset_id']}\"{page_info}\n   s3_url: \"{s3_url}\"\n"
        
        diagram_instructions += f"""

MANDATORY REQUIREMENTS:
1. You MUST include ALL {len(diagrams)} diagram(s) in the shared_assets array using the EXACT asset_ids listed above
2. Use the EXACT s3_url values provided above for each asset_id
3. **CRITICAL: Match diagrams to questions intelligently** - For each question, analyze which diagram(s) belong to it:
   - Read the question text carefully - does it reference a diagram, figure, graph, or visual element?
   - Check the document context - which diagram appears near or with this question?
   - Consider the question content - does it ask about something shown in a diagram?
   - Look at the order - diagrams are extracted in document order, questions appear in document order
   - **Match by proximity**: If a diagram appears right before or after a question in the document, they likely belong together
   - **Match by content**: If a question asks "What is shown in the diagram?" or references visual elements, include the nearest diagram
   - **Match by context**: If multiple questions share a diagram, include that asset_id in all relevant questions' assets arrays
4. For each question that needs a diagram, include the asset_id(s) in the question's "assets" array
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
  "questions": [
    {{
      "question_id": "q1",
      "prompt": "What is shown in the diagram?",
      "assets": ["{diagrams[0]['asset_id'] if diagrams else 'diagram-1'}"],
      "choices": ["Option A", "Option B", "Option C", "Option D"],
      ...
    }}
  ]
}}
```
"""
    else:
        # No diagrams extracted, but GPT might still identify diagrams in text
        diagram_instructions = """
    
## Diagram Handling Instructions

If you encounter diagrams, figures, or visual elements in the document:
1. Identify each diagram and assign it a unique asset_id (e.g., "diagram-1", "diagram-2")
2. In the shared_assets array, create an asset object for each diagram
3. For the s3_url field, use a placeholder URL (diagrams will need to be manually uploaded)
4. Questions that reference a diagram should include its asset_id in their assets array

Note: If no diagrams were automatically extracted, you may still identify them in the text and create placeholder entries.
"""
    
    user_prompt = f"{schema_prompt}{diagram_instructions}\n\nDocument content:\n\n{extracted_text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for better JSON generation
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant that converts math documents into structured JSON format. 

CRITICAL REQUIREMENTS:
1. Every question MUST have a 'choices' array with at least 2 options (typically 4 options for multiple choice)
2. Every question MUST have a 'prompt' field with the question text
3. Every question MUST have an 'explanation' array (can be empty but must be an array)
4. Return ONLY valid JSON - no markdown code blocks, no explanations outside the JSON
5. Ensure all required fields are present before returning

If a question doesn't have choices in the document, infer reasonable choices based on the question type."""
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
        math_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise Exception(f"GPT returned invalid JSON: {str(e)}\n\nResponse was: {json_text[:500]}")
    
    # Validate basic structure
    if not isinstance(math_data, dict):
        raise ValueError("GPT returned invalid JSON: expected an object")
    if 'section_id' not in math_data:
        raise ValueError("GPT returned JSON missing 'section_id' field")
    if 'title' not in math_data:
        raise ValueError("GPT returned JSON missing 'title' field")
    if 'questions' not in math_data:
        raise ValueError("GPT returned JSON missing 'questions' field")
    if not isinstance(math_data['questions'], list):
        raise ValueError("GPT returned JSON with 'questions' that is not an array")
    if len(math_data['questions']) == 0:
        raise ValueError("GPT returned JSON with empty 'questions' array")
    
    # Validate questions
    for idx, q in enumerate(math_data['questions']):
        if not isinstance(q, dict):
            raise ValueError(f"Question {idx + 1} is not an object")
        if 'question_id' not in q:
            raise ValueError(f"Question {idx + 1} missing 'question_id' field")
        if 'prompt' not in q:
            raise ValueError(f"Question {idx + 1} missing 'prompt' field")
        if 'choices' not in q:
            raise ValueError(f"Question {idx + 1} missing 'choices' field. GPT must provide answer choices for every question. If choices aren't in the document, infer reasonable options.")
        if not isinstance(q['choices'], list):
            raise ValueError(f"Question {idx + 1} 'choices' must be an array, got {type(q['choices']).__name__}")
        if len(q['choices']) == 0:
            raise ValueError(f"Question {idx + 1} 'choices' must be a non-empty array. GPT returned an empty choices array. Every question needs answer options - if not in document, infer reasonable choices.")
        if len(q['choices']) < 2:
            raise ValueError(f"Question {idx + 1} 'choices' must have at least 2 options, got {len(q['choices'])}. Multiple choice questions typically have 4 options.")
        if 'explanation' not in q:
            raise ValueError(f"Question {idx + 1} missing 'explanation' field")
        if not isinstance(q['explanation'], list):
            raise ValueError(f"Question {idx + 1} 'explanation' must be an array")
        if 'correct_answer_index' in q:
            if not isinstance(q['correct_answer_index'], int):
                raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be an integer")
            if q['correct_answer_index'] < 0 or q['correct_answer_index'] >= len(q['choices']):
                raise ValueError(f"Question {idx + 1} 'correct_answer_index' must be 0-{len(q['choices'])-1}")
    
    # Validate and update shared_assets if we extracted diagrams
    if diagrams and len(diagrams) > 0:
        # Ensure shared_assets array exists
        if 'shared_assets' not in math_data:
            math_data['shared_assets'] = []
        elif not isinstance(math_data['shared_assets'], list):
            math_data['shared_assets'] = []
        
        # Get all extracted asset_ids
        extracted_asset_ids = {d['asset_id'] for d in diagrams}
        
        # Get asset_ids that GPT included
        gpt_asset_ids = {asset.get('asset_id') for asset in math_data['shared_assets'] if asset.get('asset_id')}
        
        # Check if all extracted diagrams are included
        missing_assets = extracted_asset_ids - gpt_asset_ids
        if missing_assets:
            # Add missing assets automatically
            for diagram in diagrams:
                if diagram['asset_id'] in missing_assets:
                    s3_url = diagram_s3_map.get(diagram['asset_id'])
                    if s3_url:
                        math_data['shared_assets'].append({
                            'asset_id': diagram['asset_id'],
                            'type': 'image',
                            's3_url': s3_url
                        })
                        print(f"Warning: GPT did not include extracted diagram '{diagram['asset_id']}', adding it automatically")
        
        # Update all assets with actual S3 URLs
        for asset in math_data['shared_assets']:
            asset_id = asset.get('asset_id')
            if asset_id in diagram_s3_map:
                asset['s3_url'] = diagram_s3_map[asset_id]
    
    # Validate assets if present
    if 'shared_assets' in math_data and isinstance(math_data['shared_assets'], list):
        for idx, asset in enumerate(math_data['shared_assets']):
            if not isinstance(asset, dict):
                raise ValueError(f"Asset {idx + 1} is not an object")
            if 'asset_id' not in asset:
                raise ValueError(f"Asset {idx + 1} missing 'asset_id' field")
            if 'type' not in asset:
                raise ValueError(f"Asset {idx + 1} missing 'type' field")
            if 's3_url' not in asset:
                raise ValueError(f"Asset {idx + 1} missing 's3_url' field")
    
    # Validate asset references in questions
    asset_ids = set()
    if 'shared_assets' in math_data and isinstance(math_data['shared_assets'], list):
        asset_ids = {asset.get('asset_id') for asset in math_data['shared_assets'] if asset.get('asset_id')}
    
    for idx, q in enumerate(math_data['questions']):
        if 'assets' in q and isinstance(q['assets'], list):
            for asset_id in q['assets']:
                if asset_id not in asset_ids:
                    raise ValueError(f"Question {idx + 1} references asset '{asset_id}' which does not exist in shared_assets")
    
    # Clean up temporary directory
    if temp_dir and os.path.exists(temp_dir):
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    
    return math_data

