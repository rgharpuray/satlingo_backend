# Math Section JSON Schema

This document describes the expected JSON format for math section ingestion. Math sections are question-centric, with diagrams that need to be uploaded to S3.

## Root Structure

```json
{
  "section_id": "string (required, unique identifier, e.g., 'algebra-basics')",
  "title": "string (required, section title)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "shared_assets": [ /* array of asset objects (optional) */ ],
  "questions": [ /* array of question objects (required) */ ]
}
```

## Asset Structure

Assets represent diagrams, images, or other visual elements that are shared across questions.

```json
{
  "asset_id": "diagram-1",  // REQUIRED - unique string identifier
  "type": "image",  // REQUIRED - currently only "image" is supported
  "s3_url": "https://s3.amazonaws.com/bucket/path/to/diagram.png"  // REQUIRED - public S3 URL
}
```

## Question Structure

Each question is a standalone math problem.

```json
{
  "question_id": "q1",  // REQUIRED - unique string identifier
  "prompt": "What is the value of x in the equation 2x + 5 = 15?",  // REQUIRED
  "choices": [  // REQUIRED - must be a non-empty array
    "x = 3",
    "x = 5",
    "x = 10",
    "x = 7"
  ],
  "correct_answer_index": 1,  // optional, integer index (0-based) of correct answer, defaults to 0
  "assets": ["diagram-1"],  // optional, array of asset_id strings that this question references
  "explanation": [  // REQUIRED - array of explanation blocks
    {
      "type": "paragraph",
      "text": "To solve this equation, we need to isolate x."
    },
    {
      "type": "equation",
      "latex": "2x + 5 = 15"
    },
    {
      "type": "paragraph",
      "text": "Subtract 5 from both sides:"
    },
    {
      "type": "equation",
      "latex": "2x = 10"
    },
    {
      "type": "paragraph",
      "text": "Divide both sides by 2:"
    },
    {
      "type": "equation",
      "latex": "x = 5"
    }
  ]
}
```

## Explanation Block Types

Explanation blocks are ordered and preserve the instructional flow.

### 1. Paragraph
Regular explanatory text.

```json
{
  "type": "paragraph",
  "text": "This is explanatory text that helps understand the solution."
}
```

### 2. Equation
LaTeX math equation.

```json
{
  "type": "equation",
  "latex": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}"
}
```

### 3. Note
Warning, caution, or important note.

```json
{
  "type": "note",
  "text": "Remember to check your units when solving physics problems."
}
```

### 4. Example
Worked example text.

```json
{
  "type": "example",
  "text": "For example, if x = 3, then 2(3) + 5 = 11, which is not equal to 15."
}
```

## Complete Example

```json
{
  "section_id": "linear-equations",
  "title": "Solving Linear Equations",
  "difficulty": "Medium",
  "tier": "free",
  "shared_assets": [
    {
      "asset_id": "coordinate-plane-1",
      "type": "image",
      "s3_url": "https://s3.amazonaws.com/bucket/math/coordinate-plane-1.png"
    }
  ],
  "questions": [
    {
      "question_id": "q1",
      "prompt": "What is the value of x in the equation 2x + 5 = 15?",
      "choices": [
        "x = 3",
        "x = 5",
        "x = 10",
        "x = 7"
      ],
      "correct_answer_index": 1,
      "assets": [],
      "explanation": [
        {
          "type": "paragraph",
          "text": "To solve this equation, we need to isolate x."
        },
        {
          "type": "equation",
          "latex": "2x + 5 = 15"
        },
        {
          "type": "paragraph",
          "text": "Subtract 5 from both sides:"
        },
        {
          "type": "equation",
          "latex": "2x = 10"
        },
        {
          "type": "paragraph",
          "text": "Divide both sides by 2:"
        },
        {
          "type": "equation",
          "latex": "x = 5"
        }
      ]
    },
    {
      "question_id": "q2",
      "prompt": "Which point on the coordinate plane shown represents (3, 4)?",
      "choices": [
        "Point A",
        "Point B",
        "Point C",
        "Point D"
      ],
      "correct_answer_index": 2,
      "assets": ["coordinate-plane-1"],
      "explanation": [
        {
          "type": "paragraph",
          "text": "The coordinate (3, 4) means x = 3 and y = 4."
        },
        {
          "type": "paragraph",
          "text": "Looking at the diagram, we move 3 units to the right and 4 units up from the origin."
        },
        {
          "type": "paragraph",
          "text": "This corresponds to Point C."
        }
      ]
    }
  ]
}
```

## Important Notes

1. **Question-First Structure**: Math content is question-centric. Each problem is a standalone question. Do NOT create a single long passage.

2. **Diagram/Image Handling**:
   - Extract all diagrams, figures, or visual elements from the document
   - Export each diagram as an image (PNG or SVG preferred)
   - Upload each image to S3
   - Create one asset object per diagram in `shared_assets`
   - Questions that use a diagram must reference it by `asset_id` in their `assets` array
   - Multiple questions may reference the same asset

3. **Explanations**:
   - Must preserve all instructional content
   - Do NOT summarize or compress
   - Maintain original order
   - Use appropriate explanation block types

4. **Required Fields**:
   - Root level: `section_id`, `title`, `questions`
   - Question: `question_id`, `prompt`, `choices`, `explanation`
   - Explanation block: `type`, and the appropriate field (`text` for paragraph/note/example, `latex` for equation)
   - Asset: `asset_id`, `type`, `s3_url`

5. **Optional Fields**:
   - Root level: `difficulty` (defaults to "Medium"), `tier` (defaults to "free"), `shared_assets`
   - Question: `correct_answer_index` (defaults to 0), `assets`

6. **Validation Requirements**:
   - `section_id`, `title`, and `questions` are required
   - `questions` must be a non-empty array
   - Each question must have `prompt`, `choices`, `explanation`
   - `correct_answer_index` must be valid if present (0 to length-1)
   - Referenced `asset_id`s must exist in `shared_assets`
   - Output MUST be valid JSON

## Conversion Guidelines for GPT

When converting math content to this format:

1. **Extract diagrams first**: Identify all visual elements (diagrams, graphs, figures)
2. **Upload to S3**: Each diagram should be uploaded and get an S3 URL
3. **Create assets**: Add each diagram to `shared_assets` with a unique `asset_id`
4. **Create questions**: Each math problem becomes a question object
5. **Reference assets**: If a question uses a diagram, reference it in the question's `assets` array
6. **Preserve explanations**: Maintain all instructional content in the `explanation` array
7. **Use appropriate block types**: Use `paragraph`, `equation`, `note`, or `example` as appropriate

## Diagram Extraction and Upload

For the GPT conversion process:
- Diagrams should be extracted from the source document
- Each diagram should be saved as an image file (PNG or SVG)
- Upload each image to S3 (or configured storage)
- Store the S3 URL in the asset object
- Reference the asset by `asset_id` in questions that need it

Note: The actual diagram extraction and S3 upload will be handled by the backend during GPT conversion. GPT should identify which parts of the document are diagrams and provide instructions for extraction.







