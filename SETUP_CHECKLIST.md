# Setup Checklist for Passage Ingestion

## ✅ Completed
- [x] Tesseract OCR is installed (`/opt/homebrew/bin/tesseract`)
- [x] Database migrations created
- [x] Code implemented

## ⚠️ Still Need To Do

### 1. Run Database Migration
```bash
python3 manage.py migrate
```
**Status:** ✅ Just ran this

### 2. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```
This will install:
- `pytesseract` (OCR library)
- `Pillow` (image processing)
- `pdf2image` (PDF processing)
- `openai` (AI parsing)
- Other dependencies

**Status:** ⚠️ Need to run this

### 3. Install PDF Support (if using PDFs)
```bash
brew install poppler
```
**Status:** ⚠️ Only needed if uploading PDFs

### 4. Set OpenAI API Key
```bash
export OPENAI_API_KEY='your-api-key-here'
```
Or add to a `.env` file and load it.

**Status:** ⚠️ Need to set this

### 5. Create Media Directory
```bash
mkdir -p media/ingestions
```
**Status:** ⚠️ Will be created automatically, but good to verify

## Quick Start

After completing the above:

1. **Start the server:**
   ```bash
   python3 manage.py runserver
   ```

2. **Access admin panel:**
   - Go to: http://localhost:8000/admin/
   - Login with: `admin` / `admin123`

3. **Upload a passage:**
   - Navigate to **API > Passage ingestions**
   - Click **Add Passage Ingestion**
   - Upload an image or PDF
   - Click **Save**
   - Wait for processing (check status field)

## Testing Without OpenAI

If you don't have an OpenAI API key yet, the ingestion will fail at the AI parsing step. You can still test the OCR extraction by checking the "Extracted Text Preview" field in the admin panel.

## Need Help?

See `INGESTION_GUIDE.md` for detailed documentation.


