# Passage Ingestion Guide

This feature allows you to automatically create passages with questions by uploading images (screenshots) or PDF files. The system uses OCR to extract text and AI to parse it into structured passages with questions and answers.

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR (System Package)

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Configure OpenAI API Key

Set your OpenAI API key in environment variables:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or add to your `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

### 4. Run Migrations

```bash
python manage.py migrate
```

## Usage

### Via Admin Panel

1. Log in to Django admin: `http://localhost:8000/admin/`
2. Navigate to **API > Passage ingestions**
3. Click **Add Passage Ingestion**
4. Upload an image (PNG, JPG) or PDF file containing:
   - A reading passage
   - Questions with multiple choice options
   - Correct answers (the system will try to identify them)
5. Click **Save**
6. The system will:
   - Extract text using OCR
   - Parse the content with AI
   - Create a new Passage with Questions and Options
7. Check the status - when complete, you'll see a link to the created passage

### Supported File Types

- **Images**: PNG, JPG, JPEG, GIF, BMP
- **PDFs**: PDF files (converted to images first)

### How It Works

1. **OCR Extraction**: The uploaded file is processed to extract all text
2. **AI Parsing**: OpenAI GPT-4 analyzes the extracted text and identifies:
   - Passage title
   - Passage content
   - Difficulty level
   - Questions with options
   - Correct answer indices
   - Explanations (if present)
3. **Database Creation**: A new Passage is created with all Questions and Options

### Tips for Best Results

- **Clear Images**: Use high-quality screenshots or scans
- **Structured Format**: The AI works best when questions are clearly separated
- **Complete Content**: Include the full passage and all questions in one upload
- **Standard Format**: Questions with A/B/C/D options work best

### Troubleshooting

**"OCR libraries not installed"**
- Install Tesseract OCR system package (see Setup above)
- Install Python packages: `pip install Pillow pytesseract`

**"PDF processing libraries not installed"**
- Install: `pip install pdf2image`
- On macOS, also install: `brew install poppler`

**"OpenAI API key not configured"**
- Set the `OPENAI_API_KEY` environment variable

**Processing fails**
- Check the error message in the admin panel
- Ensure the image/PDF is clear and readable
- Try a different file format or re-scan at higher quality

## Status Tracking

Each ingestion has a status:
- **Pending**: File uploaded, waiting to process
- **Processing**: Currently extracting text and parsing
- **Completed**: Successfully created passage
- **Failed**: Error occurred (check error_message field)

## Google Drive Integration (Coming Soon)

Future versions will support direct Google Drive file imports.


