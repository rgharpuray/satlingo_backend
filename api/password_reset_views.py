"""
api/password_reset_views.py
Location: /Users/rishi/argosventures/satlingo_backend/api/password_reset_views.py

This module handles password reset functionality including:
- API endpoints for mobile apps (request reset, confirm reset)
- Web views for browser-based password reset flow
- Email sending for reset links

Used by: api/urls.py and satlingo/urls.py for URL routing
Depends on: api/models.py (User, PasswordResetToken), api/forms.py
"""

import json
import logging
import smtplib

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import User, PasswordResetToken
from .forms import PasswordResetRequestForm, PasswordResetConfirmForm

logger = logging.getLogger(__name__)


def get_social_provider_display_name(user):
    """
    Get a human-readable display name for the user's social auth provider.

    Args:
        user: User instance

    Returns:
        str: Display name like "Google" or "Apple", or None if no social provider
    """
    providers = []
    if user.google_id:
        providers.append('Google')
    if user.apple_id:
        providers.append('Apple')

    if not providers:
        return None

    return ', '.join(providers)


def send_password_reset_email(user, reset_token):
    """
    Send password reset email to user.

    Args:
        user: User instance
        reset_token: PasswordResetToken instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'Reset Your Password - Keuvi'

    # Build reset URL
    site_url = getattr(settings, 'SITE_URL', 'https://keuvi.com')
    reset_url = f"{site_url}/accounts/password-reset-confirm/{reset_token.token}/"

    # Email content
    html_message = render_to_string('emails/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
        'expires_in': '24 hours'
    })

    plain_message = strip_tags(html_message)

    # Log attempt (no PII in logs - use user ID not email)
    logger.info(
        "Attempting to send password reset email",
        extra={
            'user_id': str(user.id),
        }
    )

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@keuvi.com'),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            "Password reset email sent successfully",
            extra={'user_id': str(user.id)}
        )
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP authentication failed",
            extra={
                'user_id': str(user.id),
                'error_code': getattr(e, 'smtp_code', None),
            }
        )
        return False
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(
            "SMTP recipient refused",
            extra={'user_id': str(user.id)}
        )
        return False
    except smtplib.SMTPException as e:
        logger.error(
            "SMTP error sending password reset email",
            extra={
                'user_id': str(user.id),
                'error_type': type(e).__name__,
            }
        )
        return False
    except Exception as e:
        logger.exception(
            "Unexpected error sending password reset email",
            extra={
                'user_id': str(user.id),
                'error_type': type(e).__name__,
            }
        )
        return False


# =============================================================================
# API Endpoints (for mobile apps)
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def api_password_reset_request(request):
    """
    API endpoint to request a password reset.

    POST body: { "email": "user@example.com" }

    Returns:
        200: { "message": "Password reset instructions sent" }
        400: { "error": {...} } if email not found or social-only account
    """
    email = request.data.get('email')

    if not email:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Email is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check for users with this email
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if email exists or not for security
        # But return success message anyway
        logger.info(f"Password reset requested for non-existent email")
        return Response({
            'message': 'If an account exists with this email, password reset instructions have been sent.'
        })
    except User.MultipleObjectsReturned:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Multiple accounts found. Please contact support.'}},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user signed up with social login (no password set)
    if not user.has_usable_password():
        provider_name = get_social_provider_display_name(user)
        return Response({
            'error': {
                'code': 'SOCIAL_LOGIN_USER',
                'message': (
                    f'You signed up with {provider_name}. Please use that method to sign in.'
                    if provider_name else
                    'You signed up with a social login provider. Please use that method to sign in.'
                ),
                'social_provider': provider_name,
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create reset token
    reset_token = PasswordResetToken.create_token(user)

    # Send email
    email_sent = send_password_reset_email(user, reset_token)

    if email_sent:
        return Response({
            'message': 'If an account exists with this email, password reset instructions have been sent.'
        })
    else:
        return Response(
            {'error': {'code': 'EMAIL_FAILED', 'message': 'Failed to send password reset email. Please try again later.'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def api_password_reset_confirm(request):
    """
    API endpoint to confirm a password reset.

    POST body: { "token": "...", "new_password": "..." }

    Returns:
        200: { "message": "Password reset successfully" }
        400: { "error": {...} } if token invalid or password validation fails
    """
    token = request.data.get('token')
    new_password = request.data.get('new_password')

    if not token or not new_password:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'Token and new password are required'}},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find and validate token
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return Response(
            {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired reset token'}},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not reset_token.is_valid():
        return Response(
            {'error': {'code': 'INVALID_TOKEN', 'message': 'Reset token is expired or already used'}},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate new password
    try:
        validate_password(new_password, reset_token.user)
    except ValidationError as e:
        return Response(
            {'error': {'code': 'WEAK_PASSWORD', 'message': '; '.join(e.messages)}},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Set new password
    user = reset_token.user
    user.set_password(new_password)
    user.save()

    # Mark token as used
    reset_token.is_used = True
    reset_token.save()

    logger.info(
        "Password reset completed successfully",
        extra={'user_id': str(user.id)}
    )

    return Response({'message': 'Password reset successfully'})


# =============================================================================
# Web Views (for browser-based reset flow)
# =============================================================================

def password_reset_request(request):
    """
    Web view to request a password reset.
    GET: Show form to enter email
    POST: Process form and send reset email
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Don't reveal if email exists - show success message anyway
                messages.success(request, 'If an account exists with this email, password reset instructions have been sent.')
                return redirect('web-index')
            except User.MultipleObjectsReturned:
                messages.error(request, 'Multiple accounts found with this email address. Please contact support.')
                return render(request, 'accounts/password_reset_request.html', {'form': form})

            # Check if user signed up with social login (no password set)
            if not user.has_usable_password():
                provider_name = get_social_provider_display_name(user)
                if provider_name:
                    messages.info(
                        request,
                        f'You signed up with {provider_name}. Please use that method to sign in. '
                        'If you would like to set a password, please sign in first and use your profile settings.'
                    )
                else:
                    messages.info(
                        request,
                        'You signed up with a social login provider. Please use that method to sign in. '
                        'If you would like to set a password, please sign in first and use your profile settings.'
                    )
                return render(request, 'accounts/password_reset_request.html', {'form': form})

            # Create reset token
            reset_token = PasswordResetToken.create_token(user)

            # Send email
            email_sent = send_password_reset_email(user, reset_token)

            if email_sent:
                messages.success(request, 'Password reset instructions have been sent to your email.')
                return redirect('web-index')
            else:
                messages.error(request, 'Unable to send password reset email. Please try again later.')
                return render(request, 'accounts/password_reset_request.html', {'form': form})
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset_request.html', {'form': form})


def password_reset_confirm(request, token):
    """
    Web view to confirm a password reset.
    GET: Show form to enter new password
    POST: Process form and reset password
    """
    try:
        reset_token = PasswordResetToken.objects.get(token=token)

        if not reset_token.is_valid():
            messages.error(request, 'This password reset link is invalid or has expired.')
            return redirect('password-reset-request')

        if request.method == 'POST':
            form = PasswordResetConfirmForm(reset_token.user, request.POST)
            if form.is_valid():
                form.save()
                reset_token.is_used = True
                reset_token.save()

                logger.info(
                    "Password reset completed via web",
                    extra={'user_id': str(reset_token.user.id)}
                )

                messages.success(request, 'Your password has been reset successfully. You can now log in.')
                return redirect('web-index')
        else:
            form = PasswordResetConfirmForm(reset_token.user)

        return render(request, 'accounts/password_reset_confirm.html', {'form': form, 'token': token})

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'This password reset link is invalid.')
        return redirect('password-reset-request')
