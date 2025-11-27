# Django Admin Panel Guide

## Quick Start

### 1. Create a Superuser

To access the admin panel, you need to create a superuser account:

```bash
python manage.py createsuperuser
```

Follow the prompts to set:
- Email address
- Username
- Password

### 2. Access Admin Panel

1. Start the server: `python manage.py runserver 8001`
2. Open browser: http://localhost:8001/admin/
3. Login with your superuser credentials

## Creating Passages with Questions

### Step-by-Step Process

1. **Go to Passages** in the admin panel
2. **Click "Add Passage"**
3. **Fill in Passage Details:**
   - **Title**: e.g., "Phrenology"
   - **Content**: Paste the full passage text
   - **Difficulty**: Select Easy, Medium, or Hard
   - **Tier**: Select Free or Premium
4. **Click "Save and continue editing"** (or "Save")
5. **Add Questions:**
   - Scroll down to the "Questions" section
   - Click "Add another Question"
   - Fill in:
     - **Order**: Question number (0, 1, 2, etc.)
     - **Text**: The question text
     - **Correct Answer Index**: 0-based index (0 = first option, 1 = second, etc.)
     - **Explanation**: Why the answer is correct (optional but recommended)
6. **Add Options for Each Question:**
   - After saving a question, you'll see a link "Edit Question & Options →" in the question inline
   - Click that link (or go to Questions in the admin menu and find your question)
   - In the question edit page, scroll to the "Question Options" section
   - Click "Add another Question Option"
   - Fill in:
     - **Order**: 0, 1, 2, 3 (for A, B, C, D)
     - **Text**: The option text
   - Add 4 options (or however many you need)
   - Make sure the **Order** matches the **Correct Answer Index** in the question
   - Save the question

### Example

**Passage:**
- Title: "The History of Phrenology"
- Content: "Phrenology was a pseudoscience that attempted to..."
- Difficulty: Medium
- Tier: Free

**Question 1:**
- Order: 0
- Text: "The author's view of phrenology can be best described as:"
- Correct Answer Index: 2
- Explanation: "The author acknowledges both phrenology's flaws and its historical significance."

**Options for Question 1:**
- Order 0: "utterly scornful"
- Order 1: "hopeful"
- Order 2: "mixed" ← This is the correct answer (index 2)
- Order 3: "indifferent"

## Tips

1. **Save Frequently**: Save the passage before adding questions, then save questions before adding options
2. **Order Matters**: Question order and option order determine the sequence
3. **Correct Answer Index**: Must match the option's order number (0-based)
4. **Bulk Creation**: You can create multiple questions at once using the inline editor
5. **Tier Management**: Use the tier field to mark content as Free or Premium

## Admin Features

### Passage List View
- See all passages with difficulty, tier, and question count
- Filter by difficulty, tier, or date
- Search by title or content

### Question Management
- View all questions across all passages
- Filter by passage, difficulty, or tier
- See which questions have explanations

### Option Management
- View all options
- See which option is the correct answer for each question
- Filter by passage

## Common Workflows

### Creating a Complete Passage

1. Create passage → Save
2. Add first question → Save passage again
3. Click "Edit Question & Options →" link for first question
4. Add 4 options for first question → Save question
5. Go back to passage edit page
6. Add second question → Save passage again
7. Click "Edit Question & Options →" link for second question
8. Add 4 options for second question → Save question
9. Repeat for all questions

**Alternative Workflow:**
1. Create passage → Save
2. Add all questions inline → Save passage
3. Go to "Questions" in admin menu
4. Edit each question individually to add options

### Editing Existing Content

1. Find passage in list
2. Click to edit
3. Modify passage details, questions, or options inline
4. Save changes

### Bulk Operations

- Use the admin list filters to find specific passages
- Export data using Django admin actions (if configured)
- Use the search to quickly find content

## Troubleshooting

### Can't See Questions Section
- Make sure you've saved the passage first
- Refresh the page

### Options Not Showing
- Make sure you've saved the question first
- Click the "Edit Question & Options →" link from the passage edit page
- Or go to Questions in the admin menu and edit the question directly
- Options are added in the question edit page, not in the passage edit page

### Correct Answer Not Working
- Verify the Correct Answer Index matches an option's Order
- Remember: indices are 0-based (0, 1, 2, 3)

### Admin Not Loading
- Check server is running: `python manage.py runserver 8001`
- Verify you're logged in as superuser
- Check browser console for errors


