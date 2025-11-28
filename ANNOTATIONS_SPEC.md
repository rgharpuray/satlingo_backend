# Passage Annotations API Specification

Complete guide for implementing text annotations that appear **AFTER** users answer questions.

**🚀 IMPORTANT: Annotations are automatically included in answer responses - no separate API call needed!**

## Overview

Annotations highlight specific text selections in passages and show explanations **immediately after the user answers each question**. This provides real-time contextual feedback as users work through the passage.

**Key Behavior:**
- Annotations are on the **passage text** (character positions)
- Annotations are **tied to specific questions**
- Annotations **appear IMMEDIATELY** after answering that question (question-by-question feedback)
- Multiple annotations can be associated with one question
- Annotations accumulate as you answer more questions

## Data Model

### Annotation Object

```typescript
interface PassageAnnotation {
  id: string; // UUID
  question_id: string | null; // UUID of associated question (null = general annotation)
  start_char: number; // 0-based start position
  end_char: number; // 0-based end position (exclusive)
  selected_text: string; // The selected text
  explanation: string; // Explanation/comment
  order: number; // Display order (if multiple annotations for same question)
}
```

**Important Notes:**
- `question_id` links the annotation to a specific question
- `start_char` and `end_char` are **0-based character indices** in the passage content
- `end_char` is **exclusive** (like string.substring)
- Character positions include spaces, newlines, and all characters

## API Endpoints

### Submit Answer (Annotations Included Automatically)

**Endpoint:** `POST /api/v1/answers`

**Request Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "question_id": "660e8400-e29b-41d4-a716-446655440001",
  "selected_option_index": 2
}
```

**Response (200 OK):**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440001",
  "question_id": "660e8400-e29b-41d4-a716-446655440001",
  "selected_option_index": 2,
  "is_correct": true,
  "answered_at": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "annotations": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440001",
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "start_char": 45,
      "end_char": 67,
      "selected_text": "phrenology was a",
      "explanation": "Phrenology is a pseudoscience that attempted to determine personality traits by measuring the skull.",
      "order": 0
    }
  ]
}
```

**IMPORTANT:** 
- **Annotations are automatically included** in the response - no separate API call needed
- Annotations array is **always present** (empty array `[]` if no annotations exist for that question)
- Use the annotations immediately to highlight text on the passage
- Annotations appear **only after** answering the question (they're tied to the question)

### Get All Answers for a Passage (With Annotations)

**Endpoint:** `GET /api/v1/answers/passage/{passage_id}`

**Request Headers:**
```
Authorization: Bearer <access_token>
```

Returns all answers the user has submitted for a passage, **with annotations automatically included for each answered question**.

**Example Request:**
```bash
GET /api/v1/answers/passage/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

**Example Response:**
```json
{
  "answers": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440001",
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "selected_option_index": 2,
      "is_correct": true,
      "answered_at": "2024-01-01T12:00:00Z",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "annotations": [
        {
          "id": "aa0e8400-e29b-41d4-a716-446655440001",
          "question_id": "660e8400-e29b-41d4-a716-446655440001",
          "start_char": 45,
          "end_char": 67,
          "selected_text": "phrenology was a",
          "explanation": "Phrenology is a pseudoscience...",
          "order": 0
        }
      ]
    }
  ]
}
```

**Use Case:** 
- Call this when loading a passage to get all previously answered questions and their annotations
- Useful for displaying the passage with all current annotations already applied
- Annotations are **automatically included** - no separate call needed

### Get Annotations for a Passage

**Endpoint:** `GET /passages/{passage_id}/annotations`

**Request Headers:**
```
Authorization: Bearer <access_token>  // Required for authenticated users
```

**Behavior:**
- Only returns annotations for questions the user has **already answered**
- Anonymous users get empty array
- Premium passage access is still enforced

**Example Request:**
```bash
GET /api/v1/passages/550e8400-e29b-41d4-a716-446655440000/annotations
Authorization: Bearer <token>
```

**Example Response:**
```json
{
  "annotations": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440001",
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "start_char": 45,
      "end_char": 67,
      "selected_text": "phrenology was a",
      "explanation": "Phrenology is a pseudoscience that attempted to determine personality traits by measuring the skull.",
      "order": 0
    }
  ]
}
```

**Note:** Only annotations for questions you've answered are returned.

### Get Review Data (Includes Annotations)

**Endpoint:** `GET /progress/passages/{passage_id}/review`

This endpoint returns review data **with annotations included for each answered question** (for final review after completing all questions).

**Example Response:**
```json
{
  "passage_id": "550e8400-e29b-41d4-a716-446655440000",
  "score": 85,
  "answers": [
    {
      "question_id": "660e8400-e29b-41d4-a716-446655440001",
      "question_text": "The author's view of phrenology can be best described as:",
      "options": ["utterly scornful", "hopeful", "mixed", "indifferent"],
      "selected_option_index": 2,
      "correct_answer_index": 2,
      "is_correct": true,
      "explanation": "The author acknowledges both phrenology's flaws...",
      "annotations": [
        {
          "id": "aa0e8400-e29b-41d4-a716-446655440001",
          "start_char": 45,
          "end_char": 67,
          "selected_text": "phrenology was a",
          "explanation": "Phrenology is a pseudoscience...",
          "order": 0
        }
      ]
    }
  ]
}
```

**Key Points:**
- Each answer object includes an `annotations` array
- Only annotations for that specific question are included
- Only shown for questions the user has answered

---

## Client Implementation Guide

### Flow

1. **User reads passage** → No annotations visible
2. **User answers Question 1** → Annotations for Q1 appear **immediately** on passage text
3. **User answers Question 2** → Annotations for Q2 appear **immediately** (Q1 annotations still visible)
4. **User continues answering** → Annotations accumulate as each question is answered
5. **User views passage** → All annotations for answered questions remain visible

### Character Index System

The backend uses **0-based character indices** to mark text ranges:

```
Passage: "The quick brown fox jumps over the lazy dog."
         0123456789012345678901234567890123456789012345
         
Annotation: start_char=4, end_char=9
Selection: "quick"
```

**Important:**
- Indices are **character positions**, not word positions
- Include spaces, punctuation, and newlines in the count
- `end_char` is **exclusive** (not included in the range)

### iOS/Swift Implementation

#### 1. Data Models

```swift
struct PassageAnnotation: Codable {
    let id: String
    let questionId: String?
    let startChar: Int
    let endChar: Int
    let selectedText: String
    let explanation: String
    let order: Int
    
    enum CodingKeys: String, CodingKey {
        case id
        case questionId = "question_id"
        case startChar = "start_char"
        case endChar = "end_char"
        case selectedText = "selected_text"
        case explanation
        case order
    }
}

struct ReviewAnswer: Codable {
    let questionId: String
    let questionText: String
    let options: [String]
    let selectedOptionIndex: Int?
    let correctAnswerIndex: Int
    let isCorrect: Bool?
    let explanation: String?
    let annotations: [PassageAnnotation]  // Annotations for this question
}
```

#### 2. Submit Answer (Annotations Included Automatically)

```swift
func submitAnswer(questionId: String, optionIndex: Int, completion: @escaping (Result<AnswerResponse, Error>) -> Void) {
    guard let accessToken = AuthService.shared.getAccessToken(),
          let url = URL(string: "\(baseURL)/api/v1/answers") else {
        completion(.failure(AuthError.notAuthenticated))
        return
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "question_id": questionId,
        "selected_option_index": optionIndex
    ]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let data = data {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let answer = try? decoder.decode(AnswerResponse.self, from: data)
            if let answer = answer {
                // Annotations are AUTOMATICALLY included in the response!
                // No separate API call needed - just use answer.annotations
                self.applyAnnotationsToPassage(answer.annotations)
                completion(.success(answer))
            }
        }
    }.resume()
}

struct AnswerResponse: Codable {
    let id: String
    let questionId: String
    let selectedOptionIndex: Int
    let isCorrect: Bool
    let answeredAt: String
    let createdAt: String
    let updatedAt: String
    let annotations: [PassageAnnotation]  // Always present - empty array if none
}
```

#### 3. Get All Answers with Annotations (For Loading Existing State)

```swift
func fetchAnswers(for passageId: String, completion: @escaping (Result<[AnswerResponse], Error>) -> Void) {
    guard let accessToken = AuthService.shared.getAccessToken(),
          let url = URL(string: "\(baseURL)/api/v1/answers/passage/\(passageId)") else {
        completion(.failure(AuthError.notAuthenticated))
        return
    }
    
    var request = URLRequest(url: url)
    request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let data = data {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let answersArray = json["answers"] as? [[String: Any]] {
                let answers = answersArray.compactMap { answerDict -> AnswerResponse? in
                    guard let answerData = try? JSONSerialization.data(withJSONObject: answerDict) else { return nil }
                    return try? decoder.decode(AnswerResponse.self, from: answerData)
                }
                completion(.success(answers))
            }
        }
    }.resume()
}
```

**Note:** Annotations are **automatically included** in each answer object - no separate API call needed.

#### 3. Apply Annotations to Passage Text

```swift
func applyAnnotations(to text: String, annotations: [PassageAnnotation]) -> NSAttributedString {
    let attributedString = NSMutableAttributedString(string: text)
    
    // Sort annotations by start position (iterate backwards to preserve indices)
    let sortedAnnotations = annotations.sorted { $0.startChar < $1.startChar }
    
    for annotation in sortedAnnotations.reversed() {
        let range = NSRange(location: annotation.startChar, length: annotation.endChar - annotation.startChar)
        
        // Check if range is valid
        guard range.location + range.length <= attributedString.length else { continue }
        
        // Add highlight background color
        attributedString.addAttribute(.backgroundColor, 
                                     value: UIColor.yellow.withAlphaComponent(0.3), 
                                     range: range)
        
        // Add annotation ID as link attribute for tap detection
        // Format: "annotation://<annotation_id>"
        if let annotationURL = URL(string: "annotation://\(annotation.id)") {
            attributedString.addAttribute(.link, value: annotationURL, range: range)
        }
        
        // Optional: Add underline to indicate it's tappable
        attributedString.addAttribute(.underlineStyle, 
                                     value: NSUnderlineStyle.single.rawValue, 
                                     range: range)
    }
    
    return attributedString
}
```

**Important:** Make sure your `UITextView` has:
- `isEditable = false` (so users can't edit)
- `isSelectable = true` (so taps are detected)
- `delegate` set to handle tap events

#### 4. Display Annotations Immediately After Answering

```swift
class PassageViewController: UIViewController {
    @IBOutlet weak var passageTextView: UITextView!
    
    var passage: Passage?
    var allAnnotations: [PassageAnnotation] = []  // Accumulate annotations as questions are answered
    var annotationsByID: [String: PassageAnnotation] = [:]  // Map annotation ID to annotation object
    
    override func viewDidLoad() {
        super.viewDidLoad()
        passageTextView.delegate = self
        passageTextView.isEditable = false
        passageTextView.isSelectable = true
    }
    
    func answerQuestion(questionId: String, optionIndex: Int) {
        submitAnswer(questionId: questionId, optionIndex: optionIndex) { [weak self] result in
            switch result {
            case .success(let answer):
                // Add new annotations to our collection
                self?.allAnnotations.append(contentsOf: answer.annotations)
                
                // Update annotation lookup map
                for annotation in answer.annotations {
                    self?.annotationsByID[annotation.id] = annotation
                }
                
                // Immediately update the passage text with new annotations
                self?.updatePassageWithAnnotations()
                
                // Show feedback (correct/incorrect)
                self?.showAnswerFeedback(answer: answer)
                
            case .failure(let error):
                print("Error submitting answer: \(error)")
            }
        }
    }
    
    func updatePassageWithAnnotations() {
        guard let passageContent = passage?.content else { return }
        
        // Apply all accumulated annotations to passage text
        let attributedText = applyAnnotations(to: passageContent, annotations: allAnnotations)
        passageTextView.attributedText = attributedText
    }
    
    func loadExistingAnswers() {
        guard let passageId = passage?.id else { return }
        
        // Load all previously answered questions and their annotations
        fetchAnswers(for: passageId) { [weak self] result in
            switch result {
            case .success(let answers):
                // Collect all annotations from all answers
                let annotations = answers.flatMap { $0.annotations }
                self?.allAnnotations = annotations
                
                // Update annotation lookup map
                for annotation in annotations {
                    self?.annotationsByID[annotation.id] = annotation
                }
                
                self?.updatePassageWithAnnotations()
            case .failure(let error):
                print("Error loading answers: \(error)")
            }
        }
    }
    
    func showAnnotationExplanation(_ annotation: PassageAnnotation) {
        // Create and show popup/alert with explanation
        let alert = UIAlertController(
            title: "Explanation",
            message: annotation.explanation,
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
        
        // Alternative: Show in a custom popup view
        // showCustomAnnotationPopup(annotation: annotation)
    }
}

// MARK: - UITextViewDelegate
extension PassageViewController: UITextViewDelegate {
    func textView(_ textView: UITextView, shouldInteractWith URL: URL, in characterRange: NSRange, interaction: UITextItemInteraction) -> Bool {
        // Check if this is an annotation link
        if URL.scheme == "annotation" {
            let annotationID = URL.host ?? ""
            
            // Find the annotation
            if let annotation = annotationsByID[annotationID] {
                showAnnotationExplanation(annotation)
            }
            
            return false  // Don't open the URL, we handled it
        }
        
        return true  // Allow default handling for other URLs
    }
}
```

**Key Implementation Details:**
- Set `passageTextView.delegate = self` to handle taps
- Store annotations in a dictionary (`annotationsByID`) for quick lookup
- Implement `textView(_:shouldInteractWith:in:interaction:)` to intercept annotation taps
- Check for `URL.scheme == "annotation"` to identify annotation links
- Extract annotation ID from URL and show explanation

### React/Web Implementation

```javascript
function ReviewView({ passageId }) {
  const [reviewData, setReviewData] = useState(null);
  
  useEffect(() => {
    fetch(`/api/v1/progress/passages/${passageId}/review`, {
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`
      }
    })
    .then(r => r.json())
    .then(data => setReviewData(data));
  }, [passageId]);
  
  const renderPassageWithAnnotations = () => {
    if (!reviewData || !reviewData.passage) return null;
    
    // Collect all annotations from all answered questions
    const allAnnotations = reviewData.answers.flatMap(a => a.annotations || []);
    
    // Sort by start position
    const sortedAnnotations = [...allAnnotations].sort((a, b) => a.start_char - b.start_char);
    
    const parts = [];
    let lastIndex = 0;
    
    sortedAnnotations.forEach((annotation) => {
      // Add text before annotation
      if (annotation.start_char > lastIndex) {
        parts.push({
          text: reviewData.passage.content.substring(lastIndex, annotation.start_char),
          isAnnotation: false
        });
      }
      
      // Add annotated text
      parts.push({
        text: reviewData.passage.content.substring(annotation.start_char, annotation.end_char),
        isAnnotation: true,
        annotation: annotation
      });
      
      lastIndex = annotation.end_char;
    });
    
    // Add remaining text
    if (lastIndex < reviewData.passage.content.length) {
      parts.push({
        text: reviewData.passage.content.substring(lastIndex),
        isAnnotation: false
      });
    }
    
    return (
      <div>
        {parts.map((part, idx) => (
          part.isAnnotation ? (
            <span
              key={idx}
              style={{ backgroundColor: '#fff3cd', cursor: 'pointer' }}
              onClick={() => showAnnotationPopup(part.annotation)}
              title={part.annotation.explanation}
            >
              {part.text}
            </span>
          ) : (
            <span key={idx}>{part.text}</span>
          )
        ))}
      </div>
    );
  };
  
  return (
    <div>
      <div>{renderPassageWithAnnotations()}</div>
      <div>
        {reviewData?.answers.map(answer => (
          <QuestionReview key={answer.question_id} answer={answer} />
        ))}
      </div>
    </div>
  );
}
```

---

## Character Index Calculation

### How Character Indices Work

```
Example Passage:
"The quick brown fox jumps over the lazy dog."

Character positions:
0: T
1: h
2: e
3: (space)
4: q
5: u
6: i
7: c
8: k
...

To highlight "quick" (characters 4-8):
start_char: 4
end_char: 9  // Exclusive, so 9 is after 'k'
```

### Swift String Indexing

```swift
let text = "The quick brown fox"
let startIndex = text.index(text.startIndex, offsetBy: 4)  // 'q'
let endIndex = text.index(text.startIndex, offsetBy: 9)    // after 'k'
let selected = String(text[startIndex..<endIndex])  // "quick"
```

**Note**: Swift's `String.Index` is different from integer indices. You'll need to convert:

```swift
func getRange(from startChar: Int, to endChar: Int, in text: String) -> Range<String.Index>? {
    guard startChar >= 0 && endChar <= text.count && startChar < endChar else {
        return nil
    }
    
    let startIndex = text.index(text.startIndex, offsetBy: startChar)
    let endIndex = text.index(text.startIndex, offsetBy: endChar)
    return startIndex..<endIndex
}
```

---

## UI/UX Recommendations

### Visual Design

1. **Highlight Style**:
   - Use subtle background color (e.g., yellow with 30% opacity)
   - Different colors for different questions (if multiple questions have annotations)
   - Show annotation indicator (icon/badge) on highlighted text

2. **Interaction**:
   - **Tap/click on highlighted text shows explanation** ⚠️ **REQUIRED**
   - Show explanation in popup, tooltip, or sidebar
   - Group annotations by question if multiple questions have them
   - **Implementation:** Use `UITextViewDelegate.textView(_:shouldInteractWith:in:interaction:)` to detect taps on annotation links

3. **Display Timing**:
   - **Before answering**: No annotations visible
   - **After answering**: Annotations appear for that question
   - **During review**: All annotations for answered questions visible

### Example UI Patterns

**Pattern 1: Inline Popup** (Recommended for iOS)
- User taps highlighted text
- Small popup/alert appears with explanation
- Shows explanation text from `annotation.explanation`
- Dismisses on tap outside or "OK" button
- **Implementation:** Use `UIAlertController` or custom popup view

**Pattern 2: Question-Linked Display**
- Show annotations grouped by question
- Tapping annotation scrolls to and highlights text
- Tapping highlighted text shows full explanation

**Pattern 3: Progressive Reveal**
- After answering question 1, annotations for Q1 appear
- After answering question 2, annotations for Q2 appear
- All annotations remain visible during review

---

## API Integration Example

### Complete Flow

```swift
// 1. User reads passage (no annotations)
loadPassage(id: passageId) { passage in
    displayPassage(passage)  // No annotations yet
    loadExistingAnswers()  // Load any previously answered questions with their annotations
}

// 2. User answers Question 1
submitAnswer(questionId: q1, optionIndex: 2) { answer in
    // Annotations for Q1 are AUTOMATICALLY in answer.annotations
    // No separate API call needed!
    applyAnnotationsToPassage(answer.annotations)
    showFeedback(answer: answer)
}

// 3. User answers Question 2
submitAnswer(questionId: q2, optionIndex: 1) { answer in
    // Annotations for Q2 are AUTOMATICALLY in answer.annotations
    // Add them to existing annotations and update passage
    allAnnotations.append(contentsOf: answer.annotations)
    applyAnnotationsToPassage(allAnnotations)
    showFeedback(answer: answer)
}

// 4. Continue for all questions...
// Annotations accumulate as each question is answered
// Each answer response includes annotations automatically
```

**Key Points:**
- ✅ Annotations are **automatically included** in every answer submission response
- ✅ No separate API call needed to fetch annotations
- ✅ Just use `answer.annotations` from the response
- ✅ Empty array `[]` if no annotations exist for that question

### Error Handling

```swift
func fetchReview(for passageId: String, completion: @escaping (Result<ReviewResponse, Error>) -> Void) {
    // ... make request ...
    
    if httpResponse.statusCode == 403 {
        // Premium required - show upgrade prompt
        completion(.failure(AnnotationError.premiumRequired))
    } else if httpResponse.statusCode == 404 {
        // Passage not found
        completion(.failure(AnnotationError.notFound))
    } else if httpResponse.statusCode == 401 {
        // Token expired - refresh and retry
        AuthService.shared.refreshToken { result in
            if case .success = result {
                fetchReview(for: passageId, completion: completion)
            } else {
                completion(.failure(AnnotationError.notAuthenticated))
            }
        }
    }
}
```

---

## Testing

### Test Data

Create a test passage with annotations:

**Passage Content:**
```
"The quick brown fox jumps over the lazy dog. Phrenology was a pseudoscience."
```

**Question 1:** "What does the author say about phrenology?"
**Annotation for Q1:**
- `start_char: 52, end_char: 61` → "Phrenology"
- `question_id: <Q1_ID>`

**Question 2:** "What animal is mentioned?"
**Annotation for Q2:**
- `start_char: 4, end_char: 9` → "quick"
- `question_id: <Q2_ID>`

### Verification

1. Answer Q1 → Only Q1 annotation appears
2. Answer Q2 → Both Q1 and Q2 annotations appear
3. Review page → All annotations for answered questions visible
4. Verify character positions match selected text

---

## Best Practices

1. **Sort annotations** by `start_char` before applying
2. **Validate ranges** before applying to avoid crashes
3. **Handle edge cases**: annotations at start/end of text
4. **Performance**: For long passages with many annotations, consider lazy loading
5. **Accessibility**: Ensure annotations are accessible to screen readers
6. **Progressive reveal**: Show annotations only after questions are answered
7. **Group by question**: If multiple questions have annotations, consider visual grouping

---

## Quick Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique annotation ID |
| `question_id` | UUID \| null | Associated question ID (null = general) |
| `start_char` | Integer | 0-based start position |
| `end_char` | Integer | 0-based end position (exclusive) |
| `selected_text` | String | The selected text (for reference) |
| `explanation` | String | Explanation/comment |
| `order` | Integer | Display order |

**Endpoints:**
- `POST /api/v1/answers` - Submit answer, **annotations automatically included in response**
- `GET /api/v1/answers/passage/{passage_id}` - Get all answers, **annotations automatically included**
- `GET /api/v1/passages/{passage_id}/annotations` - Get all annotations for answered questions (optional, if needed)
- `GET /api/v1/progress/passages/{passage_id}/review` - Get review data with annotations

**Key Behavior:**
- ✅ **Annotations are automatically included** in answer submission responses - no separate API call needed
- ✅ Annotations only appear **after** answering the associated question
- ✅ Annotations are on passage text but **tied to questions**
- ✅ Character indices are 0-based, `end_char` is exclusive
- ✅ Annotations array is always present (empty `[]` if none exist)

**Implementation Note:**
When submitting an answer via `POST /api/v1/answers`, the response includes an `annotations` array. Simply use this array to highlight text on the passage - no additional API calls required!

**⚠️ CRITICAL: Tap Handling**
- Annotations are highlighted with a link attribute (`annotation://<id>`)
- You **MUST** implement `UITextViewDelegate.textView(_:shouldInteractWith:in:interaction:)` to handle taps
- When user taps highlighted text, extract the annotation ID from the URL and show `annotation.explanation`
- Without this implementation, taps will do nothing!
