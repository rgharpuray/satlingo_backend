# Lesson JSON Schema

This document describes the expected JSON format for lesson ingestion. Use this schema when converting lessons into JSON format for the system.

## Root Structure

```json
{
  "lesson_id": "string (required, unique identifier, e.g., 'commas')",
  "title": "string (required, lesson title)",
  "difficulty": "string (optional, one of: 'Easy', 'Medium', 'Hard', default: 'Medium')",
  "tier": "string (optional, one of: 'free', 'premium', default: 'free')",
  "chunks": [ /* array of chunk objects (required) */ ]
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
  "correct_answer_index": 2  // optional, integer index (0-based) of correct answer, defaults to 0 if not provided. If provided, must be >= 0 and < length of choices array
}
```

**Important:** 
- `prompt` is **REQUIRED** - the question will fail validation if missing
- `choices` is **REQUIRED** - must be a non-empty array, or validation will fail
- `correct_answer_index` is optional. If not provided, defaults to 0 (first choice). If provided, must be a valid index (0-based) within the choices array, otherwise validation will fail.

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

## Complete Example

```json
{
  "lesson_id": "commas",
  "title": "Commas",
  "difficulty": "Medium",
  "tier": "free",
  "chunks": [
    {
      "type": "header",
      "level": 1,
      "text": "Commas"
    },
    {
      "type": "paragraph",
      "text": "Commas probably show up on the test more frequently than any other grammar topic."
    },
    {
      "type": "header",
      "level": 2,
      "text": "Lists"
    },
    {
      "type": "paragraph",
      "text": "We use commas between each of the items in a list:"
    },
    {
      "type": "example",
      "text": "I had to buy apples, bananas, and cucumbers."
    },
    {
      "type": "header",
      "level": 3,
      "text": "Multiple Choice"
    },
    {
      "type": "question",
      "question_type": "multiple_choice",
      "prompt": "I did my laundry made my bed and performed my nightly breathing exercises.",
      "choices": [
        "NO CHANGE",
        "I did, my laundry, made, my bed, and performed, my nightly breathing exercises.",
        "I did my laundry, made my bed, and performed my nightly breathing exercises.",
        "I did, my laundry, made my bed, and performed my nightly breathing exercises."
      ],
      "correct_answer_index": 2
    }
  ]
}
```

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

## Conversion Guidelines for GPT

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

