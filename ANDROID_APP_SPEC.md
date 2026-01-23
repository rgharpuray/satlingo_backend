# Android App Integration Spec

Complete guide for integrating the Keuvi backend with an Android app, including authentication, payments, diagnostics, and account management.

---

## Table of Contents

1. [Authentication](#1-authentication)
   - [Google Sign-In](#google-sign-in)
   - [Account Deletion](#account-deletion)
2. [Payments (Stripe)](#2-payments-stripe)
3. [Diagnostic Tests](#3-diagnostic-tests)
   - [API Endpoint](#api-endpoint)
   - [Data Models](#data-models)
   - [UI Rendering](#ui-rendering)
   - [Navigation](#navigation)
4. [API Base URL](#4-api-base-url)

---

## 1. Authentication

### Google Sign-In

**Android Client ID:**
```
412415832820-kdps9c4s09r15fvp42rcbini75ptslu7.apps.googleusercontent.com
```

**Endpoint:**
```
POST /api/v1/auth/google/token
Content-Type: application/json

{
  "id_token": "<google_id_token_from_sdk>"
}
```

**Response (200):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "user",
    "is_premium": false
  },
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

#### Implementation

**1. Dependencies:**
```kotlin
// build.gradle.kts (app)
dependencies {
    implementation("com.google.android.gms:play-services-auth:21.0.0")
}
```

**2. Google Sign-In Setup:**
```kotlin
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException

class AuthManager(private val context: Context) {
    
    private val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
        .requestIdToken("412415832820-kdps9c4s09r15fvp42rcbini75ptslu7.apps.googleusercontent.com")
        .requestEmail()
        .build()
    
    val googleSignInClient: GoogleSignInClient = GoogleSignIn.getClient(context, gso)
    
    fun getSignInIntent() = googleSignInClient.signInIntent
}
```

**3. Sign-In Flow:**
```kotlin
class LoginActivity : AppCompatActivity() {
    
    private lateinit var authManager: AuthManager
    private val signInLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        handleSignInResult(result.data)
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        authManager = AuthManager(this)
        
        findViewById<Button>(R.id.googleSignInButton).setOnClickListener {
            signInWithGoogle()
        }
    }
    
    private fun signInWithGoogle() {
        signInLauncher.launch(authManager.getSignInIntent())
    }
    
    private fun handleSignInResult(data: Intent?) {
        val task = GoogleSignIn.getSignedInAccountFromIntent(data)
        try {
            val account = task.getResult(ApiException::class.java)
            val idToken = account.idToken
            
            if (idToken != null) {
                verifyWithBackend(idToken)
            } else {
                showError("No ID token received")
            }
        } catch (e: ApiException) {
            showError("Sign-in failed: ${e.statusCode}")
        }
    }
    
    private fun verifyWithBackend(idToken: String) {
        lifecycleScope.launch {
            try {
                val response = ApiClient.authService.googleToken(
                    GoogleTokenRequest(idToken)
                )
                
                if (response.isSuccessful) {
                    val authResponse = response.body()!!
                    
                    // Store tokens
                    TokenManager.saveTokens(
                        accessToken = authResponse.tokens.access,
                        refreshToken = authResponse.tokens.refresh
                    )
                    
                    // Navigate to main screen
                    startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    finish()
                } else {
                    showError("Auth failed: ${response.code()}")
                }
            } catch (e: Exception) {
                showError("Network error: ${e.message}")
            }
        }
    }
}
```

**4. API Service:**
```kotlin
interface AuthService {
    @POST("api/v1/auth/google/token")
    suspend fun googleToken(@Body request: GoogleTokenRequest): Response<AuthResponse>
    
    @DELETE("api/v1/auth/delete-account")
    suspend fun deleteAccount(@Header("Authorization") token: String): Response<Unit>
}

data class GoogleTokenRequest(
    @SerializedName("id_token") val idToken: String
)

data class AuthResponse(
    val user: User,
    val tokens: Tokens
)

data class User(
    val id: String,
    val email: String,
    val username: String,
    @SerializedName("is_premium") val isPremium: Boolean
)

data class Tokens(
    val access: String,
    val refresh: String
)
```

---

### Account Deletion

**Endpoint:**
```
DELETE /api/v1/auth/delete-account
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{}
```

**What it does:**
- Cancels all active subscriptions (Stripe and App Store)
- Deletes all user data (attempts, progress, answers, etc.)
- Invalidates all refresh tokens
- Logs the deletion

**Note:** This endpoint is required by Apple App Store Guideline 5.1.1(v) for account deletion. Android apps should also provide this functionality.

#### Implementation

```kotlin
class AccountManager(private val context: Context) {
    
    private val apiClient = ApiClient.instance
    
    /**
     * Delete user account and all associated data.
     * This will cancel subscriptions and delete all user data.
     */
    suspend fun deleteAccount(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val token = TokenManager.getAccessToken()
                ?: return@withContext Result.failure(Exception("Not logged in"))
            
            val response = apiClient.authService.deleteAccount("Bearer $token")
            
            if (response.isSuccessful) {
                // Clear local data
                TokenManager.clearTokens()
                UserPreferences.clear()
                
                Result.success(Unit)
            } else {
                val errorMessage = when (response.code()) {
                    401 -> "Please log in to delete your account"
                    500 -> "Server error. Please try again later"
                    else -> "Failed to delete account (${response.code()})"
                }
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Network error: ${e.message}"))
        }
    }
}
```

**UI Implementation:**
```kotlin
@Composable
fun AccountSettingsScreen(
    accountManager: AccountManager,
    onAccountDeleted: () -> Unit
) {
    var showDeleteDialog by remember { mutableStateOf(false) }
    var isDeleting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Other settings...
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Delete Account Button
        Button(
            onClick = { showDeleteDialog = true },
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.error
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Delete Account")
        }
    }
    
    // Delete Confirmation Dialog
    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete Account") },
            text = {
                Column {
                    Text("Are you sure you want to delete your account?")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "This will permanently delete all your data, including:",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text("• All practice attempts", style = MaterialTheme.typography.bodySmall)
                    Text("• Progress and scores", style = MaterialTheme.typography.bodySmall)
                    Text("• Subscription (will be cancelled)", style = MaterialTheme.typography.bodySmall)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "This action cannot be undone.",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        isDeleting = true
                        CoroutineScope(Dispatchers.Main).launch {
                            accountManager.deleteAccount()
                                .onSuccess {
                                    isDeleting = false
                                    showDeleteDialog = false
                                    onAccountDeleted()
                                }
                                .onFailure {
                                    isDeleting = false
                                    error = it.message
                                }
                        }
                    },
                    enabled = !isDeleting,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    if (isDeleting) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onError
                        )
                    } else {
                        Text("Delete")
                    }
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showDeleteDialog = false },
                    enabled = !isDeleting
                ) {
                    Text("Cancel")
                }
            }
        )
    }
    
    // Error Snackbar
    error?.let {
        LaunchedEffect(it) {
            // Show error snackbar
            SnackbarHost(
                hostState = remember { SnackbarHostState() },
                snackbar = {
                    Snackbar(
                        action = {
                            TextButton(onClick = { error = null }) {
                                Text("Dismiss")
                            }
                        }
                    ) {
                        Text(it)
                    }
                }
            )
        }
    }
}
```

---

## 2. Payments (Stripe)

See `ANDROID_PAYMENTS.md` for complete Stripe integration details.

**Quick Summary:**
- **Checkout:** `POST /api/v1/payments/checkout` → Opens Stripe Checkout in Custom Tab
- **Status:** `GET /api/v1/payments/subscription` → Get subscription status
- **Portal:** `POST /api/v1/payments/portal` → Open Customer Portal to manage/cancel
- **Sync:** `POST /api/v1/payments/sync` → Sync subscription status after returning from Stripe

**Key Points:**
- Use Chrome Custom Tabs for checkout/portal
- Handle deep links when returning from Stripe
- Always sync subscription status on app launch
- Premium status remains active until period ends after cancellation

---

## 3. Diagnostic Tests

### API Endpoint

**GET `/api/v1/profile`**

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_premium": false,
    "has_active_subscription": false
  },
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

### Data Models

```kotlin
data class ProfileResponse(
    val user: User,
    @SerializedName("study_plan") val studyPlan: StudyPlan
)

data class StudyPlan(
    val reading: CategoryPlan?,
    val writing: CategoryPlan?,
    val math: CategoryPlan?
)

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

data class SkillPerformance(
    val name: String,
    val correct: Int,
    val total: Int,
    val percentage: Int
)

enum class DiagnosticStatus {
    NOT_AVAILABLE,  // diagnosticId is null
    NOT_STARTED,    // diagnosticId exists, diagnosticCompleted == false
    COMPLETED       // diagnosticId exists, diagnosticCompleted == true
}
```

### UI Rendering

**Status Determination:**
```kotlin
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

fun getDiagnosticDisplayText(categoryPlan: CategoryPlan?): String {
    return when (getDiagnosticStatus(categoryPlan)) {
        DiagnosticStatus.NOT_AVAILABLE -> "Not Available"
        DiagnosticStatus.NOT_STARTED -> "Not Started"
        DiagnosticStatus.COMPLETED -> "Completed"
    }
}

fun shouldShowStartButton(categoryPlan: CategoryPlan?): Boolean {
    return getDiagnosticStatus(categoryPlan) == DiagnosticStatus.NOT_STARTED
}

fun shouldShowRetakeButton(categoryPlan: CategoryPlan?): Boolean {
    return getDiagnosticStatus(categoryPlan) == DiagnosticStatus.COMPLETED
}
```

**Diagnostic Card Component:**
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
                                onClick = { 
                                    navigateToDiagnostic(plan, onNavigateToPassage, onNavigateToLesson) 
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Start Diagnostic")
                            }
                        }
                        DiagnosticStatus.COMPLETED -> {
                            OutlinedButton(
                                onClick = { 
                                    navigateToDiagnostic(plan, onNavigateToPassage, onNavigateToLesson) 
                                },
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

**Profile Screen Example:**
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
            onNavigateToPassage = { id -> 
                // Navigate to passage detail
                navController.navigate("passage/$id")
            },
            onNavigateToLesson = { id -> 
                // Navigate to lesson detail
                navController.navigate("lesson/$id")
            }
        )
        
        DiagnosticCard(
            category = "Writing",
            categoryPlan = studyPlan?.writing,
            onNavigateToPassage = { id -> navController.navigate("passage/$id") },
            onNavigateToLesson = { id -> navController.navigate("lesson/$id") }
        )
        
        DiagnosticCard(
            category = "Math",
            categoryPlan = studyPlan?.math,
            onNavigateToPassage = { id -> navController.navigate("passage/$id") },
            onNavigateToLesson = { id -> navController.navigate("lesson/$id") }
        )
    }
}
```

### Navigation

**Using Jetpack Navigation:**
```kotlin
// In your NavGraph
composable("passage/{passageId}") { backStackEntry ->
    val passageId = backStackEntry.arguments?.getString("passageId") ?: return@composable
    PassageDetailScreen(passageId = passageId)
}

composable("lesson/{lessonId}") { backStackEntry ->
    val lessonId = backStackEntry.arguments?.getString("lessonId") ?: return@composable
    LessonDetailScreen(lessonId = lessonId)
}

// Navigate to diagnostic
navController.navigate("passage/$diagnosticId")
// or
navController.navigate("lesson/$diagnosticId")
```

**Using Traditional Intents:**
```kotlin
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
```

### API Integration

**API Service:**
```kotlin
interface ProfileService {
    @GET("api/v1/profile")
    suspend fun getProfile(
        @Header("Authorization") token: String
    ): Response<ProfileResponse>
}
```

**ViewModel:**
```kotlin
class ProfileViewModel : ViewModel() {
    
    private val _studyPlan = MutableStateFlow<StudyPlan?>(null)
    val studyPlan: StateFlow<StudyPlan?> = _studyPlan.asStateFlow()
    
    fun loadProfile() {
        viewModelScope.launch {
            try {
                val token = TokenManager.getAccessToken()
                    ?: return@launch
                
                val response = ApiClient.profileService.getProfile("Bearer $token")
                
                if (response.isSuccessful) {
                    response.body()?.let {
                        _studyPlan.value = it.studyPlan
                    }
                }
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}
```

### Summary Checklist

✅ **Data Fetching:**
- Call `GET /api/v1/profile` with Bearer token
- Parse `study_plan.reading`, `study_plan.writing`, `study_plan.math`

✅ **Status Determination:**
- `diagnosticId == null` → "Not Available"
- `diagnosticId != null && diagnosticCompleted == false` → "Not Started"
- `diagnosticId != null && diagnosticCompleted == true` → "Completed"

✅ **UI Rendering:**
- Show status text with appropriate color (gray/orange/green)
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

## 4. API Base URL

**Production:**
```
https://keuvi.app/
```

**Development (if needed):**
```
https://keuvi.herokuapp.com/
```

**Local (for testing):**
```
http://10.0.2.2:8000/  // Android Emulator
http://<your-local-ip>:8000/  // Physical device
```

---

## Complete Integration Checklist

### Authentication
- [ ] Google Sign-In implemented
- [ ] Token storage (SharedPreferences or DataStore)
- [ ] Token refresh logic
- [ ] Account deletion implemented

### Payments
- [ ] Stripe checkout flow
- [ ] Subscription status checking
- [ ] Customer portal integration
- [ ] Deep link handling for Stripe returns
- [ ] Subscription sync on app launch

### Diagnostics
- [ ] Profile API integration
- [ ] Diagnostic status rendering
- [ ] Navigation to passages/lessons
- [ ] Error handling

### General
- [ ] API client with authentication headers
- [ ] Error handling for network failures
- [ ] Loading states
- [ ] Offline handling (if applicable)

---

This spec provides everything needed to integrate the Keuvi backend with an Android app!
