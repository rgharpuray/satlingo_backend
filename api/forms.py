"""
api/forms.py
Location: /Users/rishi/argosventures/satlingo_backend/api/forms.py

Django forms for the API app, primarily for web-based views.
Currently contains forms for password reset functionality.

Used by: api/password_reset_views.py
"""

from django import forms
from django.contrib.auth.forms import SetPasswordForm
from .models import User


class PasswordResetRequestForm(forms.Form):
    """Form to request a password reset by entering email address."""
    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
        })
    )


class PasswordResetConfirmForm(SetPasswordForm):
    """Form to set a new password during password reset."""
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password',
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        }),
    )
