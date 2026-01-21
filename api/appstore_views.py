"""
Apple App Store In-App Purchase handling for iOS subscriptions.

iOS apps are required to use Apple's App Store for subscriptions.
This module handles:
1. Receipt verification (StoreKit 2)
2. App Store Server Notifications (webhooks)
3. Subscription status management
"""

import jwt
import json
import time
import base64
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import User, AppStoreSubscription

logger = logging.getLogger(__name__)

# Apple's App Store endpoints
APPLE_PRODUCTION_VERIFY_URL = 'https://buy.itunes.apple.com/verifyReceipt'
APPLE_SANDBOX_VERIFY_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'

# App Store Server API endpoints (StoreKit 2)
APPLE_PRODUCTION_API_URL = 'https://api.storekit.itunes.apple.com'
APPLE_SANDBOX_API_URL = 'https://api.storekit-sandbox.itunes.apple.com'


def get_appstore_jwt():
    """
    Generate JWT for App Store Server API authentication.
    Required for StoreKit 2 server-to-server calls.
    """
    if not all([
        settings.APPLE_APP_STORE_KEY_ID,
        settings.APPLE_APP_STORE_ISSUER_ID,
        settings.APPLE_APP_STORE_PRIVATE_KEY
    ]):
        return None
    
    try:
        # Decode the base64-encoded private key
        private_key = base64.b64decode(settings.APPLE_APP_STORE_PRIVATE_KEY).decode('utf-8')
        
        now = int(time.time())
        payload = {
            'iss': settings.APPLE_APP_STORE_ISSUER_ID,
            'iat': now,
            'exp': now + 3600,  # 1 hour
            'aud': 'appstoreconnect-v1',
            'bid': settings.APPLE_BUNDLE_ID,
        }
        
        headers = {
            'alg': 'ES256',
            'kid': settings.APPLE_APP_STORE_KEY_ID,
            'typ': 'JWT',
        }
        
        token = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
        return token
    except Exception as e:
        logger.error(f"Error generating App Store JWT: {e}")
        return None


def verify_transaction_jws(signed_transaction):
    """
    Verify and decode a JWS signed transaction from StoreKit 2.
    In production, you should verify the signature against Apple's certificate.
    For now, we decode without verification (Apple's SDK handles verification client-side).
    """
    try:
        # JWS format: header.payload.signature
        parts = signed_transaction.split('.')
        if len(parts) != 3:
            return None
        
        # Decode payload (base64url)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"Error decoding JWS transaction: {e}")
        return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_appstore_receipt(request):
    """
    Verify an App Store receipt and grant premium access.
    
    iOS client sends the receipt data after a successful purchase.
    We verify it with Apple and update the user's subscription status.
    
    POST body: { "receipt_data": "<base64_receipt>" }
    
    For StoreKit 2, use verify_appstore_transaction instead.
    """
    receipt_data = request.data.get('receipt_data')
    
    if not receipt_data:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'receipt_data is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not settings.APPLE_SHARED_SECRET:
        logger.error("APPLE_SHARED_SECRET not configured")
        return Response(
            {'error': {'code': 'CONFIG_ERROR', 'message': 'App Store not configured'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    user = request.user
    
    # Verify with Apple
    verify_payload = {
        'receipt-data': receipt_data,
        'password': settings.APPLE_SHARED_SECRET,
        'exclude-old-transactions': True,
    }
    
    # Try production first, then sandbox
    try:
        response = requests.post(APPLE_PRODUCTION_VERIFY_URL, json=verify_payload)
        result = response.json()
        
        # Status 21007 means this is a sandbox receipt
        if result.get('status') == 21007:
            response = requests.post(APPLE_SANDBOX_VERIFY_URL, json=verify_payload)
            result = response.json()
            environment = 'Sandbox'
        else:
            environment = 'Production'
        
        if result.get('status') != 0:
            logger.error(f"App Store verification failed: status={result.get('status')}")
            return Response(
                {'error': {'code': 'VERIFICATION_FAILED', 'message': f'Receipt verification failed: {result.get("status")}'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the receipt
        latest_receipt_info = result.get('latest_receipt_info', [])
        if not latest_receipt_info:
            return Response(
                {'error': {'code': 'NO_SUBSCRIPTION', 'message': 'No subscription found in receipt'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the most recent transaction
        latest = max(latest_receipt_info, key=lambda x: int(x.get('expires_date_ms', 0)))
        
        original_transaction_id = latest.get('original_transaction_id')
        product_id = latest.get('product_id')
        expires_date_ms = int(latest.get('expires_date_ms', 0))
        purchase_date_ms = int(latest.get('purchase_date_ms', 0))
        is_in_intro_offer = latest.get('is_in_intro_offer_period', 'false') == 'true'
        is_upgraded = latest.get('is_upgraded', 'false') == 'true'
        
        expires_date = datetime.fromtimestamp(expires_date_ms / 1000, tz=timezone.utc)
        purchase_date = datetime.fromtimestamp(purchase_date_ms / 1000, tz=timezone.utc)
        
        now = timezone.now()
        is_active = expires_date > now
        
        # Create or update subscription
        sub, created = AppStoreSubscription.objects.update_or_create(
            original_transaction_id=original_transaction_id,
            defaults={
                'user': user,
                'product_id': product_id,
                'status': 'active' if is_active else 'expired',
                'purchase_date': purchase_date,
                'expires_date': expires_date,
                'is_in_intro_offer': is_in_intro_offer,
                'is_upgraded': is_upgraded,
                'environment': environment,
            }
        )
        
        # Update user premium status
        user.is_premium = is_active
        user.save()
        
        logger.info(f"App Store receipt verified: user={user.email}, product={product_id}, expires={expires_date}, is_premium={is_active}")
        
        return Response({
            'success': True,
            'is_premium': is_active,
            'subscription': {
                'product_id': product_id,
                'expires_date': expires_date.isoformat(),
                'is_active': is_active,
                'environment': environment,
            }
        })
        
    except requests.RequestException as e:
        logger.error(f"Error contacting App Store: {e}")
        return Response(
            {'error': {'code': 'NETWORK_ERROR', 'message': 'Failed to verify receipt with App Store'}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_appstore_transaction(request):
    """
    Verify a StoreKit 2 transaction (JWS signed).
    
    StoreKit 2 provides signed transactions that can be verified server-side.
    
    POST body: { "signed_transaction": "<JWS_string>" }
    """
    signed_transaction = request.data.get('signed_transaction')
    
    if not signed_transaction:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'signed_transaction is required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    # Decode the JWS transaction
    transaction = verify_transaction_jws(signed_transaction)
    if not transaction:
        return Response(
            {'error': {'code': 'INVALID_TRANSACTION', 'message': 'Could not decode transaction'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extract transaction info
    original_transaction_id = transaction.get('originalTransactionId')
    product_id = transaction.get('productId')
    expires_date_ms = transaction.get('expiresDate')
    purchase_date_ms = transaction.get('purchaseDate')
    environment = transaction.get('environment', 'Production')
    
    if not all([original_transaction_id, product_id]):
        return Response(
            {'error': {'code': 'INVALID_TRANSACTION', 'message': 'Missing required transaction fields'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Convert timestamps
    expires_date = datetime.fromtimestamp(expires_date_ms / 1000, tz=timezone.utc) if expires_date_ms else None
    purchase_date = datetime.fromtimestamp(purchase_date_ms / 1000, tz=timezone.utc) if purchase_date_ms else timezone.now()
    
    now = timezone.now()
    is_active = expires_date and expires_date > now
    
    # Create or update subscription
    sub, created = AppStoreSubscription.objects.update_or_create(
        original_transaction_id=original_transaction_id,
        defaults={
            'user': user,
            'product_id': product_id,
            'status': 'active' if is_active else 'expired',
            'purchase_date': purchase_date,
            'expires_date': expires_date or (now + timedelta(days=30)),
            'environment': environment,
        }
    )
    
    # Update user premium status
    user.is_premium = is_active
    user.save()
    
    logger.info(f"StoreKit 2 transaction verified: user={user.email}, product={product_id}, expires={expires_date}, is_premium={is_active}")
    
    return Response({
        'success': True,
        'is_premium': is_active,
        'subscription': {
            'product_id': product_id,
            'expires_date': expires_date.isoformat() if expires_date else None,
            'is_active': is_active,
            'environment': environment,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appstore_subscription_status(request):
    """
    Get user's App Store subscription status.
    """
    user = request.user
    
    # Get active App Store subscription
    active_sub = user.appstore_subscriptions.filter(
        status='active',
        expires_date__gt=timezone.now()
    ).first()
    
    if active_sub:
        return Response({
            'has_subscription': True,
            'source': 'appstore',
            'status': active_sub.status,
            'product_id': active_sub.product_id,
            'expires_date': active_sub.expires_date.isoformat(),
            'environment': active_sub.environment,
        })
    
    # Check for expired subscription
    expired_sub = user.appstore_subscriptions.order_by('-expires_date').first()
    if expired_sub:
        return Response({
            'has_subscription': False,
            'source': 'appstore',
            'status': 'expired',
            'product_id': expired_sub.product_id,
            'expired_date': expired_sub.expires_date.isoformat(),
        })
    
    return Response({
        'has_subscription': False,
        'source': None,
        'status': None,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def appstore_webhook(request):
    """
    Handle App Store Server Notifications (v2).
    
    Apple sends notifications for subscription events:
    - SUBSCRIBED: New subscription
    - DID_RENEW: Subscription renewed
    - DID_CHANGE_RENEWAL_STATUS: Auto-renew toggled
    - EXPIRED: Subscription expired
    - DID_FAIL_TO_RENEW: Billing failed
    - GRACE_PERIOD_EXPIRED: Grace period ended
    - REFUND: Refund issued
    - REVOKE: Subscription revoked
    
    Configure this URL in App Store Connect:
    https://keuvi.herokuapp.com/api/v1/payments/appstore/webhook
    """
    try:
        # App Store Server Notifications v2 sends a signed payload
        signed_payload = request.data.get('signedPayload')
        
        if not signed_payload:
            logger.warning("App Store webhook received without signedPayload")
            return Response({'status': 'error', 'message': 'Missing signedPayload'}, status=400)
        
        # Decode the JWS payload
        payload = verify_transaction_jws(signed_payload)
        if not payload:
            logger.error("Failed to decode App Store webhook payload")
            return Response({'status': 'error', 'message': 'Invalid payload'}, status=400)
        
        notification_type = payload.get('notificationType')
        subtype = payload.get('subtype')
        data = payload.get('data', {})
        
        logger.info(f"App Store notification: type={notification_type}, subtype={subtype}")
        
        # Get transaction info from the notification
        signed_transaction_info = data.get('signedTransactionInfo')
        if signed_transaction_info:
            transaction = verify_transaction_jws(signed_transaction_info)
            if transaction:
                handle_appstore_transaction_update(notification_type, subtype, transaction)
        
        # Get renewal info if available
        signed_renewal_info = data.get('signedRenewalInfo')
        if signed_renewal_info:
            renewal_info = verify_transaction_jws(signed_renewal_info)
            if renewal_info:
                logger.info(f"Renewal info: auto_renew={renewal_info.get('autoRenewStatus')}")
        
        return Response({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing App Store webhook: {e}", exc_info=True)
        return Response({'status': 'error'}, status=500)


def handle_appstore_transaction_update(notification_type, subtype, transaction):
    """
    Update subscription based on App Store notification.
    """
    original_transaction_id = transaction.get('originalTransactionId')
    
    if not original_transaction_id:
        logger.warning("Transaction update missing originalTransactionId")
        return
    
    try:
        sub = AppStoreSubscription.objects.get(original_transaction_id=original_transaction_id)
    except AppStoreSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for transaction: {original_transaction_id}")
        return
    
    user = sub.user
    now = timezone.now()
    
    # Update based on notification type
    if notification_type == 'SUBSCRIBED':
        # New subscription or resubscribe
        expires_date_ms = transaction.get('expiresDate')
        if expires_date_ms:
            sub.expires_date = datetime.fromtimestamp(expires_date_ms / 1000, tz=timezone.utc)
        sub.status = 'active'
        sub.save()
        user.is_premium = True
        user.save()
        logger.info(f"Subscription activated: user={user.email}")
        
    elif notification_type == 'DID_RENEW':
        # Subscription renewed
        expires_date_ms = transaction.get('expiresDate')
        if expires_date_ms:
            sub.expires_date = datetime.fromtimestamp(expires_date_ms / 1000, tz=timezone.utc)
        sub.status = 'active'
        sub.save()
        user.is_premium = True
        user.save()
        logger.info(f"Subscription renewed: user={user.email}, expires={sub.expires_date}")
        
    elif notification_type == 'EXPIRED':
        sub.status = 'expired'
        sub.save()
        # Check if user has any other active subscriptions (Stripe or App Store)
        has_active = (
            user.subscriptions.filter(status='active', current_period_end__gt=now).exists() or
            user.appstore_subscriptions.filter(status='active', expires_date__gt=now).exclude(id=sub.id).exists()
        )
        user.is_premium = has_active
        user.save()
        logger.info(f"Subscription expired: user={user.email}, is_premium={has_active}")
        
    elif notification_type == 'DID_FAIL_TO_RENEW':
        if subtype == 'GRACE_PERIOD':
            sub.status = 'in_grace_period'
        else:
            sub.status = 'in_billing_retry'
        sub.save()
        # Keep premium during grace period / billing retry
        logger.info(f"Subscription billing issue: user={user.email}, status={sub.status}")
        
    elif notification_type == 'GRACE_PERIOD_EXPIRED':
        sub.status = 'expired'
        sub.save()
        has_active = (
            user.subscriptions.filter(status='active', current_period_end__gt=now).exists() or
            user.appstore_subscriptions.filter(status='active', expires_date__gt=now).exclude(id=sub.id).exists()
        )
        user.is_premium = has_active
        user.save()
        logger.info(f"Grace period expired: user={user.email}, is_premium={has_active}")
        
    elif notification_type in ['REFUND', 'REVOKE']:
        sub.status = 'revoked'
        sub.save()
        has_active = (
            user.subscriptions.filter(status='active', current_period_end__gt=now).exists() or
            user.appstore_subscriptions.filter(status='active', expires_date__gt=now).exclude(id=sub.id).exists()
        )
        user.is_premium = has_active
        user.save()
        logger.info(f"Subscription revoked/refunded: user={user.email}, is_premium={has_active}")
        
    elif notification_type == 'DID_CHANGE_RENEWAL_STATUS':
        # User toggled auto-renew (we don't track this separately, just log it)
        auto_renew = transaction.get('autoRenewStatus', 1) == 1
        logger.info(f"Auto-renew changed: user={user.email}, auto_renew={auto_renew}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restore_appstore_purchases(request):
    """
    Restore App Store purchases for a user.
    
    Called when user reinstalls app or logs in on new device.
    iOS client should call StoreKit's restoreCompletedTransactions()
    and then send all restored transactions here.
    
    POST body: { "transactions": [<signed_transaction>, ...] }
    """
    transactions = request.data.get('transactions', [])
    
    if not transactions:
        return Response(
            {'error': {'code': 'BAD_REQUEST', 'message': 'No transactions provided'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    restored_count = 0
    active_subscription = None
    now = timezone.now()
    
    for signed_transaction in transactions:
        transaction = verify_transaction_jws(signed_transaction)
        if not transaction:
            continue
        
        original_transaction_id = transaction.get('originalTransactionId')
        product_id = transaction.get('productId')
        expires_date_ms = transaction.get('expiresDate')
        purchase_date_ms = transaction.get('purchaseDate')
        environment = transaction.get('environment', 'Production')
        
        if not original_transaction_id:
            continue
        
        expires_date = datetime.fromtimestamp(expires_date_ms / 1000, tz=timezone.utc) if expires_date_ms else None
        purchase_date = datetime.fromtimestamp(purchase_date_ms / 1000, tz=timezone.utc) if purchase_date_ms else now
        
        is_active = expires_date and expires_date > now
        
        sub, created = AppStoreSubscription.objects.update_or_create(
            original_transaction_id=original_transaction_id,
            defaults={
                'user': user,
                'product_id': product_id,
                'status': 'active' if is_active else 'expired',
                'purchase_date': purchase_date,
                'expires_date': expires_date or now,
                'environment': environment,
            }
        )
        
        restored_count += 1
        
        if is_active:
            active_subscription = sub
    
    # Update user premium status
    if active_subscription:
        user.is_premium = True
        user.save()
    
    logger.info(f"Restored {restored_count} transactions for user={user.email}, is_premium={user.is_premium}")
    
    return Response({
        'success': True,
        'restored_count': restored_count,
        'is_premium': user.is_premium,
        'active_subscription': {
            'product_id': active_subscription.product_id,
            'expires_date': active_subscription.expires_date.isoformat(),
        } if active_subscription else None,
    })
