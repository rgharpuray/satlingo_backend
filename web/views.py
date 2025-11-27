from django.shortcuts import render
from django.conf import settings


def index(request):
    """Main web app page"""
    return render(request, 'web/index.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


def subscription_success(request):
    """Stripe checkout success page"""
    session_id = request.GET.get('session_id')
    return render(request, 'web/subscription_success.html', {
        'session_id': session_id,
    })


def subscription_cancel(request):
    """Stripe checkout cancel page"""
    return render(request, 'web/subscription_cancel.html')


