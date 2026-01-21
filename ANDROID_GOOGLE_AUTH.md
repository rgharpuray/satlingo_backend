# Android Google Sign-In Integration

## Android Client ID
```
412415832820-kdps9c4s09r15fvp42rcbini75ptslu7.apps.googleusercontent.com
```

## Endpoint

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

## Kotlin Implementation

### 1. Add Dependencies

In `build.gradle.kts` (app level):
```kotlin
dependencies {
    implementation("com.google.android.gms:play-services-auth:21.0.0")
}
```

### 2. Configure Google Sign-In

In your Application or Activity:

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

### 3. Sign In Flow

In your Activity:

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

### 4. API Service (Retrofit)

```kotlin
interface AuthService {
    @POST("api/v1/auth/google/token")
    suspend fun googleToken(@Body request: GoogleTokenRequest): Response<AuthResponse>
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

### 5. API Client Setup

```kotlin
object ApiClient {
    private const val BASE_URL = "https://keuvi.herokuapp.com/"
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val authService: AuthService = retrofit.create(AuthService::class.java)
}
```

### 6. Token Storage

```kotlin
object TokenManager {
    private lateinit var prefs: SharedPreferences
    
    fun init(context: Context) {
        prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
    }
    
    fun saveTokens(accessToken: String, refreshToken: String) {
        prefs.edit()
            .putString("access_token", accessToken)
            .putString("refresh_token", refreshToken)
            .apply()
    }
    
    fun getAccessToken(): String? = prefs.getString("access_token", null)
    fun getRefreshToken(): String? = prefs.getString("refresh_token", null)
    
    fun clearTokens() {
        prefs.edit().clear().apply()
    }
}
```

## That's It

1. User taps "Sign in with Google"
2. Google SDK shows sign-in UI
3. SDK returns ID token
4. Send token to `POST /api/v1/auth/google/token`
5. Backend returns JWT tokens + user info
6. Store tokens, user is logged in

---

**Same endpoint as iOS** - both platforms use `POST /api/v1/auth/google/token` with the same request/response format.
