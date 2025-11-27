from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User


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

