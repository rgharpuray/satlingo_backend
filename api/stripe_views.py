import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from .models import User, Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create Stripe checkout session for premium subscription"""
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': 'Stripe not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    user = request.user
    
    try:
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            user.save()
        else:
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/web/subscription/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.build_absolute_uri('/web/subscription/cancel'),
            metadata={
                'user_id': str(user.id),
            },
        )
        
        return Response({
            'session_id': checkout_session.id,
            'url': checkout_session.url,
        })
    
    except stripe.error.StripeError as e:
        return Response(
            {'error': {'code': 'PAYMENT_ERROR', 'message': str(e)}},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """Create Stripe customer portal session for managing subscription"""
    if not settings.STRIPE_SECRET_KEY:
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': 'Stripe not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    user = request.user
    
    if not user.stripe_customer_id:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'No active subscription'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.build_absolute_uri('/web/subscription'),
        )
        
        return Response({
            'url': portal_session.url,
        })
    
    except stripe.error.StripeError as e:
        return Response(
            {'error': {'code': 'PAYMENT_ERROR', 'message': str(e)}},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """Get user's subscription status"""
    user = request.user
    active_subscription = user.subscriptions.filter(status='active').first()
    
    if active_subscription:
        return Response({
            'has_subscription': True,
            'status': active_subscription.status,
            'current_period_end': active_subscription.current_period_end.isoformat(),
            'cancel_at_period_end': active_subscription.cancel_at_period_end,
        })
    
    return Response({
        'has_subscription': False,
        'status': None,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        return Response({'error': 'Webhook secret not configured'}, status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)
    
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        handle_subscription_created(subscription)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return Response({'status': 'success'})


def handle_checkout_session(session):
    """Handle successful checkout"""
    user_id = session.get('metadata', {}).get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            # Subscription will be created via subscription.created webhook
        except User.DoesNotExist:
            pass


def handle_subscription_created(subscription):
    """Handle new subscription"""
    customer_id = subscription['customer']
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        user.is_premium = True
        user.save()
        
        Subscription.objects.update_or_create(
            stripe_subscription_id=subscription['id'],
            defaults={
                'user': user,
                'status': subscription['status'],
                'current_period_start': timezone.datetime.fromtimestamp(
                    subscription['current_period_start'], tz=timezone.utc
                ),
                'current_period_end': timezone.datetime.fromtimestamp(
                    subscription['current_period_end'], tz=timezone.utc
                ),
                'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
            }
        )
    except User.DoesNotExist:
        pass


def handle_subscription_updated(subscription):
    """Handle subscription update"""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=subscription['id'])
        sub.status = subscription['status']
        sub.current_period_start = timezone.datetime.fromtimestamp(
            subscription['current_period_start'], tz=timezone.utc
        )
        sub.current_period_end = timezone.datetime.fromtimestamp(
            subscription['current_period_end'], tz=timezone.utc
        )
        sub.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        sub.save()
        
        # Update user premium status
        sub.user.is_premium = (sub.status == 'active')
        sub.user.save()
    except Subscription.DoesNotExist:
        pass


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=subscription['id'])
        sub.status = 'canceled'
        sub.save()
        
        # Remove premium status
        sub.user.is_premium = False
        sub.user.save()
    except Subscription.DoesNotExist:
        pass

