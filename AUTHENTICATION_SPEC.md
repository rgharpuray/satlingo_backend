# Authentication API Specification

Complete authentication guide for iOS client integration.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Overview

The API uses **JWT (JSON Web Tokens)** for authentication. Clients receive two tokens:
- **Access Token**: Short-lived (7 days), used for API requests
- **Refresh Token**: Long-lived (30 days), used to get new access tokens

## Authentication Flow

1. User registers or logs in → Receives access + refresh tokens
2. Client stores tokens securely (Keychain on iOS)
3. Include access token in `Authorization` header for authenticated requests
4. When access token expires (401), use refresh token to get new access token
5. When refresh token expires, user must login again

---

## Endpoints

### 1. Register

Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "username": "optional_username"  // Optional, defaults to email prefix
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "user",
    "is_premium": false
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Error Responses:**

**400 Bad Request** - Invalid input:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Email and password are required"
  }
}
```

**400 Bad Request** - User already exists:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "User with this email already exists"
  }
}
```

**400 Bad Request** - Weak password:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "This password is too short. It must contain at least 8 characters."
  }
}
```

---

### 2. Login

Authenticate existing user and get tokens.

**Endpoint:** `POST /auth/login`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "user",
    "is_premium": false
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Email and password are required"
  }
}
```

**401 Unauthorized:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid email or password"
  }
}
```

---

### 3. Get Current User

Get authenticated user's information.

**Endpoint:** `GET /auth/me`

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "user",
  "is_premium": false,
  "has_active_subscription": false
}
```

**Error Responses:**

**401 Unauthorized** - Invalid or expired token:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication credentials were not provided."
  }
}
```

---

### 4. Refresh Access Token

Get a new access token using refresh token.

**Endpoint:** `POST /auth/refresh`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Refresh token is required"
  }
}
```

**400 Bad Request** - Invalid refresh token:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid refresh token"
  }
}
```

---

## Using Tokens

### Making Authenticated Requests

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Example:**
```http
GET /api/v1/auth/me HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json
```

### Token Expiration Handling

When you receive a **401 Unauthorized** response, the access token has expired. Follow these steps:

1. **Check if you have a refresh token**
2. **Call `/auth/refresh` with the refresh token**
3. **Update stored access token**
4. **Retry the original request with new access token**

If refresh also fails (401), user must login again.

---

## Token Storage (iOS)

### Recommended: Keychain

Store tokens securely in iOS Keychain:

```swift
import Security

class KeychainHelper {
    static func save(_ value: String, forKey key: String) {
        let data = value.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    static func load(forKey key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true
        ]
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        guard let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    
    static func delete(forKey key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
    }
}

// Usage
KeychainHelper.save(accessToken, forKey: "access_token")
KeychainHelper.save(refreshToken, forKey: "refresh_token")
```

---

## Integration Examples

### Swift/UIKit Example

```swift
import Foundation

class AuthService {
    static let shared = AuthService()
    private let baseURL = "http://localhost:8000/api/v1"
    
    // MARK: - Registration
    func register(email: String, password: String, completion: @escaping (Result<User, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/auth/register") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "email": email,
            "password": password
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let userDict = json["user"] as? [String: Any],
                  let tokensDict = json["tokens"] as? [String: Any],
                  let accessToken = tokensDict["access"] as? String,
                  let refreshToken = tokensDict["refresh"] as? String else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            // Store tokens
            KeychainHelper.save(accessToken, forKey: "access_token")
            KeychainHelper.save(refreshToken, forKey: "refresh_token")
            
            // Parse user
            if let user = User(from: userDict) {
                completion(.success(user))
            } else {
                completion(.failure(AuthError.invalidResponse))
            }
        }.resume()
    }
    
    // MARK: - Login
    func login(email: String, password: String, completion: @escaping (Result<User, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/auth/login") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "email": email,
            "password": password
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            if httpResponse.statusCode == 401 {
                if let error = json["error"] as? [String: Any],
                   let message = error["message"] as? String {
                    completion(.failure(AuthError.unauthorized(message)))
                } else {
                    completion(.failure(AuthError.unauthorized("Invalid credentials")))
                }
                return
            }
            
            guard let userDict = json["user"] as? [String: Any],
                  let tokensDict = json["tokens"] as? [String: Any],
                  let accessToken = tokensDict["access"] as? String,
                  let refreshToken = tokensDict["refresh"] as? String else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            // Store tokens
            KeychainHelper.save(accessToken, forKey: "access_token")
            KeychainHelper.save(refreshToken, forKey: "refresh_token")
            
            // Parse user
            if let user = User(from: userDict) {
                completion(.success(user))
            } else {
                completion(.failure(AuthError.invalidResponse))
            }
        }.resume()
    }
    
    // MARK: - Get Current User
    func getCurrentUser(completion: @escaping (Result<User, Error>) -> Void) {
        guard let accessToken = KeychainHelper.load(forKey: "access_token"),
              let url = URL(string: "\(baseURL)/auth/me") else {
            completion(.failure(AuthError.notAuthenticated))
            return
        }
        
        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            if httpResponse.statusCode == 401 {
                // Token expired, try to refresh
                self.refreshToken { result in
                    switch result {
                    case .success:
                        // Retry with new token
                        self.getCurrentUser(completion: completion)
                    case .failure:
                        completion(.failure(AuthError.notAuthenticated))
                    }
                }
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let user = User(from: json) else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            completion(.success(user))
        }.resume()
    }
    
    // MARK: - Refresh Token
    func refreshToken(completion: @escaping (Result<Void, Error>) -> Void) {
        guard let refreshToken = KeychainHelper.load(forKey: "refresh_token"),
              let url = URL(string: "\(baseURL)/auth/refresh") else {
            completion(.failure(AuthError.notAuthenticated))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = ["refresh": refreshToken]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            if httpResponse.statusCode != 200 {
                // Refresh failed, clear tokens
                KeychainHelper.delete(forKey: "access_token")
                KeychainHelper.delete(forKey: "refresh_token")
                completion(.failure(AuthError.notAuthenticated))
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let accessToken = json["access"] as? String else {
                completion(.failure(AuthError.invalidResponse))
                return
            }
            
            // Update stored access token
            KeychainHelper.save(accessToken, forKey: "access_token")
            completion(.success(()))
        }.resume()
    }
    
    // MARK: - Logout
    func logout() {
        KeychainHelper.delete(forKey: "access_token")
        KeychainHelper.delete(forKey: "refresh_token")
    }
    
    // MARK: - Check if Authenticated
    func isAuthenticated() -> Bool {
        return KeychainHelper.load(forKey: "access_token") != nil
    }
    
    // MARK: - Get Access Token
    func getAccessToken() -> String? {
        return KeychainHelper.load(forKey: "access_token")
    }
}

// MARK: - Error Types
enum AuthError: Error, LocalizedError {
    case invalidResponse
    case unauthorized(String)
    case notAuthenticated
    
    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized(let message):
            return message
        case .notAuthenticated:
            return "User is not authenticated"
        }
    }
}

// MARK: - User Model
struct User: Codable {
    let id: String
    let email: String
    let username: String
    let isPremium: Bool
    
    enum CodingKeys: String, CodingKey {
        case id
        case email
        case username
        case isPremium = "is_premium"
    }
    
    init?(from dict: [String: Any]) {
        guard let id = dict["id"] as? String,
              let email = dict["email"] as? String,
              let username = dict["username"] as? String,
              let isPremium = dict["is_premium"] as? Bool else {
            return nil
        }
        self.id = id
        self.email = email
        self.username = username
        self.isPremium = isPremium
    }
}
```

### SwiftUI Example

```swift
import SwiftUI

class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var errorMessage: String?
    
    private let authService = AuthService.shared
    
    init() {
        checkAuthentication()
    }
    
    func checkAuthentication() {
        if authService.isAuthenticated() {
            authService.getCurrentUser { [weak self] result in
                DispatchQueue.main.async {
                    switch result {
                    case .success(let user):
                        self?.currentUser = user
                        self?.isAuthenticated = true
                    case .failure:
                        self?.isAuthenticated = false
                    }
                }
            }
        }
    }
    
    func login(email: String, password: String) {
        authService.login(email: email, password: password) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let user):
                    self?.currentUser = user
                    self?.isAuthenticated = true
                    self?.errorMessage = nil
                case .failure(let error):
                    self?.errorMessage = error.localizedDescription
                    self?.isAuthenticated = false
                }
            }
        }
    }
    
    func register(email: String, password: String) {
        authService.register(email: email, password: password) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let user):
                    self?.currentUser = user
                    self?.isAuthenticated = true
                    self?.errorMessage = nil
                case .failure(let error):
                    self?.errorMessage = error.localizedDescription
                    self?.isAuthenticated = false
                }
            }
        }
    }
    
    func logout() {
        authService.logout()
        isAuthenticated = false
        currentUser = nil
    }
}
```

---

## Making Authenticated API Requests

### Generic Request Helper

```swift
func makeAuthenticatedRequest<T: Decodable>(
    endpoint: String,
    method: String = "GET",
    body: [String: Any]? = nil,
    responseType: T.Type,
    completion: @escaping (Result<T, Error>) -> Void
) {
    guard let accessToken = AuthService.shared.getAccessToken(),
          let url = URL(string: "\(baseURL)\(endpoint)") else {
        completion(.failure(AuthError.notAuthenticated))
        return
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = method
    request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    if let body = body {
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    }
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let error = error {
            completion(.failure(error))
            return
        }
        
        guard let httpResponse = response as? HTTPURLResponse else {
            completion(.failure(AuthError.invalidResponse))
            return
        }
        
        // Handle token expiration
        if httpResponse.statusCode == 401 {
            AuthService.shared.refreshToken { result in
                switch result {
                case .success:
                    // Retry request with new token
                    makeAuthenticatedRequest(
                        endpoint: endpoint,
                        method: method,
                        body: body,
                        responseType: responseType,
                        completion: completion
                    )
                case .failure:
                    completion(.failure(AuthError.notAuthenticated))
                }
            }
            return
        }
        
        guard let data = data else {
            completion(.failure(AuthError.invalidResponse))
            return
        }
        
        do {
            let decoded = try JSONDecoder().decode(T.self, from: data)
            completion(.success(decoded))
        } catch {
            completion(.failure(error))
        }
    }.resume()
}

// Usage
makeAuthenticatedRequest(
    endpoint: "/progress",
    responseType: ProgressResponse.self
) { result in
    switch result {
    case .success(let progress):
        print("Progress: \(progress)")
    case .failure(let error):
        print("Error: \(error)")
    }
}
```

---

## Token Lifecycle

### Access Token
- **Lifetime**: 7 days
- **Usage**: Include in `Authorization` header for all authenticated requests
- **Expiration**: When expired, returns 401 Unauthorized

### Refresh Token
- **Lifetime**: 30 days
- **Usage**: Only for `/auth/refresh` endpoint
- **Expiration**: When expired, user must login again

### Best Practices

1. **Store tokens securely** - Use Keychain, never UserDefaults
2. **Check token on app launch** - Call `/auth/me` to verify token validity
3. **Handle 401 automatically** - Implement automatic token refresh
4. **Clear tokens on logout** - Remove both tokens from storage
5. **Handle refresh failure** - If refresh fails, redirect to login

---

## Error Handling

### Common Error Codes

| Code | Status | Description | Action |
|------|--------|-------------|--------|
| `BAD_REQUEST` | 400 | Invalid input data | Show error message to user |
| `UNAUTHORIZED` | 401 | Invalid/expired token | Refresh token or redirect to login |
| `FORBIDDEN` | 403 | Insufficient permissions | Show permission error |
| `NOT_FOUND` | 404 | Resource not found | Show not found message |
| `INTERNAL_ERROR` | 500 | Server error | Show generic error, retry later |

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}  // Optional additional details
  }
}
```

---

## Testing

### Test Credentials

For development, you can create test users via:
1. Web interface: `http://localhost:8000/web/`
2. Admin panel: `http://localhost:8000/admin/`
3. Registration endpoint

### cURL Examples

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

**Get Current User:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Refresh Token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

---

## Security Notes

1. **Never store tokens in UserDefaults** - Use Keychain
2. **Never log tokens** - Tokens are sensitive credentials
3. **Use HTTPS in production** - Always use encrypted connections
4. **Validate tokens on app launch** - Check if user is still authenticated
5. **Handle token expiration gracefully** - Auto-refresh when possible

---

## Premium Status

After authentication, check `user.is_premium` to determine access level:

- **Free users**: Can only access `tier: "free"` passages
- **Premium users**: Can access both `free` and `premium` passages

### Premium Content Filtering

**The backend automatically handles premium filtering - no client-side changes needed!**

The API automatically filters premium content based on the user's authentication status:

1. **Without authentication token**: Only free passages are returned
2. **With token (free user)**: Only free passages are returned
3. **With token (premium user)**: Both free and premium passages are returned

**How it works:**
- Client simply calls `GET /api/v1/passages` with `Authorization: Bearer <token>`
- Backend automatically checks user's premium status from the token
- Backend automatically filters the response before sending it
- Client receives only the passages the user is allowed to see

**Client Implementation:**
```swift
// Just call the endpoint normally with the token
// Backend handles all filtering automatically
var request = URLRequest(url: URL(string: "\(baseURL)/passages/")!)
request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")

// The response will automatically contain:
// - Premium users: all passages (free + premium)
// - Free users: only free passages
// No client-side filtering needed!
```

**Optional UI Enhancement:**
You can check `user.is_premium` from the login response to show/hide premium upgrade prompts in the UI, but the API filtering happens automatically on the backend.

---

## Quick Reference

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/auth/register` | POST | No | Create new account |
| `/auth/login` | POST | No | Login and get tokens |
| `/auth/me` | GET | Yes | Get current user info |
| `/auth/refresh` | POST | No* | Refresh access token |

*Refresh endpoint doesn't require Authorization header, but needs valid refresh token in body

---

## Support

For issues or questions:
1. Check error response for detailed error messages
2. Verify token is included in Authorization header
3. Ensure tokens are stored and retrieved correctly
4. Check network connectivity
5. Verify API base URL is correct


