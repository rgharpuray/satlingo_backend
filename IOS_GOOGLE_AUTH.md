# iOS Google Sign-In Integration

## iOS Client ID
```
412415832820-s8dqgts2es0mtbc7efkqjui5l5ed2sgk.apps.googleusercontent.com
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

## Swift Implementation

### 1. Add Google Sign-In SDK

In Xcode: File → Add Package Dependencies → `https://github.com/google/GoogleSignIn-iOS`

### 2. Configure Info.plist

Add URL scheme for your iOS client ID:
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.googleusercontent.apps.412415832820-s8dqgts2es0mtbc7efkqjui5l5ed2sgk</string>
    </array>
  </dict>
</array>
<key>GIDClientID</key>
<string>412415832820-s8dqgts2es0mtbc7efkqjui5l5ed2sgk.apps.googleusercontent.com</string>
```

### 3. Sign In Flow

```swift
import GoogleSignIn

func signInWithGoogle() {
    guard let presentingVC = UIApplication.shared.windows.first?.rootViewController else { return }
    
    GIDSignIn.sharedInstance.signIn(withPresenting: presentingVC) { result, error in
        guard let user = result?.user,
              let idToken = user.idToken?.tokenString else {
            print("Google Sign-In failed: \(error?.localizedDescription ?? "Unknown")")
            return
        }
        
        // Send to backend
        Task {
            await verifyWithBackend(idToken: idToken)
        }
    }
}

func verifyWithBackend(idToken: String) async {
    let url = URL(string: "https://keuvi.herokuapp.com/api/v1/auth/google/token")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(["id_token": idToken])
    
    do {
        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(AuthResponse.self, from: data)
        
        // Store tokens
        KeychainHelper.save(response.tokens.access, for: "accessToken")
        KeychainHelper.save(response.tokens.refresh, for: "refreshToken")
        
        // Update app state
        AuthManager.shared.currentUser = response.user
        AuthManager.shared.isLoggedIn = true
    } catch {
        print("Backend auth failed: \(error)")
    }
}

struct AuthResponse: Codable {
    let user: User
    let tokens: Tokens
    
    struct User: Codable {
        let id: String
        let email: String
        let username: String
        let is_premium: Bool
    }
    
    struct Tokens: Codable {
        let access: String
        let refresh: String
    }
}
```

### 4. Handle URL Callback (in App/SceneDelegate)

```swift
func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {
    return GIDSignIn.sharedInstance.handle(url)
}
```

## That's It

1. User taps "Sign in with Google"
2. Google SDK shows sign-in UI
3. SDK returns ID token
4. Send token to `POST /api/v1/auth/google/token`
5. Backend returns JWT tokens + user info
6. Store tokens, user is logged in
