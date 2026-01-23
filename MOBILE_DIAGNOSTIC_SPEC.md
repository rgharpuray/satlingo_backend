# Mobile Diagnostic Rendering & Navigation Spec

This spec shows mobile apps (iOS/Android) how to get, render, and navigate to diagnostic tests.

---

## 1. API Endpoint

**GET `/api/v1/profile`**

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user": { ... },
  "study_plan": {
    "reading": {
      "diagnostic_completed": false,
      "diagnostic_passage_id": "uuid-here",  // null if not set
      "diagnostic_passage_title": "Reading Diagnostic Test",  // null if not set
      "diagnostic_type": "passage",
      "strengths": [],
      "weaknesses": []
    },
    "writing": {
      "diagnostic_completed": false,
      "diagnostic_lesson_id": "uuid-here",  // null if not set
      "diagnostic_lesson_title": "Writing Diagnostic Test",  // null if not set
      "diagnostic_type": "lesson",
      "strengths": [],
      "weaknesses": []
    },
    "math": {
      "diagnostic_completed": true,
      "diagnostic_lesson_id": "uuid-here",  // null if not set
      "diagnostic_lesson_title": "Math Diagnostic Test",  // null if not set
      "diagnostic_type": "lesson",
      "strengths": [...],
      "weaknesses": [...]
    }
  }
}
```

---

## 2. Data Models

### iOS (Swift)

```swift
struct CategoryPlan: Codable {
    let diagnosticCompleted: Bool
    let diagnosticPassageId: UUID?  // For reading
    let diagnosticLessonId: UUID?   // For writing/math
    let diagnosticPassageTitle: String?  // For reading
    let diagnosticLessonTitle: String?  // For writing/math
    let diagnosticType: String  // "passage" or "lesson"
    let strengths: [SkillPerformance]
    let weaknesses: [SkillPerformance]
    
    enum CodingKeys: String, CodingKey {
        case strengths, weaknesses
        case diagnosticCompleted = "diagnostic_completed"
        case diagnosticPassageId = "diagnostic_passage_id"
        case diagnosticLessonId = "diagnostic_lesson_id"
        case diagnosticPassageTitle = "diagnostic_passage_title"
        case diagnosticLessonTitle = "diagnostic_lesson_title"
        case diagnosticType = "diagnostic_type"
    }
    
    // Helper computed properties
    var diagnosticId: UUID? {
        return diagnosticType == "passage" ? diagnosticPassageId : diagnosticLessonId
    }
    
    var diagnosticTitle: String? {
        return diagnosticType == "passage" ? diagnosticPassageTitle : diagnosticLessonTitle
    }
    
    var isAvailable: Bool {
        return diagnosticId != nil
    }
}
```

### Android (Kotlin)

```kotlin
data class CategoryPlan(
    @SerializedName("diagnostic_completed") val diagnosticCompleted: Boolean,
    @SerializedName("diagnostic_passage_id") val diagnosticPassageId: String?,
    @SerializedName("diagnostic_lesson_id") val diagnosticLessonId: String?,
    @SerializedName("diagnostic_passage_title") val diagnosticPassageTitle: String?,
    @SerializedName("diagnostic_lesson_title") val diagnosticLessonTitle: String?,
    @SerializedName("diagnostic_type") val diagnosticType: String,
    val strengths: List<SkillPerformance>,
    val weaknesses: List<SkillPerformance>
) {
    val diagnosticId: String?
        get() = if (diagnosticType == "passage") diagnosticPassageId else diagnosticLessonId
    
    val diagnosticTitle: String?
        get() = if (diagnosticType == "passage") diagnosticPassageTitle else diagnosticLessonTitle
    
    val isAvailable: Boolean
        get() = diagnosticId != null
}
```

---

## 3. UI Rendering Logic

### Status Determination

For each category (reading, writing, math), determine status:

```swift
// iOS
enum DiagnosticStatus {
    case notAvailable      // diagnosticId is nil
    case notStarted        // diagnosticId exists, diagnosticCompleted == false
    case completed         // diagnosticId exists, diagnosticCompleted == true
}

func getDiagnosticStatus(for categoryPlan: CategoryPlan?) -> DiagnosticStatus {
    guard let plan = categoryPlan else { return .notAvailable }
    
    if !plan.isAvailable {
        return .notAvailable
    }
    
    if plan.diagnosticCompleted {
        return .completed
    }
    
    return .notStarted
}
```

```kotlin
// Android
enum class DiagnosticStatus {
    NOT_AVAILABLE,  // diagnosticId is null
    NOT_STARTED,    // diagnosticId exists, diagnosticCompleted == false
    COMPLETED       // diagnosticId exists, diagnosticCompleted == true
}

fun getDiagnosticStatus(categoryPlan: CategoryPlan?): DiagnosticStatus {
    if (categoryPlan == null || !categoryPlan.isAvailable) {
        return DiagnosticStatus.NOT_AVAILABLE
    }
    
    return if (categoryPlan.diagnosticCompleted) {
        DiagnosticStatus.COMPLETED
    } else {
        DiagnosticStatus.NOT_STARTED
    }
}
```

### Display Text

```swift
// iOS
func getDiagnosticDisplayText(for categoryPlan: CategoryPlan?) -> String {
    let status = getDiagnosticStatus(for: categoryPlan)
    
    switch status {
    case .notAvailable:
        return "Not Available"
    case .notStarted:
        return "Not Started"
    case .completed:
        return "Completed"
    }
}
```

```kotlin
// Android
fun getDiagnosticDisplayText(categoryPlan: CategoryPlan?): String {
    return when (getDiagnosticStatus(categoryPlan)) {
        DiagnosticStatus.NOT_AVAILABLE -> "Not Available"
        DiagnosticStatus.NOT_STARTED -> "Not Started"
        DiagnosticStatus.COMPLETED -> "Completed"
    }
}
```

### Button/Action Visibility

```swift
// iOS
func shouldShowStartButton(for categoryPlan: CategoryPlan?) -> Bool {
    let status = getDiagnosticStatus(for: categoryPlan)
    return status == .notStarted
}

func shouldShowRetakeButton(for categoryPlan: CategoryPlan?) -> Bool {
    let status = getDiagnosticStatus(for: categoryPlan)
    return status == .completed
}
```

```kotlin
// Android
fun shouldShowStartButton(categoryPlan: CategoryPlan?): Boolean {
    return getDiagnosticStatus(categoryPlan) == DiagnosticStatus.NOT_STARTED
}

fun shouldShowRetakeButton(categoryPlan: CategoryPlan?): Boolean {
    return getDiagnosticStatus(categoryPlan) == DiagnosticStatus.COMPLETED
}
```

---

## 4. Navigation Logic

### iOS (SwiftUI)

```swift
import SwiftUI

struct DiagnosticCard: View {
    let category: String  // "reading", "writing", or "math"
    let categoryPlan: CategoryPlan?
    @EnvironmentObject var navigationCoordinator: NavigationCoordinator
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(category.capitalized)
                    .font(.headline)
                Spacer()
                Text(getDiagnosticDisplayText(for: categoryPlan))
                    .font(.subheadline)
                    .foregroundColor(statusColor)
            }
            
            if let plan = categoryPlan, plan.isAvailable {
                if shouldShowStartButton(for: plan) {
                    Button(action: {
                        navigateToDiagnostic(plan)
                    }) {
                        Text("Start Diagnostic")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                } else if shouldShowRetakeButton(for: plan) {
                    Button(action: {
                        navigateToDiagnostic(plan)
                    }) {
                        Text("Retake Diagnostic")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }
    
    private var statusColor: Color {
        let status = getDiagnosticStatus(for: categoryPlan)
        switch status {
        case .notAvailable: return .gray
        case .notStarted: return .orange
        case .completed: return .green
        }
    }
    
    private func navigateToDiagnostic(_ plan: CategoryPlan) {
        guard let diagnosticId = plan.diagnosticId else { return }
        
        if plan.diagnosticType == "passage" {
            // Navigate to passage detail screen
            navigationCoordinator.navigateToPassage(id: diagnosticId)
        } else {
            // Navigate to lesson detail screen
            navigationCoordinator.navigateToLesson(id: diagnosticId)
        }
    }
}
```

### iOS (UIKit)

```swift
class DiagnosticViewController: UIViewController {
    var categoryPlan: CategoryPlan?
    
    @IBAction func startDiagnosticTapped(_ sender: UIButton) {
        guard let plan = categoryPlan,
              let diagnosticId = plan.diagnosticId else { return }
        
        if plan.diagnosticType == "passage" {
            // Navigate to passage
            let passageVC = PassageDetailViewController(passageId: diagnosticId)
            navigationController?.pushViewController(passageVC, animated: true)
        } else {
            // Navigate to lesson
            let lessonVC = LessonDetailViewController(lessonId: diagnosticId)
            navigationController?.pushViewController(lessonVC, animated: true)
        }
    }
}
```

### Android (Jetpack Compose)

```kotlin
@Composable
fun DiagnosticCard(
    category: String,
    categoryPlan: CategoryPlan?,
    onNavigateToPassage: (String) -> Unit,
    onNavigateToLesson: (String) -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = category.replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.headlineSmall
                )
                Text(
                    text = getDiagnosticDisplayText(categoryPlan),
                    style = MaterialTheme.typography.bodyMedium,
                    color = getStatusColor(categoryPlan)
                )
            }
            
            categoryPlan?.let { plan ->
                if (plan.isAvailable) {
                    when (getDiagnosticStatus(plan)) {
                        DiagnosticStatus.NOT_STARTED -> {
                            Button(
                                onClick = { navigateToDiagnostic(plan, onNavigateToPassage, onNavigateToLesson) },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Start Diagnostic")
                            }
                        }
                        DiagnosticStatus.COMPLETED -> {
                            OutlinedButton(
                                onClick = { navigateToDiagnostic(plan, onNavigateToPassage, onNavigateToLesson) },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Retake Diagnostic")
                            }
                        }
                        DiagnosticStatus.NOT_AVAILABLE -> {
                            // No button shown
                        }
                    }
                }
            }
        }
    }
}

private fun navigateToDiagnostic(
    plan: CategoryPlan,
    onNavigateToPassage: (String) -> Unit,
    onNavigateToLesson: (String) -> Unit
) {
    val diagnosticId = plan.diagnosticId ?: return
    
    if (plan.diagnosticType == "passage") {
        onNavigateToPassage(diagnosticId)
    } else {
        onNavigateToLesson(diagnosticId)
    }
}

@Composable
private fun getStatusColor(categoryPlan: CategoryPlan?): Color {
    return when (getDiagnosticStatus(categoryPlan)) {
        DiagnosticStatus.NOT_AVAILABLE -> Color.Gray
        DiagnosticStatus.NOT_STARTED -> Color(0xFFFF9800) // Orange
        DiagnosticStatus.COMPLETED -> Color(0xFF4CAF50) // Green
    }
}
```

### Android (Traditional Views)

```kotlin
class DiagnosticCardView(context: Context) : LinearLayout(context) {
    private lateinit var statusText: TextView
    private lateinit var actionButton: Button
    
    fun bind(categoryPlan: CategoryPlan?) {
        val status = getDiagnosticStatus(categoryPlan)
        
        statusText.text = getDiagnosticDisplayText(categoryPlan)
        statusText.setTextColor(getStatusColor(status))
        
        if (categoryPlan?.isAvailable == true && status == DiagnosticStatus.NOT_STARTED) {
            actionButton.visibility = View.VISIBLE
            actionButton.text = "Start Diagnostic"
            actionButton.setOnClickListener {
                navigateToDiagnostic(categoryPlan)
            }
        } else if (categoryPlan?.isAvailable == true && status == DiagnosticStatus.COMPLETED) {
            actionButton.visibility = View.VISIBLE
            actionButton.text = "Retake Diagnostic"
            actionButton.setOnClickListener {
                navigateToDiagnostic(categoryPlan)
            }
        } else {
            actionButton.visibility = View.GONE
        }
    }
    
    private fun navigateToDiagnostic(plan: CategoryPlan) {
        val diagnosticId = plan.diagnosticId ?: return
        
        val intent = if (plan.diagnosticType == "passage") {
            Intent(context, PassageDetailActivity::class.java).apply {
                putExtra("PASSAGE_ID", diagnosticId)
            }
        } else {
            Intent(context, LessonDetailActivity::class.java).apply {
                putExtra("LESSON_ID", diagnosticId)
            }
        }
        
        context.startActivity(intent)
    }
}
```

---

## 5. Complete Profile Screen Example

### iOS (SwiftUI)

```swift
struct ProfileView: View {
    @StateObject private var viewModel = ProfileViewModel()
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // User info section...
                    
                    // Diagnostic Progress Section
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Diagnostic Progress")
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        DiagnosticCard(
                            category: "Reading",
                            categoryPlan: viewModel.studyPlan?.reading
                        )
                        
                        DiagnosticCard(
                            category: "Writing",
                            categoryPlan: viewModel.studyPlan?.writing
                        )
                        
                        DiagnosticCard(
                            category: "Math",
                            categoryPlan: viewModel.studyPlan?.math
                        )
                    }
                    .padding()
                }
            }
            .navigationTitle("Profile")
            .onAppear {
                viewModel.loadProfile()
            }
        }
    }
}

class ProfileViewModel: ObservableObject {
    @Published var studyPlan: StudyPlan?
    
    func loadProfile() {
        // Call GET /api/v1/profile
        // Parse response into StudyPlan
        // Update studyPlan property
    }
}
```

### Android (Jetpack Compose)

```kotlin
@Composable
fun ProfileScreen(
    viewModel: ProfileViewModel = viewModel()
) {
    val studyPlan by viewModel.studyPlan.collectAsState()
    
    LaunchedEffect(Unit) {
        viewModel.loadProfile()
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // User info section...
        
        Text(
            text = "Diagnostic Progress",
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(vertical = 8.dp)
        )
        
        DiagnosticCard(
            category = "Reading",
            categoryPlan = studyPlan?.reading,
            onNavigateToPassage = { id -> /* Navigate */ },
            onNavigateToLesson = { id -> /* Navigate */ }
        )
        
        DiagnosticCard(
            category = "Writing",
            categoryPlan = studyPlan?.writing,
            onNavigateToPassage = { id -> /* Navigate */ },
            onNavigateToLesson = { id -> /* Navigate */ }
        )
        
        DiagnosticCard(
            category = "Math",
            categoryPlan = studyPlan?.math,
            onNavigateToPassage = { id -> /* Navigate */ },
            onNavigateToLesson = { id -> /* Navigate */ }
        )
    }
}
```

---

## 6. API Integration

### iOS (URLSession)

```swift
class APIService {
    func fetchProfile() async throws -> ProfileResponse {
        guard let token = AuthManager.shared.token else {
            throw APIError.unauthorized
        }
        
        var request = URLRequest(url: URL(string: "\(baseURL)/api/v1/profile")!)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        return try JSONDecoder().decode(ProfileResponse.self, from: data)
    }
}
```

### Android (Retrofit)

```kotlin
interface ApiService {
    @GET("api/v1/profile")
    suspend fun getProfile(
        @Header("Authorization") token: String
    ): ProfileResponse
}

// Usage
val response = apiService.getProfile("Bearer $token")
val studyPlan = response.studyPlan
```

---

## 7. Navigation Routes

### iOS Navigation

```swift
// Using NavigationStack (iOS 16+)
NavigationStack {
    // Your views
}
.onChange(of: selectedDiagnosticId) { id in
    if let id = id {
        path.append(Destination.passage(id))
        // or
        path.append(Destination.lesson(id))
    }
}

// Using NavigationLink
NavigationLink(value: Destination.passage(diagnosticId)) {
    Text("Start Diagnostic")
}
```

### Android Navigation

```kotlin
// Using Jetpack Navigation
val navController = rememberNavController()

navController.navigate(
    route = "passage/$diagnosticId"
    // or
    route = "lesson/$diagnosticId"
)

// In your NavGraph
composable("passage/{passageId}") { backStackEntry ->
    val passageId = backStackEntry.arguments?.getString("passageId") ?: return@composable
    PassageDetailScreen(passageId = passageId)
}

composable("lesson/{lessonId}") { backStackEntry ->
    val lessonId = backStackEntry.arguments?.getString("lessonId") ?: return@composable
    LessonDetailScreen(lessonId = lessonId)
}
```

---

## 8. Summary Checklist

✅ **Data Fetching:**
- Call `GET /api/v1/profile` with Bearer token
- Parse `study_plan.reading`, `study_plan.writing`, `study_plan.math`

✅ **Status Determination:**
- `diagnosticId == null` → "Not Available"
- `diagnosticId != null && diagnosticCompleted == false` → "Not Started"
- `diagnosticId != null && diagnosticCompleted == true` → "Completed"

✅ **UI Rendering:**
- Show status text with appropriate color
- Show "Start Diagnostic" button when status is "Not Started"
- Show "Retake Diagnostic" button when status is "Completed"
- Hide button when status is "Not Available"

✅ **Navigation:**
- If `diagnosticType == "passage"` → Navigate to passage detail with `diagnosticPassageId`
- If `diagnosticType == "lesson"` → Navigate to lesson detail with `diagnosticLessonId`

✅ **Error Handling:**
- Handle null values gracefully
- Show "Not Available" when diagnostic is not set in backend
- Handle network errors when fetching profile

---

## 9. Testing

Test these scenarios:

1. **No diagnostics set** → All show "Not Available"
2. **Diagnostics set but not started** → Show "Not Started" with "Start" button
3. **Diagnostics completed** → Show "Completed" with "Retake" button
4. **Mixed states** → Each category shows correct status independently
5. **Navigation** → Tapping button navigates to correct passage/lesson screen

---

This spec provides everything needed to implement diagnostic rendering and navigation in mobile apps!
