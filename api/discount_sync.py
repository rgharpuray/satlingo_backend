"""
Stripe Discount Sync Service

Location: api/discount_sync.py
Summary: Handles bidirectional sync between DiscountCode model and Stripe API.
         Creates coupons and promotion codes in Stripe, updates active status,
         and fetches usage statistics.
Usage: Called by signal handlers in api/models.py when DiscountCode is saved/deleted.
       Also used by admin actions in api/admin.py for manual sync operations.
"""

import logging
import stripe
from django.conf import settings
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class DiscountSyncService:
    """
    Handles sync between DiscountCode model and Stripe API.

    All methods are static/class methods - no instance state needed.
    This keeps the service stateless and easy to test.
    """

    @staticmethod
    def create_in_stripe(discount_code) -> Tuple[str, str]:
        """
        Create coupon and promotion code in Stripe.

        Args:
            discount_code: DiscountCode model instance

        Returns:
            Tuple of (stripe_coupon_id, stripe_promotion_code_id)

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        logger.info(f"Creating Stripe coupon for discount code: {discount_code.code}")

        # Build coupon parameters
        coupon_params = {
            'name': discount_code.name,
            'duration': discount_code.duration,
            'metadata': {
                'discount_code_id': str(discount_code.id),
                'code': discount_code.code,
            }
        }

        # Set discount amount based on type
        if discount_code.discount_type == 'percent':
            coupon_params['percent_off'] = float(discount_code.percent_off)
        else:
            # Stripe expects amount in cents as integer
            coupon_params['amount_off'] = int(discount_code.amount_off)
            coupon_params['currency'] = 'usd'

        # Set duration_in_months for repeating coupons
        if discount_code.duration == 'repeating' and discount_code.duration_in_months:
            coupon_params['duration_in_months'] = discount_code.duration_in_months

        # Set max_redemptions if specified
        if discount_code.max_redemptions:
            coupon_params['max_redemptions'] = discount_code.max_redemptions

        # Set expiration if specified (Stripe uses Unix timestamp)
        if discount_code.expires_at:
            coupon_params['redeem_by'] = int(discount_code.expires_at.timestamp())

        # Create the coupon in Stripe
        logger.debug(f"Creating Stripe coupon with params: {coupon_params}")
        coupon = stripe.Coupon.create(**coupon_params)
        logger.info(f"Created Stripe coupon: {coupon.id}")

        # Build promotion code parameters
        # Note: Stripe API 2025+ requires coupon inside 'promotion' object with type
        promo_params = {
            'promotion': {
                'coupon': coupon.id,
                'type': 'coupon',
            },
            'code': discount_code.code,
            'active': discount_code.is_active,
            'metadata': {
                'discount_code_id': str(discount_code.id),
            }
        }

        # Set restrictions for first-time customers
        if discount_code.first_time_transaction:
            promo_params['restrictions'] = {
                'first_time_transaction': True
            }

        # Set max_redemptions on promo code (separate from coupon max)
        if discount_code.max_redemptions:
            promo_params['max_redemptions'] = discount_code.max_redemptions

        # Set expiration on promo code
        if discount_code.expires_at:
            promo_params['expires_at'] = int(discount_code.expires_at.timestamp())

        # Create the promotion code in Stripe
        logger.debug(f"Creating Stripe promotion code with params: {promo_params}")
        promotion_code = stripe.PromotionCode.create(**promo_params)
        logger.info(f"Created Stripe promotion code: {promotion_code.id}")

        return coupon.id, promotion_code.id

    @staticmethod
    def update_in_stripe(discount_code) -> None:
        """
        Update Stripe promotion code (mainly active status).

        Note: Stripe coupons are mostly immutable after creation.
        Only the promotion code's active status can be updated.
        For major changes (discount amount, duration, etc.),
        deactivate old code and create new one.

        Args:
            discount_code: DiscountCode model instance

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not discount_code.stripe_promotion_code_id:
            logger.warning(f"No Stripe promotion code ID for {discount_code.code}, skipping update")
            return

        logger.info(f"Updating Stripe promotion code {discount_code.stripe_promotion_code_id}: active={discount_code.is_active}")

        try:
            stripe.PromotionCode.modify(
                discount_code.stripe_promotion_code_id,
                active=discount_code.is_active,
                metadata={
                    'discount_code_id': str(discount_code.id),
                    'updated': 'true',
                }
            )
            logger.info(f"Updated Stripe promotion code {discount_code.stripe_promotion_code_id}")
        except stripe.error.InvalidRequestError as e:
            if 'No such promotion_code' in str(e):
                logger.warning(f"Promotion code {discount_code.stripe_promotion_code_id} not found in Stripe, may need to recreate")
            raise

    @staticmethod
    def deactivate_in_stripe(discount_code) -> None:
        """
        Deactivate promotion code in Stripe.

        Called before deletion to ensure code is no longer usable.
        Does not delete the Stripe objects (they may be referenced by existing subscriptions).

        Args:
            discount_code: DiscountCode model instance

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not discount_code.stripe_promotion_code_id:
            logger.warning(f"No Stripe promotion code ID for {discount_code.code}, skipping deactivation")
            return

        logger.info(f"Deactivating Stripe promotion code {discount_code.stripe_promotion_code_id}")

        try:
            stripe.PromotionCode.modify(
                discount_code.stripe_promotion_code_id,
                active=False,
                metadata={
                    'discount_code_id': str(discount_code.id),
                    'deactivated': 'true',
                }
            )
            logger.info(f"Deactivated Stripe promotion code {discount_code.stripe_promotion_code_id}")
        except stripe.error.InvalidRequestError as e:
            if 'No such promotion_code' in str(e):
                logger.warning(f"Promotion code {discount_code.stripe_promotion_code_id} not found in Stripe, already deleted or never created")
            else:
                raise

    @staticmethod
    def sync_usage_from_stripe(discount_code) -> int:
        """
        Fetch current redemption count from Stripe.

        Args:
            discount_code: DiscountCode model instance

        Returns:
            Current times_redeemed count from Stripe

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not discount_code.stripe_promotion_code_id:
            logger.warning(f"No Stripe promotion code ID for {discount_code.code}, cannot sync usage")
            return discount_code.times_redeemed

        logger.info(f"Fetching usage stats for promotion code {discount_code.stripe_promotion_code_id}")

        try:
            promo_code = stripe.PromotionCode.retrieve(discount_code.stripe_promotion_code_id)
            times_redeemed = promo_code.get('times_redeemed', 0)
            logger.info(f"Promotion code {discount_code.code} has been redeemed {times_redeemed} times")
            return times_redeemed
        except stripe.error.InvalidRequestError as e:
            if 'No such promotion_code' in str(e):
                logger.warning(f"Promotion code {discount_code.stripe_promotion_code_id} not found in Stripe")
                return discount_code.times_redeemed
            raise

    @staticmethod
    def validate_stripe_config() -> bool:
        """
        Validate that Stripe is properly configured.

        Returns:
            True if Stripe API key is configured and valid
        """
        if not settings.STRIPE_SECRET_KEY:
            logger.error("STRIPE_SECRET_KEY not configured")
            return False

        try:
            # Make a simple API call to validate the key
            stripe.Account.retrieve()
            return True
        except stripe.error.AuthenticationError:
            logger.error("Invalid STRIPE_SECRET_KEY")
            return False
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error during validation: {str(e)}")
            return False
