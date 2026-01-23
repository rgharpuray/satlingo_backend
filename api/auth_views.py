from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from .models import User, Subscription, AppStoreSubscription
import google.auth.transport.requests
from google.oauth2 import id_token
import requests
from urllib.parse import quote
import logging
import base64
import jwt
try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    cryptography_available = True
except ImportError:
    cryptography_available = False
try:
    import stripe
    stripe_available = True
except ImportError:
    stripe_available = False

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    email = request.data.get('email')
    password = request.data.get('password')
    username = request.data.get('username', email.split('@')[0])
    
    if not email or not password:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Email and password are required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'User with this email already exists'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate password
    try:
        validate_password(password)
    except ValidationError as e:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': '; '.join(e.messages)}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create user
    user = User.objects.create_user(
        email=email,
        username=username,
        password=password
    )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
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
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login and get JWT tokens"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Email and password are required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=email, password=password)
    
    if user is None:
        return Response(
            {'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid email or password'}},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    """Refresh access token"""
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Refresh token is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token
        return Response({
            'access': str(access_token),
        })
    except Exception as e:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Invalid refresh token'}},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Get current user info"""
    user = request.user
    return Response({
        'id': str(user.id),
        'email': user.email,
        'username': user.username,
        'is_premium': user.is_premium,
        'has_active_subscription': user.has_active_subscription,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def google_oauth_token(request):
    """
    Verify a Google ID token directly (for iOS/mobile apps).
    
    iOS uses Google Sign-In SDK which returns an ID token directly,
    rather than an auth code that needs to be exchanged.
    
    POST body: { "id_token": "..." }
    """
    from django.conf import settings
    
    id_token_str = request.data.get('id_token')
    
    if not id_token_str:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'id_token is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build list of valid client IDs (web, iOS, Android)
    valid_client_ids = []
    if settings.GOOGLE_OAUTH_CLIENT_ID:
        valid_client_ids.append(settings.GOOGLE_OAUTH_CLIENT_ID)
    if settings.GOOGLE_OAUTH_IOS_CLIENT_ID:
        valid_client_ids.append(settings.GOOGLE_OAUTH_IOS_CLIENT_ID)
    if settings.GOOGLE_OAUTH_ANDROID_CLIENT_ID:
        valid_client_ids.append(settings.GOOGLE_OAUTH_ANDROID_CLIENT_ID)
    
    if not valid_client_ids:
        return Response(
            {'error': {'code': 'CONFIGURATION_ERROR', 'message': 'Google OAuth not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Try to verify against each valid client ID
    idinfo = None
    last_error = None
    for client_id in valid_client_ids:
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google.auth.transport.requests.Request(),
                client_id
            )
            break  # Success!
        except ValueError as e:
            last_error = e
            continue
    
    if idinfo is None:
        return Response(
            {'error': {'code': 'OAUTH_ERROR', 'message': f'Invalid token: {str(last_error)}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extract user info
    google_id = idinfo.get('sub')
    email = idinfo.get('email')
    given_name = idinfo.get('given_name', '')
    family_name = idinfo.get('family_name', '')
    
    if not email:
        return Response(
            {'error': {'code': 'OAUTH_ERROR', 'message': 'Email not provided by Google'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find or create user
    user = None
    if google_id:
        try:
            user = User.objects.get(google_id=google_id)
        except User.DoesNotExist:
            pass
    
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
                password=None
            )
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
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


@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_url(request):
    """Get Google OAuth authorization URL"""
    from django.conf import settings
    
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return Response(
            {'error': {'code': 'CONFIGURATION_ERROR', 'message': 'Google OAuth not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Build the OAuth URL
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI or request.build_absolute_uri('/api/v1/auth/google/callback')
    # Remove trailing slash to ensure exact match
    redirect_uri = redirect_uri.rstrip('/')
    scope = 'openid email profile'
    
    # URL encode the redirect_uri for the URL
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


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """Handle Google OAuth callback"""
    from django.conf import settings
    
    code = request.GET.get('code') or request.data.get('code')
    error = request.GET.get('error') or request.data.get('error')
    
    if error:
        return Response(
            {'error': {'code': 'OAUTH_ERROR', 'message': f'OAuth error: {error}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not code:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Authorization code is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        return Response(
            {'error': {'code': 'CONFIGURATION_ERROR', 'message': 'Google OAuth not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        # Exchange code for tokens
        # IMPORTANT: redirect_uri must match EXACTLY what was used in the authorization request
        # Always use the same logic as in google_oauth_url
        if settings.GOOGLE_OAUTH_REDIRECT_URI:
            redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI.rstrip('/')
        else:
            # Build from request - but this should match what was sent in authorization
            redirect_uri = request.build_absolute_uri('/api/v1/auth/google/callback').rstrip('/')
        
        logger.info(f"Google OAuth callback - redirect_uri: {redirect_uri}, client_id: {settings.GOOGLE_OAUTH_CLIENT_ID[:20] if settings.GOOGLE_OAUTH_CLIENT_ID else 'NOT SET'}...")
        
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        token_response = requests.post(token_url, data=token_data)
        
        if not token_response.ok:
            error_detail = token_response.text
            error_json = None
            try:
                error_json = token_response.json()
                error_detail = error_json.get('error_description', error_json.get('error', error_detail))
            except:
                pass
            
            logger.error(f"Google OAuth token exchange failed: {token_response.status_code} - {error_detail}")
            logger.error(f"Redirect URI used: {redirect_uri}")
            logger.error(f"Full error response: {error_json if error_json else error_detail}")
            
            # Include redirect_uri in error for debugging (but don't expose secret)
            return Response(
                {
                    'error': {
                        'code': 'OAUTH_ERROR', 
                        'message': f'Failed to exchange code for tokens: {token_response.status_code} {error_detail}',
                        'debug_info': {
                            'redirect_uri_used': redirect_uri,
                            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID[:20] + '...' if settings.GOOGLE_OAUTH_CLIENT_ID else None
                        }
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tokens = token_response.json()
        
        id_token_str = tokens.get('id_token')
        if not id_token_str:
            return Response(
                {'error': {'code': 'OAUTH_ERROR', 'message': 'No ID token received from Google'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify and decode the ID token
        # Accept tokens from web, iOS, and Android client IDs
        valid_client_ids = [settings.GOOGLE_OAUTH_CLIENT_ID]
        if settings.GOOGLE_OAUTH_IOS_CLIENT_ID:
            valid_client_ids.append(settings.GOOGLE_OAUTH_IOS_CLIENT_ID)
        if settings.GOOGLE_OAUTH_ANDROID_CLIENT_ID:
            valid_client_ids.append(settings.GOOGLE_OAUTH_ANDROID_CLIENT_ID)
        
        idinfo = None
        last_error = None
        for client_id in valid_client_ids:
            if not client_id:
                continue
            try:
                idinfo = id_token.verify_oauth2_token(
                    id_token_str,
                    google.auth.transport.requests.Request(),
                    client_id
                )
                break
            except ValueError as e:
                last_error = e
                continue
        
        if idinfo is None:
            return Response(
                {'error': {'code': 'OAUTH_ERROR', 'message': f'Invalid token: {str(last_error)}'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract user info
        google_id = idinfo.get('sub')
        email = idinfo.get('email')
        name = idinfo.get('name', '')
        given_name = idinfo.get('given_name', '')
        family_name = idinfo.get('family_name', '')
        
        if not email:
            return Response(
                {'error': {'code': 'OAUTH_ERROR', 'message': 'Email not provided by Google'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find or create user
        user = None
        if google_id:
            try:
                user = User.objects.get(google_id=google_id)
            except User.DoesNotExist:
                pass
        
        # If no user found by google_id, try by email
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
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Check if this is a browser redirect (has Referer or User-Agent suggests browser)
        # If so, redirect to frontend with tokens in URL fragment
        # Otherwise return JSON (for API calls)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        is_browser = 'Mozilla' in user_agent or 'Chrome' in user_agent or 'Safari' in user_agent or 'Firefox' in user_agent
        
        if is_browser and request.method == 'GET':
            # Redirect to frontend with tokens in URL fragment (not query string for security)
            from django.shortcuts import redirect
            import base64
            import json as json_lib
            
            # Encode tokens in base64 to pass in URL
            token_data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'is_premium': user.is_premium,
                }
            }
            
            # Use URL fragment to avoid tokens in server logs
            token_json = json_lib.dumps(token_data)
            token_encoded = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip('=')
            
            # Redirect to frontend with tokens in URL fragment (hash)
            # Redirect to passages view after login
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
        
    except requests.RequestException as e:
        logger.error(f"Google OAuth RequestException: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'OAUTH_ERROR', 'message': f'Failed to exchange code for tokens: {str(e)}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Google OAuth unexpected error: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': f'Unexpected error: {str(e)}'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def verify_apple_token(identity_token, bundle_id):
    """
    Verify Apple identity token and return decoded claims.
    
    Args:
        identity_token: JWT string from Apple Sign In
        bundle_id: Your app's bundle ID (e.g., 'com.keuvi.app')
    
    Returns:
        dict: Decoded token claims (sub, email, etc.)
    
    Raises:
        ValueError: If token is invalid
    """
    try:
        # Fetch Apple's public keys
        apple_keys_url = 'https://appleid.apple.com/auth/keys'
        apple_keys_response = requests.get(apple_keys_url, timeout=10)
        apple_keys_response.raise_for_status()
        apple_keys = apple_keys_response.json()
        
        # Decode header to get kid (key ID)
        unverified_header = jwt.get_unverified_header(identity_token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise ValueError("Token header missing 'kid'")
        
        # Find matching key
        matching_key = None
        for key in apple_keys.get('keys', []):
            if key.get('kid') == kid:
                matching_key = key
                break
        
        if not matching_key:
            raise ValueError(f"No matching key found for kid: {kid}")
        
        # Construct public key from JWK using cryptography
        if not cryptography_available:
            raise ValueError("cryptography library is required for Apple token verification")
        
        # Convert JWK to PEM format for PyJWT
        # PyJWT can decode with the public key directly
        # We'll use jwt.decode with options={'verify_signature': True} and construct the key
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        
        # Extract key parameters from JWK (base64url encoded)
        # Add padding if needed for base64 decoding
        n_b64 = matching_key['n']
        e_b64 = matching_key['e']
        
        # Add padding
        n_padded = n_b64 + '=' * (4 - len(n_b64) % 4)
        e_padded = e_b64 + '=' * (4 - len(e_b64) % 4)
        
        # Decode base64url to bytes, then to int
        n_bytes = base64.urlsafe_b64decode(n_padded)
        e_bytes = base64.urlsafe_b64decode(e_padded)
        
        n = int.from_bytes(n_bytes, 'big')
        e = int.from_bytes(e_bytes, 'big')
        
        # Construct RSA public key
        public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
        
        # Serialize to PEM format for PyJWT
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Verify and decode the token (PyJWT accepts PEM string or key object)
        decoded = jwt.decode(
            identity_token,
            pem,
            algorithms=['RS256'],
            audience=bundle_id,
            issuer='https://appleid.apple.com'
        )
        
        return decoded
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidAudienceError:
        raise ValueError(f"Invalid audience. Expected: {bundle_id}")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid issuer. Expected: https://appleid.apple.com")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")


@api_view(['POST'])
@permission_classes([AllowAny])
def apple_oauth_token(request):
    """
    Verify Apple identity token and create/login user.
    
    POST body:
    {
        "identity_token": "eyJraWQiOiJXNldjT0...",  // Required: JWT from Apple
        "email": "user@example.com",                 // Optional: Only on first sign-in
        "first_name": "John",                        // Optional: Only on first sign-in
        "last_name": "Doe"                           // Optional: Only on first sign-in
    }
    """
    identity_token = request.data.get('identity_token')
    email = request.data.get('email')  # Optional, may be in token or request
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    
    if not identity_token:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'identity_token is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    bundle_id = settings.APPLE_BUNDLE_ID
    if not bundle_id:
        return Response(
            {'error': {'code': 'CONFIGURATION_ERROR', 'message': 'Apple Bundle ID not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        # Verify the token
        decoded_token = verify_apple_token(identity_token, bundle_id)
        
        # Extract user info from token
        apple_user_id = decoded_token.get('sub')  # Apple's unique user ID
        token_email = decoded_token.get('email')  # Email may be in token (first sign-in only)
        
        # Use email from token if available, otherwise use email from request
        user_email = token_email or email
        
        if not apple_user_id:
            return Response(
                {'error': {'code': 'OAUTH_ERROR', 'message': 'Invalid token: missing sub claim'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find or create user
        user = None
        
        # First, try to find by Apple ID
        if apple_user_id:
            try:
                user = User.objects.get(apple_id=apple_user_id)
            except User.DoesNotExist:
                pass
        
        # If not found by Apple ID, try to find by email (for account linking)
        if not user and user_email:
            try:
                user = User.objects.get(email=user_email)
                # Link Apple account to existing user
                if not user.apple_id:
                    user.apple_id = apple_user_id
                    user.save()
            except User.DoesNotExist:
                pass
        
        # If still no user, create a new one
        if not user:
            # Generate email if not provided (Apple private relay or placeholder)
            if not user_email:
                user_email = f"{apple_user_id}@privaterelay.appleid.com"
            
            # Generate unique username
            username = user_email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                email=user_email,
                username=username,
                apple_id=apple_user_id,
                first_name=first_name,
                last_name=last_name,
                password=None  # No password for OAuth users
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
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
        
    except ValueError as e:
        logger.error(f"Apple OAuth token verification failed: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'OAUTH_ERROR', 'message': f'Invalid token: {str(e)}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Apple OAuth unexpected error: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': f'Unexpected error: {str(e)}'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Delete user account and all associated data.
    
    Required by Apple App Store Guideline 5.1.1(v).
    
    This will:
    - Cancel any active subscriptions (Stripe and App Store)
    - Delete or anonymize user data
    - Invalidate all refresh tokens
    - Log the deletion
    """
    user = request.user
    
    try:
        # Cancel Stripe subscriptions
        stripe_subscriptions = Subscription.objects.filter(user=user, status='active')
        for sub in stripe_subscriptions:
            try:
                if sub.stripe_subscription_id and stripe_available and settings.STRIPE_SECRET_KEY:
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    stripe.Subscription.delete(sub.stripe_subscription_id)
                    logger.info(f"Cancelled Stripe subscription {sub.stripe_subscription_id} for user {user.email}")
            except Exception as e:
                logger.error(f"Error cancelling Stripe subscription {sub.stripe_subscription_id}: {str(e)}", exc_info=True)
            
            # Mark subscription as cancelled in database
            sub.status = 'canceled'
            sub.save()
        
        # Cancel App Store subscriptions (mark as revoked)
        appstore_subscriptions = AppStoreSubscription.objects.filter(user=user, status='active')
        for sub in appstore_subscriptions:
            sub.status = 'revoked'
            sub.save()
            logger.info(f"Revoked App Store subscription {sub.original_transaction_id} for user {user.email}")
        
        # Invalidate all refresh tokens for this user
        # Note: simplejwt doesn't have a built-in blacklist, but we can delete refresh tokens
        # by filtering them (they're stored in the database if using a token blacklist app)
        # For now, we'll just delete the user which will cascade to related tokens
        
        # Store user info for logging before deletion
        user_id = user.id
        user_email = user.email
        
        # Delete all user-related data (cascade will handle related objects)
        # This includes: UserProgress, UserAnswer, PassageAttempt, LessonAttempt, etc.
        user.delete()
        
        logger.info(f"Account deleted: user_id={user_id}, email={user_email}, ip={request.META.get('REMOTE_ADDR', 'unknown')}")
        
        return Response({}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting account for user {user.email}: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': f'Failed to delete account: {str(e)}'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

