# How to Trigger Passage Ingestion

## Automatic Processing (Recommended)

**The ingestion triggers automatically when you upload a file!**

1. Go to **Admin Panel** → **API** → **Passage ingestions**
2. Click **"Add Passage Ingestion"**
3. Click **"Choose File"** and select your image/PDF
4. Click **"Save"**
5. **That's it!** The system will automatically:
   - Save the file
   - Extract text using OCR
   - Parse with AI to create passage/questions
   - Create the passage in the database

The processing happens **synchronously** (you'll wait for it to complete), so:
- For small images: 10-30 seconds
- For PDFs or large images: 30-60 seconds
- You'll see an error message if something fails

## Manual Processing (If Needed)

If automatic processing didn't work or you want to retry:

### Option 1: Use Admin Actions
1. Go to **Passage ingestions** list view
2. Check the box next to the ingestion(s) you want to process
3. Select **"Process selected ingestions"** from the Actions dropdown
4. Click **"Go"**

### Option 2: Edit and Re-save
1. Click on the ingestion to edit it
2. Just click **"Save"** again (the file is already uploaded)
3. It will re-trigger processing

## Check Status

After uploading, you can check the status:

- **Pending**: File uploaded, waiting to process
- **Processing**: Currently extracting text and parsing
- **Completed**: Successfully created passage (click the link to view it!)
- **Failed**: Error occurred (check the error_message field)

## Troubleshooting

**"Nothing happens when I click Save"**
- Check the browser console for errors
- Make sure you selected a file before clicking Save
- Check that the file path is shown in the "File path" field

**"Status stays on Pending"**
- The processing might have failed silently
- Check the "Error message" field
- Try the manual processing option

**"Processing takes forever"**
- Large PDFs can take 1-2 minutes
- Check server logs for progress
- You can refresh the page to see updated status

## What Happens During Processing

1. **File Upload** (instant)
   - File saved to `media/ingestions/`

2. **OCR Extraction** (10-30 seconds)
   - Text extracted from image/PDF
   - Saved to `extracted_text` field

3. **AI Parsing** (10-30 seconds)
   - OpenAI analyzes the text
   - Identifies passage, questions, answers
   - Creates structured JSON

4. **Database Creation** (instant)
   - Creates Passage object
   - Creates Question objects
   - Creates QuestionOption objects
   - Links everything together

5. **Status Update** (instant)
   - Status changes to "Completed"
   - Link to created passage appears


