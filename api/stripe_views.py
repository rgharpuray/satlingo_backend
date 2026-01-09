import stripe
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from .models import User, Subscription

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create Stripe checkout session for premium subscription"""
    # Check configuration
    if not settings.STRIPE_SECRET_KEY:
        logger.error("STRIPE_SECRET_KEY not configured")
        return Response(
            {'error': {'code': 'CONFIG_ERROR', 'message': 'Stripe secret key not configured. Please contact support.'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    if not settings.STRIPE_PRICE_ID:
        logger.error("STRIPE_PRICE_ID not configured")
        return Response(
            {'error': {'code': 'CONFIG_ERROR', 'message': 'Stripe price ID not configured. Please contact support.'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    user = request.user
    
    # Validate user has email
    if not user.email:
        logger.error(f"User {user.id} does not have an email address")
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'User email is required for subscription'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            logger.info(f"Creating new Stripe customer for user {user.id} with email {user.email}")
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            user.save()
        else:
            logger.info(f"Retrieving existing Stripe customer {user.stripe_customer_id} for user {user.id}")
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
        
        # Create checkout session
        logger.info(f"Creating checkout session for customer {customer.id} with price {settings.STRIPE_PRICE_ID}")
        
        # Build absolute URLs for success and cancel
        # Force HTTPS in production (Heroku uses HTTPS)
        host = request.get_host()
        # Use HTTPS for production (keuvi.app), HTTP only for localhost
        if 'keuvi.app' in host or not settings.DEBUG:
            scheme = 'https'
        else:
            scheme = 'http'
        
        success_url = f"{scheme}://{host}/web/?from=subscription&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{scheme}://{host}/web/subscription/cancel"
        
        logger.info(f"Success URL: {success_url}")
        logger.info(f"Cancel URL: {cancel_url}")
        
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(user.id),
            },
        )
        
        logger.info(f"Checkout session created successfully: {checkout_session.id}")
        return Response({
            'session_id': checkout_session.id,
            'url': checkout_session.url,
        })
    
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe invalid request error: {str(e)}")
        # Check if it's a price ID issue
        if 'price' in str(e).lower() or 'No such price' in str(e):
            return Response(
                {'error': {'code': 'CONFIG_ERROR', 'message': f'Invalid Stripe price ID configured: {settings.STRIPE_PRICE_ID}. Please contact support.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'error': {'code': 'PAYMENT_ERROR', 'message': f'Invalid request: {str(e)}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)} (type: {type(e).__name__})")
        return Response(
            {'error': {'code': 'PAYMENT_ERROR', 'message': f'Payment error: {str(e)}'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {str(e)}", exc_info=True)
        return Response(
            {'error': {'code': 'INTERNAL_ERROR', 'message': 'An unexpected error occurred. Please try again.'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_subscription_from_stripe(request):
    """Manually sync subscription status from Stripe (useful if webhook didn't fire)"""
    user = request.user
    
    if not user.stripe_customer_id:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'No Stripe customer ID found'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get customer from Stripe
        customer = stripe.Customer.retrieve(user.stripe_customer_id)
        
        # Get all subscriptions for this customer
        subscriptions = stripe.Subscription.list(customer=customer.id, limit=10)
        
        # Find active subscriptions OR canceled subscriptions that are still within their period
        now = timezone.now()
        active_stripe_subs = []
        for sub in subscriptions.data:
            if sub.status in ['active', 'trialing']:
                active_stripe_subs.append(sub)
            elif sub.status == 'canceled':
                # Check if canceled subscription is still within its period
                period_end = timezone.datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
                if period_end > now:
                    # Canceled but still within period - treat as active
                    active_stripe_subs.append(sub)
        
        if active_stripe_subs:
            # Update with the most recent active subscription
            stripe_sub = active_stripe_subs[0]
            
            # Create or update subscription in database
            period_end = timezone.datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )
            
            sub, created = Subscription.objects.update_or_create(
                stripe_subscription_id=stripe_sub.id,
                defaults={
                    'user': user,
                    'status': stripe_sub.status,
                    'current_period_start': timezone.datetime.fromtimestamp(
                        stripe_sub.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': period_end,
                    'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
                }
            )
            
            # Set premium status - check if period has ended
            # Even if canceled (cancel_at_period_end=True), keep premium until period ends
            subscription_status = stripe_sub.status
            now = timezone.now()
            
            if subscription_status in ['active', 'trialing']:
                # Subscription is active - check if period has ended
                # Even if cancel_at_period_end=True, keep premium until period ends
                is_premium = (period_end > now) if period_end else True
            elif subscription_status == 'canceled':
                # Subscription is canceled - check if period has ended
                # Keep premium if period hasn't ended yet
                is_premium = (period_end > now) if period_end else False
            else:
                # Status is incomplete, past_due, etc. - remove premium
                is_premium = False
            
            user.is_premium = is_premium
            user.save()
            
            return Response({
                'success': True,
                'message': 'Subscription synced successfully',
                'subscription_status': stripe_sub.status,
                'is_premium': user.is_premium,
            })
        else:
            # No active subscriptions found
            user.is_premium = False
            user.save()
            
            return Response({
                'success': True,
                'message': 'No active subscriptions found',
                'is_premium': False,
            })
    
    except stripe.error.StripeError as e:
        return Response(
            {'error': {'code': 'STRIPE_ERROR', 'message': str(e)}},
            status=status.HTTP_400_BAD_REQUEST
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Log that we received a webhook request (before validation)
    logger.info(f"Webhook request received: method={request.method}, content_type={request.content_type}, has_signature={bool(sig_header)}")
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured - webhooks will fail!")
        return Response({'error': 'Webhook secret not configured'}, status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"✅ Received Stripe webhook: {event['type']} (id: {event.get('id')})")
    except ValueError as e:
        logger.error(f"❌ Invalid webhook payload: {str(e)}")
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Invalid webhook signature: {str(e)} - Check that STRIPE_WEBHOOK_SECRET matches Stripe dashboard")
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    try:
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
        
        logger.info(f"✅ Successfully processed webhook: {event['type']}")
    except Exception as e:
        logger.error(f"❌ Error handling webhook {event['type']}: {str(e)}", exc_info=True)
        return Response({'error': 'Webhook processing failed'}, status=500)
    
    return Response({'status': 'success'})


def handle_checkout_session(session):
    """Handle successful checkout"""
    user_id = session.get('metadata', {}).get('user_id')
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    
    logger.info(f"Processing checkout.session.completed: session_id={session.get('id')}, customer={customer_id}, subscription={subscription_id}")
    
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            
            # If we have a subscription ID from the session, try to process it immediately
            # This handles cases where the subscription.created webhook hasn't fired yet
            if subscription_id:
                try:
                    # Retrieve the subscription from Stripe to get its status
                    stripe_sub = stripe.Subscription.retrieve(subscription_id)
                    subscription_status = stripe_sub.status
                    
                    logger.info(f"Found subscription {subscription_id} in checkout session, status: {subscription_status}")
                    
                    # Create or update subscription record
                    sub, created = Subscription.objects.update_or_create(
                        stripe_subscription_id=subscription_id,
                        defaults={
                            'user': user,
                            'status': subscription_status,
                            'current_period_start': timezone.datetime.fromtimestamp(
                                stripe_sub.current_period_start, tz=timezone.utc
                            ),
                            'current_period_end': timezone.datetime.fromtimestamp(
                                stripe_sub.current_period_end, tz=timezone.utc
                            ),
                            'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
                        }
                    )
                    
                    # Set premium status immediately (active or trialing = premium)
                    is_premium = (subscription_status in ['active', 'trialing'])
                    user.is_premium = is_premium
                    user.save()
                    
                    logger.info(f"Checkout session processed: user {user.email}, subscription {subscription_id}, is_premium={is_premium}, created={created}")
                except stripe.error.StripeError as e:
                    logger.error(f"Error retrieving subscription {subscription_id} from Stripe: {str(e)}")
                    # Fallback: subscription will be created via subscription.created webhook
            elif customer_id:
                # If we have customer_id but no subscription_id, try to find active subscriptions
                try:
                    subscriptions = stripe.Subscription.list(customer=customer_id, limit=1, status='active')
                    if subscriptions.data:
                        stripe_sub = subscriptions.data[0]
                        subscription_status = stripe_sub.status
                        
                        sub, created = Subscription.objects.update_or_create(
                            stripe_subscription_id=stripe_sub.id,
                            defaults={
                                'user': user,
                                'status': subscription_status,
                                'current_period_start': timezone.datetime.fromtimestamp(
                                    stripe_sub.current_period_start, tz=timezone.utc
                                ),
                                'current_period_end': timezone.datetime.fromtimestamp(
                                    stripe_sub.current_period_end, tz=timezone.utc
                                ),
                                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
                            }
                        )
                        
                        is_premium = (subscription_status in ['active', 'trialing'])
                        user.is_premium = is_premium
                        user.save()
                        
                        logger.info(f"Checkout session processed via customer lookup: user {user.email}, subscription {stripe_sub.id}, is_premium={is_premium}")
                except stripe.error.StripeError as e:
                    logger.error(f"Error looking up subscriptions for customer {customer_id}: {str(e)}")
                    # Fallback: subscription will be created via subscription.created webhook
            else:
                logger.warning(f"Checkout session {session.get('id')} has no subscription_id or customer_id, waiting for subscription.created webhook")
        except User.DoesNotExist:
            logger.error(f"User not found for user_id: {user_id} in checkout.session.completed webhook")


def handle_subscription_created(subscription):
    """Handle new subscription"""
    customer_id = subscription['customer']
    subscription_id = subscription['id']
    subscription_status = subscription['status']
    
    logger.info(f"Processing subscription.created webhook: {subscription_id} for customer {customer_id}, status: {subscription_status}")
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # Create or update subscription record
        sub, created = Subscription.objects.update_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                'user': user,
                'status': subscription_status,
                'current_period_start': timezone.datetime.fromtimestamp(
                    subscription['current_period_start'], tz=timezone.utc
                ),
                'current_period_end': timezone.datetime.fromtimestamp(
                    subscription['current_period_end'], tz=timezone.utc
                ),
                'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
            }
        )
        
        # Set premium status based on subscription status (active, trialing = premium)
        is_premium = (subscription_status in ['active', 'trialing'])
        user.is_premium = is_premium
        user.save()
        
        logger.info(f"Subscription {subscription_id} processed: user {user.email}, is_premium={is_premium}, created={created}")
    except User.DoesNotExist:
        logger.error(f"User not found for customer_id: {customer_id} in subscription.created webhook")
    except Exception as e:
        logger.error(f"Error processing subscription.created webhook: {str(e)}", exc_info=True)


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
        # IMPORTANT: Premium should remain active until the END of the billing period they paid for
        # (current_period_end from when they first subscribed), NOT from the cancellation date
        # Even if canceled (cancel_at_period_end=True), keep premium until the original period ends
        subscription_status = subscription['status']
        period_end = sub.current_period_end  # This is the end of the period they originally paid for
        now = timezone.now()
        
        # Check if we're still within the billing period they paid for
        if period_end and period_end > now:
            # Still within the period they paid for - keep premium regardless of status
            # (Stripe keeps status as 'active' until period ends when cancel_at_period_end=True)
            is_premium = True
        else:
            # Period has ended - remove premium
            is_premium = False
        
        sub.user.is_premium = is_premium
        sub.user.save()
        
        logger.info(f"Subscription {subscription['id']} updated: status={subscription_status}, cancel_at_period_end={sub.cancel_at_period_end}, period_end={period_end}, is_premium={is_premium}")
    except Subscription.DoesNotExist:
        # Subscription doesn't exist yet, try to create it
        customer_id = subscription.get('customer')
        if customer_id:
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                sub, created = Subscription.objects.update_or_create(
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
                # Set premium status - check if period has ended
                subscription_status = subscription['status']
                period_end = timezone.datetime.fromtimestamp(
                    subscription['current_period_end'], tz=timezone.utc
                )
                now = timezone.now()
                
                if subscription_status in ['active', 'trialing']:
                    # Subscription is active - check if period has ended
                    is_premium = (period_end > now) if period_end else True
                else:
                    # Status is canceled, incomplete, etc. - remove premium
                    is_premium = False
                
                user.is_premium = is_premium
                user.save()
                
                logger.info(f"Subscription {subscription['id']} created via update: status={subscription_status}, period_end={period_end}, is_premium={is_premium}")
            except User.DoesNotExist:
                pass


def handle_subscription_deleted(subscription):
    """Handle subscription deletion (when period actually ends after cancellation)"""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=subscription['id'])
        sub.status = 'canceled'
        
        # Get period_end from the subscription object if available
        if 'current_period_end' in subscription:
            sub.current_period_end = timezone.datetime.fromtimestamp(
                subscription['current_period_end'], tz=timezone.utc
            )
        
        sub.save()
        
        # Check if period has actually ended
        # If period_end exists and hasn't passed, keep premium until it ends
        now = timezone.now()
        if sub.current_period_end and sub.current_period_end > now:
            # Period hasn't ended yet - keep premium until period_end
            is_premium = True
            logger.info(f"Subscription {subscription['id']} deleted but period hasn't ended yet (ends {sub.current_period_end}), keeping premium")
        else:
            # Period has ended - remove premium
            is_premium = False
            logger.info(f"Subscription {subscription['id']} deleted and period has ended, removing premium")
        
        sub.user.is_premium = is_premium
        sub.user.save()
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription {subscription.get('id')} not found in database when handling deletion")

