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
from .models import User
import google.auth.transport.requests
from google.oauth2 import id_token
import requests
from urllib.parse import quote
import logging

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
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google.auth.transport.requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except ValueError as e:
            return Response(
                {'error': {'code': 'OAUTH_ERROR', 'message': f'Invalid token: {str(e)}'}},
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
            frontend_url = f'/web/#google_oauth={token_encoded}'
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

