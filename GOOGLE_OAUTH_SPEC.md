# Google OAuth Authentication Specification

This document describes the complete Google OAuth implementation used in this project, from start to finish.

## Overview

The implementation uses the OAuth 2.0 authorization code flow with Google. The flow consists of:
1. Frontend requests OAuth URL from backend
2. User is redirected to Google for authentication
3. Google redirects back to backend callback endpoint
4. Backend exchanges code for tokens and creates/updates user
5. Backend redirects to frontend with tokens in URL fragment
6. Frontend extracts tokens and stores them

## Backend Implementation

### 1. Dependencies

**Python packages required:**
```python
google-auth-httplib2>=0.1.1
google-auth-oauthlib>=1.1.0
requests  # For token exchange
```

### 2. Environment Variables

Set these in your environment or settings:
```python
GOOGLE_OAUTH_CLIENT_ID = 'your-client-id.apps.googleusercontent.com'
GOOGLE_OAUTH_CLIENT_SECRET = 'your-client-secret'
GOOGLE_OAUTH_REDIRECT_URI = 'https://yourdomain.com/api/v1/auth/google/callback'
# Optional: If not set, will be auto-generated from request
```

### 3. User Model

Add a `google_id` field to your User model:
```python
class User(AbstractUser):
    google_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        unique=True,
        help_text="Google OAuth ID"
    )
```

**Migration:**
```python
# Create migration: python manage.py makemigrations
# The field should be nullable and unique
```

### 4. API Endpoints

#### Endpoint 1: Get OAuth URL
**Route:** `GET /api/v1/auth/google/url`

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=openid email profile&access_type=offline&prompt=consent",
  "client_id": "your-client-id"
}
```

**Implementation:**
```python
@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_url(request):
    """Get Google OAuth authorization URL"""
    from django.conf import settings
    from urllib.parse import quote
    
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return Response(
            {'error': {'code': 'CONFIGURATION_ERROR', 'message': 'Google OAuth not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Build the OAuth URL
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI or request.build_absolute_uri('/api/v1/auth/google/callback')
    redirect_uri = redirect_uri.rstrip('/')  # Remove trailing slash for exact match
    scope = 'openid email profile'
    
    # URL encode the redirect_uri
    redirect_uri_encoded = quote(redirect_uri, safe='')
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_OAUTH_CLIENT_ID}&"
        f"redirect_uri={redirect_uri_encoded}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return Response({
        'auth_url': auth_url,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID
    })
```

**Key points:**
- `redirect_uri` must match EXACTLY in both URL generation and callback (no trailing slashes)
- `access_type=offline` allows getting refresh tokens
- `prompt=consent` ensures we get a refresh token

#### Endpoint 2: OAuth Callback
**Route:** `GET /api/v1/auth/google/callback` (also accepts POST)

**Query Parameters:**
- `code`: Authorization code from Google
- `error`: Error code if user denied access

**Implementation Flow:**

1. **Extract code and validate:**
```python
code = request.GET.get('code') or request.data.get('code')
error = request.GET.get('error') or request.data.get('error')

if error:
    return Response({'error': {'code': 'OAUTH_ERROR', 'message': f'OAuth error: {error}'}}, ...)

if not code:
    return Response({'error': {'code': 'BAD_REQUEST', 'message': 'Authorization code is required'}}, ...)
```

2. **Exchange code for tokens:**
```python
import requests

token_url = 'https://oauth2.googleapis.com/token'
token_data = {
    'code': code,
    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
    'redirect_uri': redirect_uri,  # MUST match exactly what was sent in auth URL
    'grant_type': 'authorization_code',
}

token_response = requests.post(token_url, data=token_data)
tokens = token_response.json()
id_token_str = tokens.get('id_token')
```

3. **Verify and decode ID token:**
```python
import google.auth.transport.requests
from google.oauth2 import id_token

idinfo = id_token.verify_oauth2_token(
    id_token_str,
    google.auth.transport.requests.Request(),
    settings.GOOGLE_OAUTH_CLIENT_ID
)

# Extract user info
google_id = idinfo.get('sub')  # Google's unique user ID
email = idinfo.get('email')
given_name = idinfo.get('given_name', '')
family_name = idinfo.get('family_name', '')
```

4. **Find or create user:**
```python
user = None

# First, try to find by google_id
if google_id:
    try:
        user = User.objects.get(google_id=google_id)
    except User.DoesNotExist:
        pass

# If not found, try by email (link Google account to existing user)
if not user:
    try:
        user = User.objects.get(email=email)
        # Link Google account to existing user
        if not user.google_id:
            user.google_id = google_id
            user.save()
    except User.DoesNotExist:
        # Create new user
        username = email.split('@')[0]
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(
            email=email,
            username=username,
            google_id=google_id,
            first_name=given_name,
            last_name=family_name,
            password=None  # No password for OAuth users
        )
```

5. **Generate JWT tokens:**
```python
from rest_framework_simplejwt.tokens import RefreshToken

refresh = RefreshToken.for_user(user)
```

6. **Return response (browser vs API):**
```python
# Detect if this is a browser request
user_agent = request.META.get('HTTP_USER_AGENT', '')
is_browser = 'Mozilla' in user_agent or 'Chrome' in user_agent or 'Safari' in user_agent or 'Firefox' in user_agent

if is_browser and request.method == 'GET':
    # Redirect to frontend with tokens in URL fragment (not query string for security)
    import base64
    import json
    
    token_data = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'is_premium': user.is_premium,  # Add any other user fields you need
        }
    }
    
    # Encode tokens in base64 to pass in URL
    token_json = json.dumps(token_data)
    token_encoded = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip('=')
    
    # Redirect to frontend with tokens in URL fragment (hash)
    frontend_url = f'/web/#passages?google_oauth={token_encoded}'
    return redirect(frontend_url)

# Return JSON for API calls
return Response({
    'user': {
        'id': str(user.id),
        'email': user.email,
        'username': user.username,
        'is_premium': user.is_premium,
    },
    'tokens': {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
})
```

### 5. URL Configuration

```python
# urls.py
from .auth_views import google_oauth_url, google_oauth_callback

urlpatterns = [
    # ... other patterns
    path('auth/google/url', google_oauth_url, name='google-oauth-url'),
    path('auth/google/callback', google_oauth_callback, name='google-oauth-callback'),
]
```

## Frontend Implementation

### 1. Initiate Google Login

```javascript
async function handleGoogleLogin() {
    try {
        // Get the Google OAuth URL from backend
        const response = await fetch(`${API_BASE}/auth/google/url`);
        const result = await response.json();
        
        if (response.ok && result.auth_url) {
            // Close any modals
            closeModal('loginModal');
            closeModal('registerModal');
            
            // Redirect to Google OAuth
            window.location.href = result.auth_url;
        } else {
            alert('Failed to initiate Google login. Please try again.');
        }
    } catch (error) {
        console.error('Google login error:', error);
        alert('Network error. Please try again.');
    }
}
```

### 2. Handle OAuth Callback

**Call this function on page load (before hash routing):**

```javascript
async function handleGoogleCallback() {
    const hash = window.location.hash;
    
    // Check for tokens in URL fragment (from backend redirect)
    if (hash.includes('google_oauth=')) {
        // Parse hash - could be #passages?google_oauth=... or just #google_oauth=...
        let hashPart = hash.substring(1); // Remove #
        let tokenData = null;
        
        // Check if it has query params
        if (hashPart.includes('?')) {
            const parts = hashPart.split('?');
            const params = new URLSearchParams(parts[1]);
            tokenData = params.get('google_oauth');
        } else {
            // Direct parameter in hash
            const params = new URLSearchParams(hashPart);
            tokenData = params.get('google_oauth');
        }
        
        if (tokenData) {
            try {
                // Decode base64 token data
                let padded = tokenData;
                while (padded.length % 4) {
                    padded += '=';
                }
                const decoded = atob(padded);
                const result = JSON.parse(decoded);
                
                // Validate result structure
                if (!result.access || !result.user) {
                    throw new Error('Invalid token structure');
                }
                
                // Store tokens and user info
                authToken = result.access;
                if (result.refresh) {
                    localStorage.setItem('refreshToken', result.refresh);
                }
                localStorage.setItem('authToken', authToken);
                currentUser = result.user;
                
                // Clean up URL - remove google_oauth param but keep navigation
                const cleanHash = hashPart.split('?')[0] || '#passages';
                window.history.replaceState({}, document.title, window.location.pathname + cleanHash);
                
                // Update UI
                updateUI();
                
                // Navigate to appropriate view
                if (!hashPart.includes('passages')) {
                    showPassages();
                } else {
                    handleHashRoute();
                }
                return;
            } catch (error) {
                console.error('Error in Google OAuth callback:', error);
                alert('Failed to complete Google login: ' + (error.message || 'Unknown error'));
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }
    }
    
    // Fallback: Check for code in query string (direct API call)
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    
    if (error) {
        alert(`Google login failed: ${error}`);
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }
    
    if (code) {
        try {
            // Exchange code for tokens
            const response = await fetch(`${API_BASE}/auth/google/callback?code=${encodeURIComponent(code)}`);
            const result = await response.json();
            
            if (response.ok) {
                authToken = result.tokens.access;
                localStorage.setItem('authToken', authToken);
                currentUser = result.user;
                window.history.replaceState({}, document.title, window.location.pathname);
                updateUI();
                showPassages();
            } else {
                alert(result.error?.message || 'Google login failed');
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        } catch (error) {
            console.error('Google callback error:', error);
            alert('Failed to complete Google login. Please try again.');
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }
}
```

### 3. Call on Page Load

```javascript
// Call this BEFORE hash routing
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        handleGoogleCallback();  // Check for OAuth callback first
        // ... then handle hash routing
    });
} else {
    handleGoogleCallback();  // Check for OAuth callback first
    // ... then handle hash routing
}
```

## Google Cloud Console Setup

1. **Go to Google Cloud Console:** https://console.cloud.google.com/
2. **Create/Select Project**
3. **Enable Google+ API** (or Google Identity API)
4. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: Add your callback URL
     - Example: `https://yourdomain.com/api/v1/auth/google/callback`
   - Save and copy Client ID and Client Secret

## Security Considerations

1. **URL Fragment vs Query String:**
   - Tokens are passed in URL fragment (`#`) not query string (`?`)
   - Fragments are not sent to server, so tokens don't appear in server logs
   - Use base64 encoding to safely pass in URL

2. **Redirect URI Matching:**
   - Google requires EXACT match (no trailing slashes, exact protocol/domain)
   - Always use `.rstrip('/')` to remove trailing slashes
   - Use the same logic to build redirect_uri in both URL generation and callback

3. **Token Verification:**
   - Always verify the ID token using Google's library
   - Never trust the token without verification

4. **User Linking:**
   - If user exists by email but not google_id, link the accounts
   - This allows users to use either email/password or Google login

## Error Handling

**Backend errors:**
- Configuration errors (missing client ID/secret)
- OAuth errors (user denied, invalid code)
- Token exchange failures
- User creation failures

**Frontend errors:**
- Network errors
- Invalid token structure
- Decoding failures
- UI update failures

Always provide user-friendly error messages and log detailed errors server-side.

## Testing

1. **Test successful flow:**
   - Click "Sign in with Google"
   - Complete Google authentication
   - Verify tokens are stored
   - Verify user is logged in

2. **Test error cases:**
   - User denies access
   - Invalid redirect URI
   - Network failures
   - Missing configuration

3. **Test user linking:**
   - Create user with email/password
   - Sign in with Google using same email
   - Verify accounts are linked

## Complete Flow Diagram

```
User clicks "Sign in with Google"
    ↓
Frontend: GET /api/v1/auth/google/url
    ↓
Backend: Returns auth_url
    ↓
Frontend: Redirects to Google (window.location.href = auth_url)
    ↓
User authenticates with Google
    ↓
Google redirects to: /api/v1/auth/google/callback?code=...
    ↓
Backend: Exchanges code for tokens
    ↓
Backend: Verifies ID token
    ↓
Backend: Finds/creates user
    ↓
Backend: Generates JWT tokens
    ↓
Backend: Redirects to frontend with tokens in URL fragment
    ↓
Frontend: Extracts tokens from hash
    ↓
Frontend: Stores tokens in localStorage
    ↓
Frontend: Updates UI and navigates
```

## Key Implementation Notes

1. **Redirect URI consistency is critical** - must match exactly
2. **Use URL fragments for tokens** - more secure than query strings
3. **Handle both browser redirects and API calls** - detect via User-Agent
4. **Link existing accounts** - check by email if google_id not found
5. **Call handleGoogleCallback() before hash routing** - to catch OAuth redirects
6. **Clean up URL after extracting tokens** - remove OAuth params from hash


