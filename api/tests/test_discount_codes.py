"""
Unit tests for DiscountCode model and DiscountSyncService.

Location: api/tests/test_discount_codes.py
Coverage: DiscountCode model validation, business logic, and Stripe sync service.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from api.models import DiscountCode
from api.discount_sync import DiscountSyncService


class DiscountCodeModelTests(TestCase):
    """Tests for DiscountCode model creation and validation."""

    def test_create_percentage_discount(self):
        """Test creating a discount code with percentage off."""
        # Arrange / Act - disconnect signal to avoid Stripe calls
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='PERCENT20',
                name='20% Off',
                discount_type='percent',
                percent_off=Decimal('20.00'),
                duration='forever',
                is_active=True
            )

        # Assert
        self.assertEqual(code.code, 'PERCENT20')
        self.assertEqual(code.discount_type, 'percent')
        self.assertEqual(code.percent_off, Decimal('20.00'))
        self.assertIsNone(code.amount_off)
        self.assertEqual(code.duration, 'forever')
        self.assertTrue(code.is_active)

    def test_create_fixed_amount_discount(self):
        """Test creating a discount code with fixed amount off."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='SAVE500',
                name='$5 Off',
                discount_type='amount',
                amount_off=Decimal('500.00'),  # 500 cents = $5
                duration='once',
                is_active=True
            )

        # Assert
        self.assertEqual(code.code, 'SAVE500')
        self.assertEqual(code.discount_type, 'amount')
        self.assertEqual(code.amount_off, Decimal('500.00'))
        self.assertIsNone(code.percent_off)
        self.assertEqual(code.duration, 'once')

    def test_validation_percent_discount_requires_percent_off(self):
        """Test that percent discount type requires percent_off value."""
        code = DiscountCode(
            code='INVALID1',
            name='Invalid Percent',
            discount_type='percent',
            percent_off=None,  # Missing required field
            duration='forever'
        )

        with self.assertRaises(ValidationError) as context:
            code.clean()

        self.assertIn('Percentage off is required', str(context.exception))

    def test_validation_amount_discount_requires_amount_off(self):
        """Test that amount discount type requires amount_off value."""
        code = DiscountCode(
            code='INVALID2',
            name='Invalid Amount',
            discount_type='amount',
            amount_off=None,  # Missing required field
            duration='forever'
        )

        with self.assertRaises(ValidationError) as context:
            code.clean()

        self.assertIn('Amount off is required', str(context.exception))

    def test_validation_repeating_duration_requires_months(self):
        """Test that repeating duration requires duration_in_months."""
        code = DiscountCode(
            code='REPEAT1',
            name='Repeating Discount',
            discount_type='percent',
            percent_off=Decimal('15.00'),
            duration='repeating',
            duration_in_months=None  # Missing required field
        )

        with self.assertRaises(ValidationError) as context:
            code.clean()

        self.assertIn('Duration in months is required', str(context.exception))

    def test_str_percentage_discount(self):
        """Test string representation for percentage discount."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode(
                code='TEST25',
                name='25% Off',
                discount_type='percent',
                percent_off=Decimal('25.00'),
                duration='forever'
            )

        self.assertEqual(str(code), 'TEST25 (25.00% off)')

    def test_str_fixed_amount_discount(self):
        """Test string representation for fixed amount discount."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode(
                code='SAVE10',
                name='$10 Off',
                discount_type='amount',
                amount_off=Decimal('1000.00'),  # 1000 cents = $10
                duration='forever'
            )

        self.assertEqual(str(code), 'SAVE10 ($10.00 off)')


class DiscountCodeIsValidTests(TestCase):
    """Tests for DiscountCode.is_valid() method."""

    def test_is_valid_active_unexpired(self):
        """Test that active, unexpired code is valid."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='VALID1',
                name='Valid Code',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=True,
                expires_at=None,
                max_redemptions=None
            )

        self.assertTrue(code.is_valid())

    def test_is_valid_inactive_code(self):
        """Test that inactive code is not valid."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='INACTIVE1',
                name='Inactive Code',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=False
            )

        self.assertFalse(code.is_valid())

    def test_is_valid_expired_code(self):
        """Test that expired code is not valid."""
        past_date = timezone.now() - timedelta(days=1)
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='EXPIRED1',
                name='Expired Code',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=True,
                expires_at=past_date
            )

        self.assertFalse(code.is_valid())

    def test_is_valid_future_expiration(self):
        """Test that code with future expiration is valid."""
        future_date = timezone.now() + timedelta(days=30)
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='FUTURE1',
                name='Future Expiration',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=True,
                expires_at=future_date
            )

        self.assertTrue(code.is_valid())

    def test_is_valid_maxed_out(self):
        """Test that code at max redemptions is not valid."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='MAXED1',
                name='Maxed Out Code',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=True,
                max_redemptions=10,
                times_redeemed=10
            )

        self.assertFalse(code.is_valid())

    def test_is_valid_under_max_redemptions(self):
        """Test that code under max redemptions is valid."""
        with patch('api.models.sync_discount_code_to_stripe'):
            code = DiscountCode.objects.create(
                code='UNDERMAX1',
                name='Under Max',
                discount_type='percent',
                percent_off=Decimal('10.00'),
                duration='forever',
                is_active=True,
                max_redemptions=10,
                times_redeemed=5
            )

        self.assertTrue(code.is_valid())


class DiscountSyncServiceCreateTests(TestCase):
    """Tests for DiscountSyncService.create_in_stripe method."""

    def setUp(self):
        """Set up test data."""
        # Disconnect signal to prevent automatic Stripe sync
        self.patcher = patch('api.models.sync_discount_code_to_stripe')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_percent_discount(self, mock_coupon_create, mock_promo_create):
        """Test creating a percentage discount in Stripe."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_test123')
        mock_promo_create.return_value = MagicMock(id='promo_test123')

        code = DiscountCode(
            id=uuid.uuid4(),
            code='STRIPE20',
            name='20% Stripe Discount',
            discount_type='percent',
            percent_off=Decimal('20.00'),
            duration='forever',
            is_active=True
        )

        # Act
        coupon_id, promo_id = DiscountSyncService.create_in_stripe(code)

        # Assert
        self.assertEqual(coupon_id, 'coupon_test123')
        self.assertEqual(promo_id, 'promo_test123')

        # Verify coupon creation call
        mock_coupon_create.assert_called_once()
        coupon_args = mock_coupon_create.call_args[1]
        self.assertEqual(coupon_args['name'], '20% Stripe Discount')
        self.assertEqual(coupon_args['percent_off'], 20.0)
        self.assertEqual(coupon_args['duration'], 'forever')
        self.assertNotIn('amount_off', coupon_args)

        # Verify promo code creation call
        mock_promo_create.assert_called_once()
        promo_args = mock_promo_create.call_args[1]
        self.assertEqual(promo_args['coupon'], 'coupon_test123')
        self.assertEqual(promo_args['code'], 'STRIPE20')
        self.assertTrue(promo_args['active'])

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_fixed_amount_discount(self, mock_coupon_create, mock_promo_create):
        """Test creating a fixed amount discount in Stripe."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_fixed123')
        mock_promo_create.return_value = MagicMock(id='promo_fixed123')

        code = DiscountCode(
            id=uuid.uuid4(),
            code='SAVE1000',
            name='$10 Off',
            discount_type='amount',
            amount_off=Decimal('1000'),  # 1000 cents
            duration='once',
            is_active=True
        )

        # Act
        coupon_id, promo_id = DiscountSyncService.create_in_stripe(code)

        # Assert
        self.assertEqual(coupon_id, 'coupon_fixed123')
        self.assertEqual(promo_id, 'promo_fixed123')

        # Verify coupon creation call
        coupon_args = mock_coupon_create.call_args[1]
        self.assertEqual(coupon_args['amount_off'], 1000)
        self.assertEqual(coupon_args['currency'], 'usd')
        self.assertNotIn('percent_off', coupon_args)

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_with_max_redemptions(self, mock_coupon_create, mock_promo_create):
        """Test creating a discount with max redemptions."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_max123')
        mock_promo_create.return_value = MagicMock(id='promo_max123')

        code = DiscountCode(
            id=uuid.uuid4(),
            code='LIMITED100',
            name='Limited Use',
            discount_type='percent',
            percent_off=Decimal('15.00'),
            duration='forever',
            is_active=True,
            max_redemptions=100
        )

        # Act
        DiscountSyncService.create_in_stripe(code)

        # Assert
        coupon_args = mock_coupon_create.call_args[1]
        self.assertEqual(coupon_args['max_redemptions'], 100)

        promo_args = mock_promo_create.call_args[1]
        self.assertEqual(promo_args['max_redemptions'], 100)

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_with_expiration(self, mock_coupon_create, mock_promo_create):
        """Test creating a discount with expiration date."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_exp123')
        mock_promo_create.return_value = MagicMock(id='promo_exp123')

        expires_at = timezone.now() + timedelta(days=30)
        code = DiscountCode(
            id=uuid.uuid4(),
            code='EXPIRING',
            name='Expiring Code',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            expires_at=expires_at
        )

        # Act
        DiscountSyncService.create_in_stripe(code)

        # Assert
        coupon_args = mock_coupon_create.call_args[1]
        self.assertEqual(coupon_args['redeem_by'], int(expires_at.timestamp()))

        promo_args = mock_promo_create.call_args[1]
        self.assertEqual(promo_args['expires_at'], int(expires_at.timestamp()))

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_first_time_customer(self, mock_coupon_create, mock_promo_create):
        """Test creating a first-time customer only discount."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_first123')
        mock_promo_create.return_value = MagicMock(id='promo_first123')

        code = DiscountCode(
            id=uuid.uuid4(),
            code='NEWUSER',
            name='New User Discount',
            discount_type='percent',
            percent_off=Decimal('25.00'),
            duration='forever',
            is_active=True,
            first_time_transaction=True
        )

        # Act
        DiscountSyncService.create_in_stripe(code)

        # Assert
        promo_args = mock_promo_create.call_args[1]
        self.assertIn('restrictions', promo_args)
        self.assertTrue(promo_args['restrictions']['first_time_transaction'])

    @patch('api.discount_sync.stripe.PromotionCode.create')
    @patch('api.discount_sync.stripe.Coupon.create')
    def test_create_in_stripe_repeating_duration(self, mock_coupon_create, mock_promo_create):
        """Test creating a repeating duration discount."""
        # Arrange
        mock_coupon_create.return_value = MagicMock(id='coupon_repeat123')
        mock_promo_create.return_value = MagicMock(id='promo_repeat123')

        code = DiscountCode(
            id=uuid.uuid4(),
            code='REPEAT3',
            name='3 Month Discount',
            discount_type='percent',
            percent_off=Decimal('20.00'),
            duration='repeating',
            duration_in_months=3,
            is_active=True
        )

        # Act
        DiscountSyncService.create_in_stripe(code)

        # Assert
        coupon_args = mock_coupon_create.call_args[1]
        self.assertEqual(coupon_args['duration'], 'repeating')
        self.assertEqual(coupon_args['duration_in_months'], 3)


class DiscountSyncServiceUpdateTests(TestCase):
    """Tests for DiscountSyncService.update_in_stripe method."""

    def setUp(self):
        """Set up test data."""
        self.patcher = patch('api.models.sync_discount_code_to_stripe')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_update_in_stripe_active_status(self, mock_promo_modify):
        """Test updating promotion code active status."""
        # Arrange
        code = DiscountCode(
            id=uuid.uuid4(),
            code='UPDATE1',
            name='Update Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=False,
            stripe_promotion_code_id='promo_update123'
        )

        # Act
        DiscountSyncService.update_in_stripe(code)

        # Assert
        mock_promo_modify.assert_called_once_with(
            'promo_update123',
            active=False,
            metadata={
                'discount_code_id': str(code.id),
                'updated': 'true',
            }
        )

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_update_in_stripe_no_promo_id_skips(self, mock_promo_modify):
        """Test that update is skipped when no Stripe promo ID exists."""
        # Arrange
        code = DiscountCode(
            id=uuid.uuid4(),
            code='NOPROMO',
            name='No Promo ID',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id=None
        )

        # Act
        DiscountSyncService.update_in_stripe(code)

        # Assert
        mock_promo_modify.assert_not_called()

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_update_in_stripe_handles_not_found(self, mock_promo_modify):
        """Test handling of Stripe 'not found' error."""
        import stripe

        # Arrange
        mock_promo_modify.side_effect = stripe.error.InvalidRequestError(
            message='No such promotion_code: promo_notfound',
            param=None
        )

        code = DiscountCode(
            id=uuid.uuid4(),
            code='NOTFOUND',
            name='Not Found',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id='promo_notfound'
        )

        # Act & Assert - should re-raise the error
        with self.assertRaises(stripe.error.InvalidRequestError):
            DiscountSyncService.update_in_stripe(code)


class DiscountSyncServiceDeactivateTests(TestCase):
    """Tests for DiscountSyncService.deactivate_in_stripe method."""

    def setUp(self):
        """Set up test data."""
        self.patcher = patch('api.models.sync_discount_code_to_stripe')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_deactivate_in_stripe(self, mock_promo_modify):
        """Test deactivating promotion code in Stripe."""
        # Arrange
        code = DiscountCode(
            id=uuid.uuid4(),
            code='DEACTIVATE1',
            name='Deactivate Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id='promo_deactivate123'
        )

        # Act
        DiscountSyncService.deactivate_in_stripe(code)

        # Assert
        mock_promo_modify.assert_called_once_with(
            'promo_deactivate123',
            active=False,
            metadata={
                'discount_code_id': str(code.id),
                'deactivated': 'true',
            }
        )

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_deactivate_in_stripe_no_promo_id_skips(self, mock_promo_modify):
        """Test that deactivation is skipped when no Stripe promo ID exists."""
        # Arrange
        code = DiscountCode(
            id=uuid.uuid4(),
            code='NODEACTIVATE',
            name='No Promo ID',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id=None
        )

        # Act
        DiscountSyncService.deactivate_in_stripe(code)

        # Assert
        mock_promo_modify.assert_not_called()

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_deactivate_in_stripe_handles_not_found_gracefully(self, mock_promo_modify):
        """Test that 'not found' error is handled gracefully during deactivation."""
        import stripe

        # Arrange
        mock_promo_modify.side_effect = stripe.error.InvalidRequestError(
            message='No such promotion_code: promo_gone',
            param=None
        )

        code = DiscountCode(
            id=uuid.uuid4(),
            code='GONE',
            name='Already Gone',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id='promo_gone'
        )

        # Act - should NOT raise, just log warning
        DiscountSyncService.deactivate_in_stripe(code)  # Should not raise

        # Assert
        mock_promo_modify.assert_called_once()

    @patch('api.discount_sync.stripe.PromotionCode.modify')
    def test_deactivate_in_stripe_reraises_other_errors(self, mock_promo_modify):
        """Test that non-'not found' errors are re-raised."""
        import stripe

        # Arrange
        mock_promo_modify.side_effect = stripe.error.InvalidRequestError(
            message='Some other Stripe error',
            param=None
        )

        code = DiscountCode(
            id=uuid.uuid4(),
            code='ERROR',
            name='Error Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id='promo_error'
        )

        # Act & Assert
        with self.assertRaises(stripe.error.InvalidRequestError):
            DiscountSyncService.deactivate_in_stripe(code)


class DiscountSyncServiceUsageTests(TestCase):
    """Tests for DiscountSyncService.sync_usage_from_stripe method."""

    def setUp(self):
        """Set up test data."""
        self.patcher = patch('api.models.sync_discount_code_to_stripe')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('api.discount_sync.stripe.PromotionCode.retrieve')
    def test_sync_usage_from_stripe(self, mock_promo_retrieve):
        """Test fetching usage stats from Stripe."""
        # Arrange
        mock_promo_retrieve.return_value = {'times_redeemed': 42}

        code = DiscountCode(
            id=uuid.uuid4(),
            code='USAGE1',
            name='Usage Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id='promo_usage123',
            times_redeemed=0
        )

        # Act
        result = DiscountSyncService.sync_usage_from_stripe(code)

        # Assert
        self.assertEqual(result, 42)
        mock_promo_retrieve.assert_called_once_with('promo_usage123')

    @patch('api.discount_sync.stripe.PromotionCode.retrieve')
    def test_sync_usage_no_promo_id_returns_current(self, mock_promo_retrieve):
        """Test that sync returns current count when no Stripe promo ID."""
        # Arrange
        code = DiscountCode(
            id=uuid.uuid4(),
            code='NOUSAGE',
            name='No Usage',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True,
            stripe_promotion_code_id=None,
            times_redeemed=5
        )

        # Act
        result = DiscountSyncService.sync_usage_from_stripe(code)

        # Assert
        self.assertEqual(result, 5)
        mock_promo_retrieve.assert_not_called()


class DiscountCodeSignalTests(TestCase):
    """Tests for DiscountCode signal handlers (post_save, pre_delete)."""

    @patch('api.discount_sync.DiscountSyncService.create_in_stripe')
    def test_post_save_signal_on_create(self, mock_create):
        """Test that post_save signal triggers Stripe sync on creation."""
        # Arrange
        mock_create.return_value = ('coupon_signal123', 'promo_signal123')

        # Act
        code = DiscountCode.objects.create(
            code='SIGNAL1',
            name='Signal Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True
        )

        # Assert
        mock_create.assert_called_once()

        # Refresh to get updated Stripe IDs
        code.refresh_from_db()
        self.assertEqual(code.stripe_coupon_id, 'coupon_signal123')
        self.assertEqual(code.stripe_promotion_code_id, 'promo_signal123')

    @patch('api.discount_sync.DiscountSyncService.update_in_stripe')
    @patch('api.discount_sync.DiscountSyncService.create_in_stripe')
    def test_post_save_signal_on_update(self, mock_create, mock_update):
        """Test that post_save signal triggers update on existing code."""
        # Arrange
        mock_create.return_value = ('coupon_update1', 'promo_update1')

        code = DiscountCode.objects.create(
            code='SIGNALUPD',
            name='Signal Update Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True
        )

        # Reset mock after creation
        mock_create.reset_mock()
        mock_update.reset_mock()

        # Act - update the code
        code.is_active = False
        code.save()

        # Assert
        mock_create.assert_not_called()  # Should not create
        mock_update.assert_called_once()  # Should update

    @patch('api.discount_sync.DiscountSyncService.deactivate_in_stripe')
    @patch('api.discount_sync.DiscountSyncService.create_in_stripe')
    def test_pre_delete_signal_deactivates(self, mock_create, mock_deactivate):
        """Test that pre_delete signal deactivates in Stripe."""
        # Arrange
        mock_create.return_value = ('coupon_del1', 'promo_del1')

        code = DiscountCode.objects.create(
            code='SIGNALDEL',
            name='Signal Delete Test',
            discount_type='percent',
            percent_off=Decimal('10.00'),
            duration='forever',
            is_active=True
        )

        # Act
        code.delete()

        # Assert
        mock_deactivate.assert_called_once()
