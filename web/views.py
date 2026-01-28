from django.shortcuts import render
from django.conf import settings


def index(request):
    """Main web app page"""
    # Extract Sentry JS key from DSN (the key is the part before @)
    sentry_js_key = ''
    if settings.SENTRY_DSN:
        try:
            # DSN format: https://KEY@o123.ingest.sentry.io/PROJECT_ID
            sentry_js_key = settings.SENTRY_DSN.split('//')[1].split('@')[0]
        except (IndexError, AttributeError):
            pass
    
    return render(request, 'web/index.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'SENTRY_JS_KEY': sentry_js_key,
        'POSTHOG_API_KEY': getattr(settings, 'POSTHOG_API_KEY', ''),
        'POSTHOG_HOST': getattr(settings, 'POSTHOG_HOST', 'https://us.i.posthog.com'),
        'DEBUG': settings.DEBUG,
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


def terms(request):
    """Terms of Service"""
    return render(request, 'web/terms.html')


def privacy(request):
    """Privacy Policy"""
    return render(request, 'web/privacy.html')


def support(request):
    """Support / contact"""
    return render(request, 'web/support.html')

