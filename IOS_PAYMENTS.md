# iOS In-App Purchases (App Store)

Apple requires iOS apps to use the App Store for subscriptions.

## Product ID
Your product ID in App Store Connect:
```
keuvipremiumbase
```
Price: Set in App Store Connect (e.g., $4.99/month)

## Endpoints

### 1. Verify Transaction (StoreKit 2 - Recommended)
```
POST /api/v1/payments/appstore/transaction
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "signed_transaction": "<JWS_string_from_StoreKit2>"
}
```

**Response (200):**
```json
{
  "success": true,
  "is_premium": true,
  "subscription": {
    "product_id": "keuvipremiumbase",
    "expires_date": "2026-02-21T00:00:00Z",
    "is_active": true,
    "environment": "Production"
  }
}
```

### 2. Verify Receipt (Legacy StoreKit 1)
```
POST /api/v1/payments/appstore/verify
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "receipt_data": "<base64_receipt_string>"
}
```

### 3. Get Subscription Status
```
GET /api/v1/payments/appstore/status
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "has_subscription": true,
  "source": "appstore",
  "status": "active",
  "product_id": "keuvipremiumbase",
  "expires_date": "2026-02-21T00:00:00Z",
  "environment": "Production"
}
```

### 4. Restore Purchases
```
POST /api/v1/payments/appstore/restore
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "transactions": ["<signed_transaction_1>", "<signed_transaction_2>", ...]
}
```

**Response:**
```json
{
  "success": true,
  "restored_count": 2,
  "is_premium": true,
  "active_subscription": {
    "product_id": "keuvipremiumbase",
    "expires_date": "2026-02-21T00:00:00Z"
  }
}
```

---

## Swift Implementation (StoreKit 2)

### 1. Product Configuration

```swift
import StoreKit

enum SubscriptionProduct: String, CaseIterable {
    case premium = "keuvipremiumbase"
}

@MainActor
class StoreManager: ObservableObject {
    @Published var products: [Product] = []
    @Published var purchasedProductIDs: Set<String> = []
    @Published var isLoading = false
    
    private var updateListenerTask: Task<Void, Error>?
    
    init() {
        updateListenerTask = listenForTransactions()
        Task {
            await loadProducts()
            await updatePurchasedProducts()
        }
    }
    
    deinit {
        updateListenerTask?.cancel()
    }
    
    // Load products from App Store
    func loadProducts() async {
        isLoading = true
        do {
            let productIDs = SubscriptionProduct.allCases.map { $0.rawValue }
            products = try await Product.products(for: productIDs)
        } catch {
            print("Failed to load products: \(error)")
        }
        isLoading = false
    }
    
    // Listen for transaction updates
    func listenForTransactions() -> Task<Void, Error> {
        return Task.detached {
            for await result in Transaction.updates {
                do {
                    let transaction = try self.checkVerified(result)
                    await self.updatePurchasedProducts()
                    await self.verifyWithBackend(transaction: transaction)
                    await transaction.finish()
                } catch {
                    print("Transaction failed verification: \(error)")
                }
            }
        }
    }
    
    // Purchase a product
    func purchase(_ product: Product) async throws -> Bool {
        let result = try await product.purchase()
        
        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            await updatePurchasedProducts()
            await verifyWithBackend(transaction: transaction)
            await transaction.finish()
            return true
            
        case .userCancelled:
            return false
            
        case .pending:
            return false
            
        @unknown default:
            return false
        }
    }
    
    // Restore purchases
    func restorePurchases() async {
        do {
            try await AppStore.sync()
            await updatePurchasedProducts()
            await restoreWithBackend()
        } catch {
            print("Failed to restore purchases: \(error)")
        }
    }
    
    // Update local purchase state
    func updatePurchasedProducts() async {
        var purchased: Set<String> = []
        
        for await result in Transaction.currentEntitlements {
            do {
                let transaction = try checkVerified(result)
                purchased.insert(transaction.productID)
            } catch {
                print("Failed to verify transaction: \(error)")
            }
        }
        
        await MainActor.run {
            self.purchasedProductIDs = purchased
        }
    }
    
    // Verify transaction result
    func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw StoreError.verificationFailed
        case .verified(let safe):
            return safe
        }
    }
    
    // Send transaction to backend for verification
    func verifyWithBackend(transaction: Transaction) async {
        guard let jwsRepresentation = transaction.jwsRepresentation else { return }
        
        do {
            let response = try await APIClient.shared.verifyAppStoreTransaction(
                signedTransaction: jwsRepresentation
            )
            
            if response.success {
                AuthManager.shared.currentUser?.isPremium = response.isPremium
            }
        } catch {
            print("Backend verification failed: \(error)")
        }
    }
    
    // Restore with backend
    func restoreWithBackend() async {
        var transactions: [String] = []
        
        for await result in Transaction.currentEntitlements {
            if case .verified(let transaction) = result,
               let jws = transaction.jwsRepresentation {
                transactions.append(jws)
            }
        }
        
        guard !transactions.isEmpty else { return }
        
        do {
            let response = try await APIClient.shared.restoreAppStorePurchases(
                transactions: transactions
            )
            
            if response.success {
                AuthManager.shared.currentUser?.isPremium = response.isPremium
            }
        } catch {
            print("Backend restore failed: \(error)")
        }
    }
}

enum StoreError: Error {
    case verificationFailed
}
```

### 2. API Client Extensions

```swift
extension APIClient {
    
    func verifyAppStoreTransaction(signedTransaction: String) async throws -> AppStoreVerifyResponse {
        let url = URL(string: "\(baseURL)/api/v1/payments/appstore/transaction")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(["signed_transaction": signedTransaction])
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(AppStoreVerifyResponse.self, from: data)
    }
    
    func restoreAppStorePurchases(transactions: [String]) async throws -> AppStoreRestoreResponse {
        let url = URL(string: "\(baseURL)/api/v1/payments/appstore/restore")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(["transactions": transactions])
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(AppStoreRestoreResponse.self, from: data)
    }
    
    func getAppStoreSubscriptionStatus() async throws -> AppStoreStatusResponse {
        let url = URL(string: "\(baseURL)/api/v1/payments/appstore/status")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(AppStoreStatusResponse.self, from: data)
    }
}

struct AppStoreVerifyResponse: Codable {
    let success: Bool
    let isPremium: Bool
    let subscription: AppStoreSubscription?
    
    enum CodingKeys: String, CodingKey {
        case success
        case isPremium = "is_premium"
        case subscription
    }
}

struct AppStoreRestoreResponse: Codable {
    let success: Bool
    let restoredCount: Int
    let isPremium: Bool
    let activeSubscription: AppStoreSubscription?
    
    enum CodingKeys: String, CodingKey {
        case success
        case restoredCount = "restored_count"
        case isPremium = "is_premium"
        case activeSubscription = "active_subscription"
    }
}

struct AppStoreStatusResponse: Codable {
    let hasSubscription: Bool
    let source: String?
    let status: String?
    let productId: String?
    let expiresDate: String?
    
    enum CodingKeys: String, CodingKey {
        case hasSubscription = "has_subscription"
        case source
        case status
        case productId = "product_id"
        case expiresDate = "expires_date"
    }
}

struct AppStoreSubscription: Codable {
    let productId: String
    let expiresDate: String?
    let isActive: Bool?
    let environment: String?
    
    enum CodingKeys: String, CodingKey {
        case productId = "product_id"
        case expiresDate = "expires_date"
        case isActive = "is_active"
        case environment
    }
}
```

### 3. Subscription View

```swift
import SwiftUI
import StoreKit

struct SubscriptionView: View {
    @StateObject private var storeManager = StoreManager()
    @State private var isPurchasing = false
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        VStack(spacing: 24) {
            // Header
            Text("Keuvi Premium")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            // Benefits
            VStack(alignment: .leading, spacing: 12) {
                BenefitRow(icon: "checkmark.circle.fill", text: "Unlimited practice questions")
                BenefitRow(icon: "checkmark.circle.fill", text: "All passages and lessons")
                BenefitRow(icon: "checkmark.circle.fill", text: "Detailed explanations")
                BenefitRow(icon: "checkmark.circle.fill", text: "Progress tracking")
            }
            .padding()
            
            Spacer()
            
            // Product
            if let product = storeManager.products.first {
                VStack(spacing: 8) {
                    Text(product.displayPrice)
                        .font(.title)
                        .fontWeight(.bold)
                    Text("per month")
                        .foregroundColor(.secondary)
                }
                
                Button(action: {
                    Task {
                        await purchase(product)
                    }
                }) {
                    if isPurchasing {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Text("Subscribe")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
                .disabled(isPurchasing)
            } else if storeManager.isLoading {
                ProgressView()
            }
            
            // Restore button
            Button("Restore Purchases") {
                Task {
                    await storeManager.restorePurchases()
                }
            }
            .foregroundColor(.secondary)
        }
        .padding()
        .alert("Error", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage)
        }
    }
    
    func purchase(_ product: Product) async {
        isPurchasing = true
        do {
            let success = try await storeManager.purchase(product)
            if success {
                // Navigate away or update UI
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isPurchasing = false
    }
}

struct BenefitRow: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.green)
            Text(text)
        }
    }
}
```

---

## App Store Connect Setup

1. **Create In-App Purchase**
   - Go to App Store Connect → Your App → In-App Purchases
   - Click "+" → Auto-Renewable Subscription
   - Reference Name: "Premium Monthly"
   - Product ID: `keuvipremiumbase`
   - Price: $4.99 (or your choice)

2. **Configure Server Notifications**
   - Go to App Store Connect → Your App → App Information
   - Scroll to "App Store Server Notifications"
   - URL: `https://keuvi.app/api/v1/payments/appstore/webhook`
   - Version: Version 2

3. **Set Up Shared Secret** (for receipt verification)
   - Go to App Store Connect → Your App → In-App Purchases → Manage
   - Click "App-Specific Shared Secret"
   - Generate and copy the secret
   - Set `APPLE_SHARED_SECRET` env var on Heroku

---

## Flow Summary

1. **User taps Subscribe**
2. **StoreKit shows Apple's purchase sheet**
3. **Apple processes payment**
4. **StoreKit returns signed transaction**
5. **App sends transaction to `POST /api/v1/payments/appstore/transaction`**
6. **Backend verifies and sets `is_premium = true`**
7. **App updates UI to show premium features**

### Cancellation Flow
1. **User cancels in iOS Settings → Subscriptions**
2. **Apple sends webhook to `/api/v1/payments/appstore/webhook`**
3. **Backend updates subscription status**
4. **User keeps premium until period ends**
5. **When period ends, Apple sends EXPIRED notification**
6. **Backend sets `is_premium = false`**

**Important**: Users cancel subscriptions through iOS Settings → [Your Name] → Subscriptions → Keuvi. The app cannot cancel subscriptions directly (Apple requirement). However, you should:
- Show subscription status in your app
- Display expiration date
- Provide a button that opens iOS Settings to manage subscription
- Check subscription status on app launch

---

## Complete Implementation Guide

### 1. Check Subscription Status on App Launch

```swift
// In your AppDelegate or SceneDelegate
func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    Task {
        await checkSubscriptionStatus()
    }
    return true
}

// Or in your main view's onAppear
struct ContentView: View {
    @StateObject private var storeManager = StoreManager()
    
    var body: some View {
        // Your app content
        .onAppear {
            Task {
                await checkSubscriptionStatus()
            }
        }
    }
    
    func checkSubscriptionStatus() async {
        // Check with backend
        do {
            let status = try await APIClient.shared.getAppStoreSubscriptionStatus()
            if status.hasSubscription {
                AuthManager.shared.currentUser?.isPremium = true
            }
        } catch {
            print("Failed to check subscription: \(error)")
        }
        
        // Also check local StoreKit entitlements
        await storeManager.updatePurchasedProducts()
    }
}
```

### 2. Subscription Management View

```swift
import SwiftUI
import StoreKit

struct SubscriptionManagementView: View {
    @StateObject private var storeManager = StoreManager()
    @State private var subscriptionStatus: AppStoreStatusResponse?
    @State private var isLoading = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                if isLoading {
                    ProgressView()
                } else if let status = subscriptionStatus {
                    if status.hasSubscription {
                        // Active subscription
                        VStack(spacing: 16) {
                            HStack {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.green)
                                Text("Premium Active")
                                    .font(.headline)
                            }
                            
                            if let expiresDate = status.expiresDate {
                                Text("Expires: \(formatDate(expiresDate))")
                                    .foregroundColor(.secondary)
                            }
                            
                            Button(action: {
                                openSubscriptionSettings()
                            }) {
                                Text("Manage Subscription")
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(Color.blue)
                                    .foregroundColor(.white)
                                    .cornerRadius(12)
                            }
                            
                            Text("Manage your subscription in iOS Settings")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    } else {
                        // No subscription
                        VStack(spacing: 16) {
                            Text("No Active Subscription")
                                .font(.headline)
                            
                            Button(action: {
                                // Navigate to subscription purchase view
                            }) {
                                Text("Subscribe Now")
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(Color.blue)
                                    .foregroundColor(.white)
                                    .cornerRadius(12)
                            }
                        }
                    }
                }
            }
            .padding()
            .navigationTitle("Subscription")
            .onAppear {
                Task {
                    await loadSubscriptionStatus()
                }
            }
        }
    }
    
    func loadSubscriptionStatus() async {
        isLoading = true
        do {
            subscriptionStatus = try await APIClient.shared.getAppStoreSubscriptionStatus()
        } catch {
            print("Failed to load subscription status: \(error)")
        }
        isLoading = false
    }
    
    func openSubscriptionSettings() {
        // Open iOS Settings → Subscriptions
        if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
            UIApplication.shared.open(url)
        }
    }
    
    func formatDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: dateString) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .none
            return displayFormatter.string(from: date)
        }
        return dateString
    }
}
```

### 3. Handle Subscription Status Changes

```swift
// Add to StoreManager
@MainActor
class StoreManager: ObservableObject {
    // ... existing code ...
    
    @Published var subscriptionStatus: SubscriptionStatus = .unknown
    
    enum SubscriptionStatus {
        case unknown
        case active
        case expired
        case cancelled
    }
    
    // Check subscription status periodically
    func startStatusMonitoring() {
        Task {
            while true {
                await checkStatus()
                try? await Task.sleep(nanoseconds: 3600_000_000_000) // Check every hour
            }
        }
    }
    
    func checkStatus() async {
        do {
            let status = try await APIClient.shared.getAppStoreSubscriptionStatus()
            
            await MainActor.run {
                if status.hasSubscription {
                    self.subscriptionStatus = .active
                    AuthManager.shared.currentUser?.isPremium = true
                } else {
                    self.subscriptionStatus = .expired
                    AuthManager.shared.currentUser?.isPremium = false
                }
            }
        } catch {
            print("Failed to check status: \(error)")
        }
    }
}
```

### 4. Listen for Transaction Updates (Auto-renewal, Cancellation)

```swift
// Enhanced transaction listener in StoreManager
func listenForTransactions() -> Task<Void, Error> {
    return Task.detached {
        for await result in Transaction.updates {
            do {
                let transaction = try self.checkVerified(result)
                
                // Check transaction type
                if transaction.revocationDate != nil {
                    // Subscription was revoked/refunded
                    await MainActor.run {
                        self.subscriptionStatus = .cancelled
                        AuthManager.shared.currentUser?.isPremium = false
                    }
                } else if transaction.expirationDate != nil,
                          transaction.expirationDate! < Date() {
                    // Subscription expired
                    await MainActor.run {
                        self.subscriptionStatus = .expired
                        AuthManager.shared.currentUser?.isPremium = false
                    }
                } else {
                    // Active subscription
                    await self.verifyWithBackend(transaction: transaction)
                }
                
                await transaction.finish()
            } catch {
                print("Transaction failed verification: \(error)")
            }
        }
    }
}
```

### 5. Show Premium Status Throughout App

```swift
// Create a view modifier or environment object
@MainActor
class PremiumManager: ObservableObject {
    @Published var isPremium: Bool = false
    
    func checkPremiumStatus() async {
        // Check with backend
        do {
            let status = try await APIClient.shared.getAppStoreSubscriptionStatus()
            isPremium = status.hasSubscription
        } catch {
            // Fallback to local StoreKit check
            let storeManager = StoreManager()
            await storeManager.updatePurchasedProducts()
            isPremium = !storeManager.purchasedProductIDs.isEmpty
        }
    }
}

// Use in your views
struct PremiumContentView: View {
    @StateObject private var premiumManager = PremiumManager()
    
    var body: some View {
        if premiumManager.isPremium {
            // Premium content
        } else {
            // Free content or upgrade prompt
        }
    }
}
```

---

## Testing Checklist

### Sandbox Testing
1. Create sandbox test account in App Store Connect
2. Sign out of App Store on device
3. Test purchase flow
4. Test cancellation (cancel in Settings)
5. Test restore purchases
6. Verify backend receives webhooks

### Production Testing
1. Submit app with subscription for review
2. Apple will test the subscription flow
3. Once approved, test with real account
4. Monitor webhook logs on Heroku

---

## Important Notes

1. **Cancellation**: Users must cancel through iOS Settings. Your app cannot cancel subscriptions (Apple requirement).

2. **Status Sync**: Always check subscription status on app launch and periodically during use.

3. **Webhooks**: Backend automatically handles renewals, cancellations, and expirations via webhooks. The app should periodically check status as a backup.

4. **Restore Purchases**: Always provide a "Restore Purchases" button for users who reinstall the app or switch devices.

5. **Error Handling**: Handle network errors gracefully. If backend verification fails, you can still check local StoreKit entitlements as a fallback.
