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
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.InvalidRequestError as e:
                if 'No such customer' in str(e):
                    # Customer ID exists in DB but not in Stripe - create a new one
                    logger.warning(f"Customer {user.stripe_customer_id} not found in Stripe, creating new customer for user {user.id}")
                    customer = stripe.Customer.create(
                        email=user.email,
                        metadata={'user_id': str(user.id)}
                    )
                    user.stripe_customer_id = customer.id
                    user.save()
                    logger.info(f"Created new Stripe customer {customer.id} for user {user.id}")
                else:
                    raise
        
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


def get_subscription_field(sub, field, default=None):
    """Safely get a field from a Stripe subscription object (handles API version differences)"""
    result = default
    
    # Try dictionary access first (most common for webhook payloads)
    try:
        if field in sub:
            result = sub[field]
            if result is not None:
                return result
    except (TypeError, KeyError):
        pass
    
    # Try .get() method
    try:
        result = sub.get(field)
        if result is not None:
            return result
    except (AttributeError, TypeError):
        pass
    
    # Try attribute access (for Stripe objects)
    try:
        result = getattr(sub, field, None)
        if result is not None:
            return result
    except AttributeError:
        pass
    
    # For subscription objects in the new API version (2025-12-15.clover),
    # current_period_start and current_period_end are inside items.data[0]
    if field in ['current_period_start', 'current_period_end']:
        try:
            # Try to get from items.data[0] (new API structure)
            items = sub.get('items') if hasattr(sub, 'get') else getattr(sub, 'items', None)
            if items:
                items_data = items.get('data') if hasattr(items, 'get') else getattr(items, 'data', None)
                if items_data and len(items_data) > 0:
                    first_item = items_data[0]
                    item_result = first_item.get(field) if hasattr(first_item, 'get') else getattr(first_item, field, None)
                    if item_result is not None:
                        logger.info(f"Found {field}={item_result} in items.data[0]")
                        return item_result
        except (AttributeError, TypeError, KeyError, IndexError) as e:
            logger.debug(f"Error getting {field} from items: {e}")
        
        try:
            # Fallback: Check if there's a 'start_date' field (sometimes used instead)
            if field == 'current_period_start':
                start_date = sub.get('start_date') if hasattr(sub, 'get') else getattr(sub, 'start_date', None)
                if start_date:
                    return start_date
        except (AttributeError, TypeError):
            pass
    
    logger.debug(f"Could not find field '{field}' in subscription object, returning default: {default}")
    return default


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
            sub_status = get_subscription_field(sub, 'status')
            if sub_status in ['active', 'trialing']:
                active_stripe_subs.append(sub)
            elif sub_status == 'canceled':
                # Check if canceled subscription is still within its period
                period_end_ts = get_subscription_field(sub, 'current_period_end')
                if period_end_ts:
                    period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
                    if period_end > now:
                        # Canceled but still within period - treat as active
                        active_stripe_subs.append(sub)
        
        if active_stripe_subs:
            # Update with the most recent active subscription
            stripe_sub = active_stripe_subs[0]
            
            # Get subscription fields safely
            period_start_ts = get_subscription_field(stripe_sub, 'current_period_start')
            period_end_ts = get_subscription_field(stripe_sub, 'current_period_end')
            subscription_status = get_subscription_field(stripe_sub, 'status')
            cancel_at_period_end = get_subscription_field(stripe_sub, 'cancel_at_period_end', False)
            
            # Create or update subscription in database
            period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else None
            period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc) if period_start_ts else None
            
            sub, created = Subscription.objects.update_or_create(
                stripe_subscription_id=stripe_sub.id,
                defaults={
                    'user': user,
                    'status': subscription_status,
                    'current_period_start': period_start,
                    'current_period_end': period_end,
                    'cancel_at_period_end': cancel_at_period_end,
                }
            )
            
            # Set premium status - check if period has ended
            # Even if canceled (cancel_at_period_end=True), keep premium until period ends
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
                'subscription_status': subscription_status,
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
                    
                    # Log the raw subscription object for debugging
                    logger.info(f"Raw subscription object keys: {list(stripe_sub.keys()) if hasattr(stripe_sub, 'keys') else 'N/A'}")
                    logger.info(f"Raw subscription object: {dict(stripe_sub) if hasattr(stripe_sub, 'keys') else str(stripe_sub)[:500]}")
                    
                    subscription_status = get_subscription_field(stripe_sub, 'status')
                    period_start_ts = get_subscription_field(stripe_sub, 'current_period_start')
                    period_end_ts = get_subscription_field(stripe_sub, 'current_period_end')
                    cancel_at_period_end = get_subscription_field(stripe_sub, 'cancel_at_period_end', False)
                    
                    logger.info(f"Found subscription {subscription_id}: status={subscription_status}, period_start={period_start_ts}, period_end={period_end_ts}")
                    
                    # If period timestamps are missing, use current time as fallback
                    now = timezone.now()
                    if not period_start_ts:
                        logger.warning(f"No current_period_start found for subscription {subscription_id}, using current time")
                        period_start = now
                    else:
                        period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc)
                    
                    if not period_end_ts:
                        logger.warning(f"No current_period_end found for subscription {subscription_id}, using 30 days from now")
                        period_end = now + timezone.timedelta(days=30)
                    else:
                        period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
                    
                    # Create or update subscription record
                    sub, created = Subscription.objects.update_or_create(
                        stripe_subscription_id=subscription_id,
                        defaults={
                            'user': user,
                            'status': subscription_status,
                            'current_period_start': period_start,
                            'current_period_end': period_end,
                            'cancel_at_period_end': cancel_at_period_end,
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
                        subscription_status = get_subscription_field(stripe_sub, 'status')
                        period_start_ts = get_subscription_field(stripe_sub, 'current_period_start')
                        period_end_ts = get_subscription_field(stripe_sub, 'current_period_end')
                        cancel_at_period_end = get_subscription_field(stripe_sub, 'cancel_at_period_end', False)
                        
                        # If period timestamps are missing, use current time as fallback
                        now = timezone.now()
                        period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc) if period_start_ts else now
                        period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else (now + timezone.timedelta(days=30))
                        
                        sub, created = Subscription.objects.update_or_create(
                            stripe_subscription_id=stripe_sub.id,
                            defaults={
                                'user': user,
                                'status': subscription_status,
                                'current_period_start': period_start,
                                'current_period_end': period_end,
                                'cancel_at_period_end': cancel_at_period_end,
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
    customer_id = subscription.get('customer')
    subscription_id = subscription.get('id')
    subscription_status = subscription.get('status')
    period_start_ts = subscription.get('current_period_start')
    period_end_ts = subscription.get('current_period_end')
    cancel_at_period_end = subscription.get('cancel_at_period_end', False)
    
    logger.info(f"Processing subscription.created webhook: {subscription_id} for customer {customer_id}, status: {subscription_status}, period_start={period_start_ts}, period_end={period_end_ts}")
    
    try:
        user = User.objects.get(stripe_customer_id=customer_id)
        
        # If period timestamps are missing, use current time as fallback
        now = timezone.now()
        period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc) if period_start_ts else now
        period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else (now + timezone.timedelta(days=30))
        
        # Create or update subscription record
        sub, created = Subscription.objects.update_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                'user': user,
                'status': subscription_status,
                'current_period_start': period_start,
                'current_period_end': period_end,
                'cancel_at_period_end': cancel_at_period_end,
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
    subscription_id = subscription.get('id')
    subscription_status = subscription.get('status')
    period_start_ts = subscription.get('current_period_start')
    period_end_ts = subscription.get('current_period_end')
    cancel_at_period_end = subscription.get('cancel_at_period_end', False)
    
    try:
        sub = Subscription.objects.get(stripe_subscription_id=subscription_id)
        sub.status = subscription_status
        if period_start_ts:
            sub.current_period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc)
        if period_end_ts:
            sub.current_period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        sub.cancel_at_period_end = cancel_at_period_end
        sub.save()
        
        # Update user premium status
        # IMPORTANT: Premium should remain active until the END of the billing period they paid for
        # (current_period_end from when they first subscribed), NOT from the cancellation date
        # Even if canceled (cancel_at_period_end=True), keep premium until the original period ends
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
        
        logger.info(f"Subscription {subscription_id} updated: status={subscription_status}, cancel_at_period_end={cancel_at_period_end}, period_end={period_end}, is_premium={is_premium}")
    except Subscription.DoesNotExist:
        # Subscription doesn't exist yet, try to create it
        customer_id = subscription.get('customer')
        if customer_id:
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                
                # If period timestamps are missing, use current time as fallback
                now = timezone.now()
                period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else (now + timezone.timedelta(days=30))
                period_start = timezone.datetime.fromtimestamp(period_start_ts, tz=timezone.utc) if period_start_ts else now
                
                sub, created = Subscription.objects.update_or_create(
                    stripe_subscription_id=subscription_id,
                    defaults={
                        'user': user,
                        'status': subscription_status,
                        'current_period_start': period_start,
                        'current_period_end': period_end,
                        'cancel_at_period_end': cancel_at_period_end,
                    }
                )
                # Set premium status - check if period has ended
                if subscription_status in ['active', 'trialing']:
                    # Subscription is active - check if period has ended
                    is_premium = (period_end > now) if period_end else True
                else:
                    # Status is canceled, incomplete, etc. - remove premium
                    is_premium = False
                
                user.is_premium = is_premium
                user.save()
                
                logger.info(f"Subscription {subscription_id} created via update: status={subscription_status}, period_end={period_end}, is_premium={is_premium}")
            except User.DoesNotExist:
                pass


def handle_subscription_deleted(subscription):
    """Handle subscription deletion (when period actually ends after cancellation)"""
    subscription_id = subscription.get('id')
    period_end_ts = subscription.get('current_period_end')
    
    try:
        sub = Subscription.objects.get(stripe_subscription_id=subscription_id)
        sub.status = 'canceled'
        
        # Get period_end from the subscription object if available
        if period_end_ts:
            sub.current_period_end = timezone.datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        
        sub.save()
        
        # Check if period has actually ended
        # If period_end exists and hasn't passed, keep premium until it ends
        now = timezone.now()
        if sub.current_period_end and sub.current_period_end > now:
            # Period hasn't ended yet - keep premium until period_end
            is_premium = True
            logger.info(f"Subscription {subscription_id} deleted but period hasn't ended yet (ends {sub.current_period_end}), keeping premium")
        else:
            # Period has ended - remove premium
            is_premium = False
            logger.info(f"Subscription {subscription_id} deleted and period has ended, removing premium")
        
        sub.user.is_premium = is_premium
        sub.user.save()
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription {subscription_id} not found in database when handling deletion")

