# Android Payments (Stripe)

Android apps can use Stripe for subscriptions (Google Play allows external payment processors).

## Endpoints

### 1. Create Checkout Session
```
POST /api/v1/payments/checkout
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Response (200):**
```json
{
  "session_id": "cs_test_...",
  "url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

### 2. Get Subscription Status
```
GET /api/v1/payments/subscription
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "has_subscription": true,
  "status": "active",
  "current_period_end": "2026-02-21T00:00:00Z",
  "cancel_at_period_end": false
}
```

### 3. Open Customer Portal (Manage/Cancel)
```
POST /api/v1/payments/portal
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "url": "https://billing.stripe.com/p/session/..."
}
```

### 4. Sync Subscription (if webhook missed)
```
POST /api/v1/payments/sync
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription synced successfully",
  "subscription_status": "active",
  "is_premium": true
}
```

---

## Kotlin Implementation

### 1. Dependencies

```kotlin
// build.gradle.kts (app)
dependencies {
    implementation("com.stripe:stripe-android:20.37.0")
    implementation("androidx.browser:browser:1.7.0")  // For Custom Tabs
}
```

### 2. Payment Manager

```kotlin
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PaymentManager(private val context: Context) {
    
    private val apiClient = ApiClient.instance
    
    /**
     * Start subscription checkout flow.
     * Opens Stripe Checkout in a Custom Tab (Chrome).
     */
    suspend fun startCheckout(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.createCheckoutSession()
            
            if (response.isSuccessful) {
                val checkoutUrl = response.body()?.url
                    ?: return@withContext Result.failure(Exception("No checkout URL"))
                
                // Open Stripe Checkout in Custom Tab
                withContext(Dispatchers.Main) {
                    val customTabsIntent = CustomTabsIntent.Builder()
                        .setShowTitle(true)
                        .build()
                    customTabsIntent.launchUrl(context, Uri.parse(checkoutUrl))
                }
                
                Result.success(Unit)
            } else {
                Result.failure(Exception("Failed to create checkout: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Get current subscription status.
     */
    suspend fun getSubscriptionStatus(): Result<SubscriptionStatus> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.getSubscriptionStatus()
            
            if (response.isSuccessful) {
                response.body()?.let { Result.success(it) }
                    ?: Result.failure(Exception("Empty response"))
            } else {
                Result.failure(Exception("Failed to get status: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Open customer portal to manage subscription.
     */
    suspend fun openCustomerPortal(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.createPortalSession()
            
            if (response.isSuccessful) {
                val portalUrl = response.body()?.url
                    ?: return@withContext Result.failure(Exception("No portal URL"))
                
                withContext(Dispatchers.Main) {
                    val customTabsIntent = CustomTabsIntent.Builder()
                        .setShowTitle(true)
                        .build()
                    customTabsIntent.launchUrl(context, Uri.parse(portalUrl))
                }
                
                Result.success(Unit)
            } else {
                Result.failure(Exception("Failed to open portal: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Sync subscription status with Stripe.
     * Call this after returning from checkout or portal.
     */
    suspend fun syncSubscription(): Result<SyncResponse> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.syncSubscription()
            
            if (response.isSuccessful) {
                response.body()?.let { 
                    // Update local premium status
                    TokenManager.isPremium = it.isPremium
                    Result.success(it) 
                } ?: Result.failure(Exception("Empty response"))
            } else {
                Result.failure(Exception("Failed to sync: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

### 3. API Service

```kotlin
interface PaymentService {
    
    @POST("api/v1/payments/checkout")
    suspend fun createCheckoutSession(): Response<CheckoutResponse>
    
    @GET("api/v1/payments/subscription")
    suspend fun getSubscriptionStatus(): Response<SubscriptionStatus>
    
    @POST("api/v1/payments/portal")
    suspend fun createPortalSession(): Response<PortalResponse>
    
    @POST("api/v1/payments/sync")
    suspend fun syncSubscription(): Response<SyncResponse>
}

data class CheckoutResponse(
    @SerializedName("session_id") val sessionId: String,
    val url: String
)

data class SubscriptionStatus(
    @SerializedName("has_subscription") val hasSubscription: Boolean,
    val status: String?,
    @SerializedName("current_period_end") val currentPeriodEnd: String?,
    @SerializedName("cancel_at_period_end") val cancelAtPeriodEnd: Boolean?
)

data class PortalResponse(
    val url: String
)

data class SyncResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("subscription_status") val subscriptionStatus: String?,
    @SerializedName("is_premium") val isPremium: Boolean
)
```

### 4. Subscription Screen

```kotlin
@Composable
fun SubscriptionScreen(
    paymentManager: PaymentManager,
    onSubscribed: () -> Unit
) {
    var isLoading by remember { mutableStateOf(false) }
    var subscriptionStatus by remember { mutableStateOf<SubscriptionStatus?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    
    // Load subscription status on launch
    LaunchedEffect(Unit) {
        paymentManager.getSubscriptionStatus()
            .onSuccess { subscriptionStatus = it }
            .onFailure { error = it.message }
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Header
        Text(
            text = "Keuvi Premium",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Benefits
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            BenefitRow("Unlimited practice questions")
            BenefitRow("All passages and lessons")
            BenefitRow("Detailed explanations")
            BenefitRow("Progress tracking")
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Price
        Text(
            text = "$4.99",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "per month",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Subscribe button
        if (subscriptionStatus?.hasSubscription == true) {
            // Already subscribed - show manage button
            Button(
                onClick = {
                    isLoading = true
                    CoroutineScope(Dispatchers.Main).launch {
                        paymentManager.openCustomerPortal()
                            .onFailure { error = it.message }
                        isLoading = false
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Manage Subscription")
                }
            }
            
            Text(
                text = "Expires: ${subscriptionStatus?.currentPeriodEnd ?: "N/A"}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp)
            )
        } else {
            // Not subscribed - show subscribe button
            Button(
                onClick = {
                    isLoading = true
                    CoroutineScope(Dispatchers.Main).launch {
                        paymentManager.startCheckout()
                            .onFailure { error = it.message }
                        isLoading = false
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Subscribe")
                }
            }
        }
        
        // Error message
        error?.let {
            Text(
                text = it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 8.dp)
            )
        }
    }
}

@Composable
fun BenefitRow(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Icon(
            imageVector = Icons.Default.CheckCircle,
            contentDescription = null,
            tint = Color(0xFF4CAF50)
        )
        Text(text = text)
    }
}
```

### 5. Check Subscription Status on App Launch

```kotlin
// In your Application class or MainActivity
class KeuviApplication : Application() {
    
    override fun onCreate() {
        super.onCreate()
        
        // Check subscription status on app launch
        if (TokenManager.isLoggedIn()) {
            CoroutineScope(Dispatchers.IO).launch {
                val paymentManager = PaymentManager(this@KeuviApplication)
                paymentManager.getSubscriptionStatus()
                    .onSuccess { status ->
                        // Update premium status
                        TokenManager.isPremium = status.hasSubscription
                    }
                    .onFailure {
                        // If status check fails, try syncing
                        paymentManager.syncSubscription()
                            .onSuccess { syncResponse ->
                                TokenManager.isPremium = syncResponse.isPremium
                            }
                    }
            }
        }
    }
}
```

### 6. Handle Return from Checkout/Portal

When user returns from Stripe Checkout or Portal, sync the subscription:

```kotlin
class MainActivity : ComponentActivity() {
    
    private val paymentManager by lazy { PaymentManager(this) }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Handle deep link from Stripe
        handleDeepLink(intent)
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleDeepLink(intent)
    }
    
    private fun handleDeepLink(intent: Intent?) {
        val uri = intent?.data
        if (uri != null && (uri.host == "keuvi.app" || uri.host == "keuvi.herokuapp.com")) {
            val path = uri.path
            if (path?.contains("subscription") == true || path?.contains("portal") == true) {
                // Returning from Stripe checkout or portal
                lifecycleScope.launch {
                    paymentManager.syncSubscription()
                        .onSuccess { response ->
                            TokenManager.isPremium = response.isPremium
                            
                            // Show success message
                            if (response.isPremium) {
                                Toast.makeText(
                                    this@MainActivity,
                                    "Subscription activated!",
                                    Toast.LENGTH_SHORT
                                ).show()
                            } else {
                                Toast.makeText(
                                    this@MainActivity,
                                    "Subscription status updated",
                                    Toast.LENGTH_SHORT
                                ).show()
                            }
                            
                            // Refresh UI
                            // (Trigger recomposition or update ViewModel)
                        }
                        .onFailure {
                            Toast.makeText(
                                this@MainActivity,
                                "Failed to sync subscription. Please check your connection.",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                }
            }
        }
    }
}
```

### 7. Deep Link Configuration

Add to `AndroidManifest.xml`:

```xml
<activity 
    android:name=".MainActivity"
    android:launchMode="singleTop">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
    
    <!-- Handle return from Stripe checkout/portal -->
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        
        <!-- Handle return from Stripe checkout -->
        <data
            android:scheme="https"
            android:host="keuvi.app"
            android:pathPrefix="/web" />
        
        <!-- Fallback for herokuapp.com -->
        <data
            android:scheme="https"
            android:host="keuvi.herokuapp.com"
            android:pathPrefix="/web" />
    </intent-filter>
</activity>
```

### 8. Enhanced Subscription Management View

```kotlin
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

@Composable
fun SubscriptionManagementScreen(
    paymentManager: PaymentManager,
    onSubscribed: () -> Unit
) {
    var isLoading by remember { mutableStateOf(false) }
    var subscriptionStatus by remember { mutableStateOf<SubscriptionStatus?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var isRefreshing by remember { mutableStateOf(false) }
    
    // Load subscription status on launch
    LaunchedEffect(Unit) {
        loadStatus()
    }
    
    fun loadStatus() {
        isRefreshing = true
        CoroutineScope(Dispatchers.Main).launch {
            paymentManager.getSubscriptionStatus()
                .onSuccess { 
                    subscriptionStatus = it
                    TokenManager.isPremium = it.hasSubscription
                    error = null
                }
                .onFailure { 
                    error = it.message
                }
            isRefreshing = false
        }
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Header
        Text(
            text = "Keuvi Premium",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Subscription Status Card
        if (subscriptionStatus != null) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (subscriptionStatus!!.hasSubscription) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.surfaceVariant
                    }
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = if (subscriptionStatus!!.hasSubscription) {
                                Icons.Default.CheckCircle
                            } else {
                                Icons.Default.Cancel
                            },
                            contentDescription = null,
                            tint = if (subscriptionStatus!!.hasSubscription) {
                                Color(0xFF4CAF50)
                            } else {
                                MaterialTheme.colorScheme.error
                            }
                        )
                        Text(
                            text = if (subscriptionStatus!!.hasSubscription) {
                                "Premium Active"
                            } else {
                                "No Active Subscription"
                            },
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    
                    if (subscriptionStatus!!.hasSubscription) {
                        subscriptionStatus!!.status?.let { status ->
                            Text(
                                text = "Status: $status",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                        
                        subscriptionStatus!!.currentPeriodEnd?.let { endDate ->
                            Text(
                                text = "Expires: ${formatDate(endDate)}",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                        
                        if (subscriptionStatus!!.cancelAtPeriodEnd == true) {
                            Text(
                                text = "⚠️ Subscription will cancel at period end",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // Benefits
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            BenefitRow("Unlimited practice questions")
            BenefitRow("All passages and lessons")
            BenefitRow("Detailed explanations")
            BenefitRow("Progress tracking")
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Price
        Text(
            text = "$4.99",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "per month",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Action buttons
        if (subscriptionStatus?.hasSubscription == true) {
            // Already subscribed - show manage button
            Button(
                onClick = {
                    isLoading = true
                    CoroutineScope(Dispatchers.Main).launch {
                        paymentManager.openCustomerPortal()
                            .onSuccess {
                                // Portal opened, will sync on return
                            }
                            .onFailure { 
                                error = it.message
                            }
                        isLoading = false
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Manage Subscription")
                }
            }
            
            // Refresh button
            TextButton(
                onClick = { loadStatus() },
                enabled = !isRefreshing
            ) {
                if (isRefreshing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp)
                    )
                } else {
                    Text("Refresh Status")
                }
            }
        } else {
            // Not subscribed - show subscribe button
            Button(
                onClick = {
                    isLoading = true
                    CoroutineScope(Dispatchers.Main).launch {
                        paymentManager.startCheckout()
                            .onSuccess {
                                // Checkout opened, will sync on return
                            }
                            .onFailure { 
                                error = it.message
                                isLoading = false
                            }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Subscribe")
                }
            }
        }
        
        // Error message
        error?.let {
            Text(
                text = it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 8.dp),
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

fun formatDate(dateString: String): String {
    return try {
        val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        inputFormat.timeZone = TimeZone.getTimeZone("UTC")
        val date = inputFormat.parse(dateString)
        val outputFormat = SimpleDateFormat("MMM dd, yyyy", Locale.US)
        outputFormat.format(date ?: Date())
    } catch (e: Exception) {
        dateString
    }
}
```

---

## Flow Summary

1. **User taps Subscribe**
2. **App calls `POST /api/v1/payments/checkout`**
3. **Backend returns Stripe Checkout URL**
4. **App opens URL in Custom Tab (Chrome)**
5. **User completes payment in Stripe**
6. **Stripe redirects back to app**
7. **App calls `POST /api/v1/payments/sync`**
8. **Backend confirms subscription, sets `is_premium = true`**
9. **App updates UI to show premium features**

### Cancellation Flow
1. **User taps "Manage Subscription"**
2. **App calls `POST /api/v1/payments/portal`**
3. **Opens Stripe Customer Portal**
4. **User cancels subscription**
5. **Stripe sends webhook to backend**
6. **Backend updates subscription with `cancel_at_period_end = true`**
7. **User keeps premium until period ends**
8. **When period ends, Stripe sends `customer.subscription.deleted`**
9. **Backend sets `is_premium = false`**

---

### 9. Enhanced Payment Manager with Error Handling

```kotlin
import org.json.JSONObject
import androidx.core.content.ContextCompat

class PaymentManager(private val context: Context) {
    
    private val apiClient = ApiClient.instance
    
    /**
     * Start subscription checkout flow.
     * Opens Stripe Checkout in a Custom Tab (Chrome).
     */
    suspend fun startCheckout(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.createCheckoutSession()
            
            if (response.isSuccessful) {
                val body = response.body()
                when {
                    body == null -> Result.failure(Exception("Empty response from server"))
                    body.url.isBlank() -> Result.failure(Exception("No checkout URL received"))
                    else -> {
                        // Open Stripe Checkout in Custom Tab
                        withContext(Dispatchers.Main) {
                            try {
                                val customTabsIntent = CustomTabsIntent.Builder()
                                    .setShowTitle(true)
                                    .setToolbarColor(ContextCompat.getColor(context, R.color.primary))
                                    .build()
                                
                                customTabsIntent.launchUrl(context, Uri.parse(body.url))
                                Result.success(Unit)
                            } catch (e: Exception) {
                                Result.failure(Exception("Failed to open browser: ${e.message}"))
                            }
                        }
                    }
                }
            } else {
                // Parse error response
                val errorBody = response.errorBody()?.string()
                val errorMessage = try {
                    val errorJson = JSONObject(errorBody ?: "{}")
                    errorJson.getJSONObject("error")?.getString("message") 
                        ?: "Failed to create checkout session"
                } catch (e: Exception) {
                    "Failed to create checkout session (${response.code()})"
                }
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Network error: ${e.message}"))
        }
    }
    
    /**
     * Get current subscription status.
     */
    suspend fun getSubscriptionStatus(): Result<SubscriptionStatus> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.getSubscriptionStatus()
            
            if (response.isSuccessful) {
                response.body()?.let { Result.success(it) }
                    ?: Result.failure(Exception("Empty response"))
            } else {
                val errorMessage = when (response.code()) {
                    401 -> "Please log in to check subscription status"
                    500 -> "Server error. Please try again later"
                    else -> "Failed to get status (${response.code()})"
                }
                Result.failure(Exception(errorMessage))
            }
        } catch (e: java.net.UnknownHostException) {
            Result.failure(Exception("No internet connection"))
        } catch (e: Exception) {
            Result.failure(Exception("Network error: ${e.message}"))
        }
    }
    
    /**
     * Open customer portal to manage subscription.
     */
    suspend fun openCustomerPortal(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.createPortalSession()
            
            if (response.isSuccessful) {
                val body = response.body()
                when {
                    body == null -> Result.failure(Exception("Empty response from server"))
                    body.url.isBlank() -> Result.failure(Exception("No portal URL received"))
                    else -> {
                        withContext(Dispatchers.Main) {
                            try {
                                val customTabsIntent = CustomTabsIntent.Builder()
                                    .setShowTitle(true)
                                    .setToolbarColor(ContextCompat.getColor(context, R.color.primary))
                                    .build()
                                
                                customTabsIntent.launchUrl(context, Uri.parse(body.url))
                                Result.success(Unit)
                            } catch (e: Exception) {
                                Result.failure(Exception("Failed to open browser: ${e.message}"))
                            }
                        }
                    }
                }
            } else {
                val errorBody = response.errorBody()?.string()
                val errorMessage = try {
                    val errorJson = JSONObject(errorBody ?: "{}")
                    errorJson.getJSONObject("error")?.getString("message")
                        ?: "Failed to open customer portal"
                } catch (e: Exception) {
                    when (response.code()) {
                        400 -> "No active subscription found"
                        401 -> "Please log in to manage subscription"
                        else -> "Failed to open portal (${response.code()})"
                    }
                }
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Network error: ${e.message}"))
        }
    }
    
    /**
     * Sync subscription status with Stripe.
     * Call this after returning from checkout or portal.
     */
    suspend fun syncSubscription(): Result<SyncResponse> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authService.syncSubscription()
            
            if (response.isSuccessful) {
                response.body()?.let { 
                    // Update local premium status
                    TokenManager.isPremium = it.isPremium
                    Result.success(it) 
                } ?: Result.failure(Exception("Empty response"))
            } else {
                val errorMessage = when (response.code()) {
                    400 -> "No Stripe customer found"
                    401 -> "Please log in to sync subscription"
                    500 -> "Server error. Please try again later"
                    else -> "Failed to sync (${response.code()})"
                }
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Network error: ${e.message}"))
        }
    }
}
```

### 10. Periodic Status Checking

```kotlin
// In your ViewModel or Repository
class SubscriptionRepository {
    
    private val paymentManager = PaymentManager(context)
    
    // Check subscription status periodically (e.g., every hour)
    fun startPeriodicStatusCheck() {
        CoroutineScope(Dispatchers.IO).launch {
            while (true) {
                delay(3600_000) // 1 hour
                
                if (TokenManager.isLoggedIn()) {
                    paymentManager.getSubscriptionStatus()
                        .onSuccess { status ->
                            TokenManager.isPremium = status.hasSubscription
                        }
                        .onFailure {
                            // If status check fails, try syncing
                            paymentManager.syncSubscription()
                                .onSuccess { syncResponse ->
                                    TokenManager.isPremium = syncResponse.isPremium
                                }
                        }
                }
            }
        }
    }
}
```

---

## Testing

### Test Mode Setup

1. **Use Stripe test mode keys** in your backend
2. **Test cards:**
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
   - 3D Secure: `4000 0025 0000 3155`
3. **Any future expiry date, any CVC**
4. **Test cancellation:**
   - Stripe Dashboard → Customers → [User] → Cancel subscription
   - Or use Customer Portal in app

### Testing Checklist

- [ ] Create checkout session
- [ ] Complete payment with test card
- [ ] Return to app and verify premium status
- [ ] Open customer portal
- [ ] Cancel subscription in portal
- [ ] Verify premium remains until period ends
- [ ] Check subscription status on app launch
- [ ] Test deep link handling
- [ ] Test error handling (no internet, server errors)
- [ ] Test with expired/invalid tokens

---

## Important Notes

1. **Cancellation**: Users cancel through Stripe Customer Portal (opened from your app). The app cannot cancel subscriptions directly.

2. **Status Sync**: Always check subscription status on app launch and periodically during use. The backend handles webhooks automatically, but the app should check status as a backup.

3. **Deep Links**: Make sure your `AndroidManifest.xml` is configured correctly to handle returns from Stripe checkout/portal.

4. **Error Handling**: Handle network errors gracefully. If backend sync fails, you can still check local premium status (though it may be stale).

5. **Custom Tabs**: Use Chrome Custom Tabs for better UX (seamless transition, no browser UI). Falls back to regular browser if Chrome isn't available.

6. **Premium Status**: The backend automatically sets `is_premium` based on subscription status. When a user cancels, they keep premium until `current_period_end`.
