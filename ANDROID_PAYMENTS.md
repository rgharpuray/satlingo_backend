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

### 5. Handle Return from Checkout

When user returns from Stripe Checkout, sync the subscription:

```kotlin
class MainActivity : ComponentActivity() {
    
    private val paymentManager by lazy { PaymentManager(this) }
    
    override fun onResume() {
        super.onResume()
        
        // Check if returning from Stripe checkout
        val uri = intent?.data
        if (uri?.host == "keuvi.herokuapp.com" && uri.path?.contains("subscription") == true) {
            // Sync subscription status
            lifecycleScope.launch {
                paymentManager.syncSubscription()
                    .onSuccess { 
                        if (it.isPremium) {
                            // Update UI to show premium
                            Toast.makeText(this@MainActivity, "Subscription activated!", Toast.LENGTH_SHORT).show()
                        }
                    }
            }
        }
    }
}
```

### 6. Deep Link Configuration

Add to `AndroidManifest.xml`:

```xml
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        
        <!-- Handle return from Stripe checkout -->
        <data
            android:scheme="https"
            android:host="keuvi.herokuapp.com"
            android:pathPrefix="/web" />
    </intent-filter>
</activity>
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

## Testing

1. Use Stripe test mode keys
2. Test card: `4242 4242 4242 4242`
3. Any future expiry, any CVC
4. Test cancellation in Stripe Dashboard → Customers → [User] → Cancel subscription
