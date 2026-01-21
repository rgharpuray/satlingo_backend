# LessonQuestion Text Rendering Fix

## Problem

iOS app logs show empty question text:
```
Question 1 text: '' (empty: true)
```

## Root Cause

`LessonQuestion.text` is a **JSON array of ContentBlock objects**, not a plain string.

**What the API returns:**
```json
{
  "text": [
    {"type": "paragraph", "content": "What is 2 + 2?"}
  ]
}
```

**What the iOS app expects:**
```json
{
  "text": "What is 2 + 2?"
}
```

## Fix

### 1. Update ContentBlock Model

```swift
struct ContentBlock: Codable {
    let type: String  // "paragraph", "text", "example", "diagram", "rule", "side_by_side"
    let content: String?
    let diagramId: String?
    let left: String?
    let right: String?
    
    enum CodingKeys: String, CodingKey {
        case type, content, left, right
        case diagramId = "diagram_id"
    }
}
```

### 2. Update LessonQuestion Model

```swift
struct LessonQuestion: Codable, Identifiable {
    let id: UUID
    let text: [ContentBlock]  // THIS IS AN ARRAY, NOT A STRING
    let options: [QuestionOption]
    let correctAnswerIndex: Int
    let explanation: [ContentBlock]?
    let order: Int
    let chunkIndex: Int?
    let assets: [LessonAsset]
    
    enum CodingKeys: String, CodingKey {
        case id, text, options, explanation, order, assets
        case correctAnswerIndex = "correct_answer_index"
        case chunkIndex = "chunk_index"
    }
}
```

### 3. Add Display Text Extension

```swift
extension LessonQuestion {
    /// Extracts plain text from question blocks for display
    var displayText: String {
        return text.compactMap { block -> String? in
            switch block.type {
            case "paragraph", "text", "example", "rule":
                return block.content
            case "side_by_side":
                let left = block.left ?? ""
                let right = block.right ?? ""
                return left.isEmpty && right.isEmpty ? nil : "\(left) | \(right)"
            case "diagram":
                return nil  // Diagrams are rendered separately as images
            default:
                return block.content
            }
        }.joined(separator: "\n\n")
    }
}
```

### 4. Update UI to Use displayText

**Before (broken):**
```swift
Text(question.text)  // ERROR: text is [ContentBlock], not String
```

**After (fixed):**
```swift
Text(question.displayText)  // Uses the extension to extract text
```

## Block Types Reference

| Type | Fields | Description |
|------|--------|-------------|
| `paragraph` | `content` | Main question text |
| `text` | `content` | Plain text |
| `example` | `content` | Example (styled) |
| `rule` | `content` | Grammar/math rule |
| `diagram` | `diagram_id` | Image (resolve from assets) |
| `side_by_side` | `left`, `right` | Two-column comparison |

## Handling Diagrams

If `displayText` is empty but `text` array has diagram blocks:

```swift
extension LessonQuestion {
    var diagramIds: [String] {
        return text.compactMap { $0.type == "diagram" ? $0.diagramId : nil }
    }
    
    var hasDiagrams: Bool {
        return !diagramIds.isEmpty
    }
}

// In your view:
if question.displayText.isEmpty && question.hasDiagrams {
    // Render diagram images from assets
    ForEach(question.diagramIds, id: \.self) { diagramId in
        if let asset = lesson.assets.first(where: { $0.assetId == diagramId }) {
            AsyncImage(url: URL(string: asset.s3Url))
        }
    }
} else {
    Text(question.displayText)
}
```

## Quick Test

```swift
// Debug logging
print("Question text blocks: \(question.text.count)")
print("First block type: \(question.text.first?.type ?? "none")")
print("First block content: \(question.text.first?.content ?? "none")")
print("Display text: '\(question.displayText)'")
```

## Summary

| Field | Type | How to Display |
|-------|------|----------------|
| `LessonQuestion.text` | `[ContentBlock]` | Use `.displayText` |
| `PassageQuestion.text` | `String` | Direct |
| `WritingSectionQuestion.text` | `String` | Direct |
| `MathQuestion.text` | `String` | Direct |

Only `LessonQuestion` uses the block array format. All other question types use plain strings.
