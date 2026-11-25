import json
import re
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .email_backend import ResendEmailBackend
from .models import (
    CancellationRequest, Category, ContactMessage, Coupon, NewsletterSubscriber, Order, OrderItem, OrderPayment,
    Product, ProductImage, ProductVariant, SiteSettings, Size, Subcategory,
)
from .services import icredit
from .services.orders import confirm_order_payment, finalize_paid_order
from .services.pricing import calculate_totals, evaluate_coupon
from .services.shipping import amount_to_free_shipping, calculate_shipping_fee

SALE_ID = '0f8fad5b-d9cb-469f-a165-70867728950e'
OTHER_SALE_ID = '7c9e6679-7425-40de-944b-e07fc1f90ae7'
PRIVATE_TOKEN = '3f2504e0-4f89-11d3-9a0c-0305e82c3301'
PUBLIC_TOKEN = '9a7b330a-a736-4f1b-8e0c-5c4f6d2b1a10'
PAYMENT_PAGE_URL = 'https://testicredit.rivhit.co.il/payment/PaymentItems.aspx?Token=abc'


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class FakeICredit:
    """
    מחליף את requests.post של שירות iCredit. מתעד את הבקשות ומחזיר תשובות
    בפורמט של ה-API האמיתי.
    """

    def __init__(self, verified=True, sale_details_sale_id=''):
        self.verified = verified
        self.sale_details_sale_id = sale_details_sale_id
        self.calls = []

    def __call__(self, url, data=None, **kwargs):
        payload = json.loads(data)
        self.calls.append((url, payload))
        if url.endswith('/GetUrl'):
            return FakeResponse({
                'Status': 0,
                'URL': PAYMENT_PAGE_URL,
                'PrivateSaleToken': PRIVATE_TOKEN,
                'PublicSaleToken': PUBLIC_TOKEN,
            })
        if url.endswith('/Verify'):
            return FakeResponse({'Status': 'VERIFIED' if self.verified else 'NOTVERIFIED'})
        if url.endswith('/SaleDetails'):
            return FakeResponse({'Status': 0 if self.sale_details_sale_id else 1, 'SaleId': self.sale_details_sale_id or None})
        raise AssertionError(f'unexpected iCredit call: {url}')

    def payloads(self, operation):
        return [payload for url, payload in self.calls if url.endswith('/' + operation)]


def patch_icredit(fake):
    return mock.patch('store.services.icredit.requests.post', side_effect=fake)


def make_product(name='חליפת תינוק', price='80.00', stock=10, **extra):
    return Product.objects.create(
        name=name,
        slug=extra.pop('slug', None) or f'product-{Product.objects.count() + 1}',
        description='תיאור',
        price=Decimal(price),
        stock_quantity=stock,
        image='products/test.jpg',
        **extra,
    )


def make_coupon(code='SAVE10', discount_type='percent', value='10', **extra):
    now = timezone.now()
    return Coupon.objects.create(
        code=code,
        discount_type=discount_type,
        discount_value=Decimal(value),
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        **extra,
    )


CHECKOUT_DATA = {
    'shipping_method': 'delivery',
    'first_name': 'דנה',
    'last_name': 'כהן',
    'guest_phone': '0501234567',
    'guest_email': 'dana@example.com',
    'guest_address': 'הרצל 1',
    'guest_city': 'תל אביב',
    'notes': '',
    'accept_terms': 'on',
}


class ShippingFeeTests(TestCase):
    def test_delivery_tiers_match_published_policy(self):
        cases = [
            ('1', '39.00'), ('99', '39.00'), ('99.99', '39.00'),
            ('100', '25.00'), ('199.99', '25.00'),
            ('200', '25.00'), ('299.99', '25.00'),
            ('300', '0.00'), ('1000', '0.00'),
        ]
        for amount, fee in cases:
            with self.subTest(amount=amount):
                self.assertEqual(calculate_shipping_fee(Decimal(amount)), Decimal(fee))

    def test_pickup_is_always_free(self):
        for amount in ('1', '99', '250', '500'):
            self.assertEqual(calculate_shipping_fee(Decimal(amount), 'pickup'), Decimal('0.00'))

    def test_empty_cart_has_no_shipping_fee(self):
        self.assertEqual(calculate_shipping_fee(Decimal('0')), Decimal('0.00'))

    def test_amount_to_free_shipping(self):
        self.assertEqual(amount_to_free_shipping(Decimal('250')), Decimal('50'))
        self.assertEqual(amount_to_free_shipping(Decimal('300')), Decimal('0.00'))
        self.assertEqual(amount_to_free_shipping(Decimal('0')), Decimal('0.00'))


class PricingTests(TestCase):
    def test_totals_without_coupon(self):
        totals = calculate_totals(Decimal('160'))
        self.assertEqual(totals.shipping_fee, Decimal('25.00'))
        self.assertEqual(totals.total, Decimal('185.00'))

    def test_shipping_tier_is_based_on_amount_after_coupon(self):
        make_coupon('SAVE10')
        totals = calculate_totals(Decimal('320'), 'save10')
        self.assertEqual(totals.discount, Decimal('32.00'))
        # 288 אחרי הנחה - כבר לא משלוח חינם
        self.assertEqual(totals.shipping_fee, Decimal('25.00'))
        self.assertEqual(totals.total, Decimal('313.00'))

    def test_pickup_keeps_delivery_fee_for_display(self):
        totals = calculate_totals(Decimal('160'), shipping_method='pickup')
        self.assertEqual(totals.shipping_fee, Decimal('0.00'))
        self.assertEqual(totals.delivery_fee, Decimal('25.00'))
        self.assertEqual(totals.total, Decimal('160.00'))

    def test_fixed_coupon_never_exceeds_subtotal(self):
        make_coupon('BIG', discount_type='fixed', value='500')
        totals = calculate_totals(Decimal('80'), 'BIG')
        self.assertEqual(totals.discount, Decimal('80.00'))
        self.assertEqual(totals.total, Decimal('0.00'))

    def test_coupon_minimum_order(self):
        make_coupon('MIN200', minimum_order_amount=Decimal('200'))
        self.assertFalse(evaluate_coupon('MIN200', Decimal('150')).is_valid)
        self.assertTrue(evaluate_coupon('MIN200', Decimal('200')).is_valid)

    def test_expired_and_unknown_coupons_are_rejected(self):
        coupon = make_coupon('OLD')
        coupon.valid_until = timezone.now() - timedelta(hours=1)
        coupon.save()
        self.assertFalse(evaluate_coupon('OLD', Decimal('100')).is_valid)
        self.assertFalse(evaluate_coupon('NOPE', Decimal('100')).is_valid)
        self.assertEqual(calculate_totals(Decimal('100'), 'NOPE').discount, Decimal('0.00'))

    def test_newsletter_coupon(self):
        NewsletterSubscriber.objects.create(email='a@example.com', coupon_code='ARYE-ABCDE', discount_percent=10)
        result = evaluate_coupon('arye-abcde', Decimal('99.90'))
        self.assertTrue(result.is_valid)
        self.assertEqual(result.discount, Decimal('9.99'))

    def test_used_newsletter_coupon_is_rejected(self):
        NewsletterSubscriber.objects.create(email='a@example.com', coupon_code='ARYE-ABCDE', is_used=True)
        self.assertFalse(evaluate_coupon('ARYE-ABCDE', Decimal('100')).is_valid)


@override_settings(RESEND_API_KEY='')
class StoreFlowTestCase(TestCase):
    """בסיס לבדיקות של עגלה, קופה ותשלום."""

    def setUp(self):
        self.product = make_product(price='80.00', stock=10)

    def add_to_cart(self, product=None, quantity=2):
        product = product or self.product
        return self.client.post(reverse('add_to_cart', args=[product.id]), {'quantity': quantity})

    def checkout(self, **overrides):
        data = dict(CHECKOUT_DATA)
        data.update(overrides)
        return self.client.post(reverse('checkout'), data)

    def pending_order(self, **overrides):
        """עגלה + קופה, ומחזיר את ההזמנה הממתינה לתשלום."""
        self.add_to_cart()
        self.checkout(**overrides)
        return Order.objects.get()

    def post_ipn(self, order_id, sale_id=SALE_ID, as_json=True):
        data = {'SaleId': sale_id, 'Custom1': str(order_id), 'TransactionAmount': '1.00'}
        if as_json:
            return self.client.post(reverse('payment_notify'), json.dumps(data), content_type='application/json')
        return self.client.post(reverse('payment_notify'), data)


class CartAndCheckoutTests(StoreFlowTestCase):
    def test_cart_page_shows_shipping_fee_and_total(self):
        self.add_to_cart(quantity=2)
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['shipping_fee'], Decimal('25.00'))
        self.assertEqual(response.context['total'], Decimal('185.00'))

    def test_cart_data_api_uses_server_side_shipping(self):
        self.add_to_cart(quantity=1)
        data = self.client.get(reverse('cart_data')).json()
        self.assertEqual(data['subtotal'], 80.0)
        self.assertEqual(data['shipping_fee'], 39.0)
        self.assertEqual(data['total'], 119.0)
        self.assertEqual(data['free_shipping_threshold'], 300.0)
        self.assertEqual(data['remaining_for_free_shipping'], 220.0)

    def test_add_to_cart_with_invalid_quantity_does_not_crash(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]), {'quantity': 'abc'})
        self.assertEqual(response.status_code, 302)

    def test_checkout_page_renders(self):
        self.add_to_cart()
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="shipping_method"')
        self.assertContains(response, '052064219')
        self.assertContains(response, 'name="accept_terms"')
        self.assertEqual(response.context['totals_json']['delivery_fee'], 25.0)

    def test_checkout_requires_terms_acceptance(self):
        self.add_to_cart()
        data = dict(CHECKOUT_DATA)
        data.pop('accept_terms')
        response = self.client.post(reverse('checkout'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertIn('accept_terms', response.context['form'].errors)

    def test_checkout_creates_order_with_delivery_fee(self):
        self.add_to_cart(quantity=2)
        response = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(response, reverse('initiate_payment', args=[order.id]), fetch_redirect_response=False)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.shipping_method, 'delivery')
        self.assertEqual(order.shipping_fee, Decimal('25.00'))
        self.assertEqual(order.total_price, Decimal('185.00'))
        self.assertEqual(order.guest_city, 'תל אביב')
        self.assertEqual(order.items.get().quantity, 2)

    def test_checkout_does_not_touch_stock(self):
        self.pending_order()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_pickup_is_free_and_needs_no_address(self):
        self.add_to_cart(quantity=2)
        self.checkout(shipping_method='pickup', guest_address='', guest_city='')
        order = Order.objects.get()
        self.assertEqual(order.shipping_method, 'pickup')
        self.assertEqual(order.shipping_fee, Decimal('0.00'))
        self.assertEqual(order.total_price, Decimal('160.00'))

    def test_delivery_requires_address(self):
        self.add_to_cart()
        response = self.checkout(guest_address='', guest_city='')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertIn('guest_address', response.context['form'].errors)
        self.assertIn('guest_city', response.context['form'].errors)

    def test_shipping_fee_cannot_be_set_by_the_client(self):
        self.add_to_cart(quantity=1)
        self.checkout(shipping_fee='0', total='1', total_price='1')
        order = Order.objects.get()
        self.assertEqual(order.shipping_fee, Decimal('39.00'))
        self.assertEqual(order.total_price, Decimal('119.00'))

    def test_double_submit_reuses_the_same_order(self):
        self.add_to_cart()
        self.checkout()
        self.checkout()
        self.assertEqual(Order.objects.count(), 1)

    def test_changed_cart_creates_a_new_order(self):
        self.add_to_cart(quantity=1)
        self.checkout()
        self.add_to_cart(quantity=1)
        self.checkout()
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(self.client.session['pending_order_id'], Order.objects.order_by('-id').first().id)

    def test_checkout_blocks_out_of_stock_cart(self):
        self.add_to_cart(quantity=2)
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        response = self.checkout()
        self.assertRedirects(response, reverse('cart'), fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_cannot_checkout(self):
        response = self.checkout()
        self.assertRedirects(response, reverse('cart'), fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())

    def test_coupon_is_charged_at_checkout(self):
        make_coupon('SAVE10')
        self.add_to_cart(quantity=2)
        response = self.client.post(
            reverse('apply_coupon'),
            json.dumps({'coupon_code': 'save10', 'shipping_method': 'delivery'}),
            content_type='application/json',
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['discount_amount'], 16.0)
        self.assertEqual(data['total'], 169.0)

        self.checkout()
        order = Order.objects.get()
        self.assertEqual(order.coupon_code, 'SAVE10')
        self.assertEqual(order.discount_amount, Decimal('16.00'))
        self.assertEqual(order.shipping_fee, Decimal('25.00'))
        self.assertEqual(order.total_price, Decimal('169.00'))

    def test_invalid_coupon_is_not_applied(self):
        self.add_to_cart()
        response = self.client.post(
            reverse('apply_coupon'), json.dumps({'coupon_code': 'NOPE'}), content_type='application/json',
        )
        self.assertFalse(response.json()['success'])
        self.assertNotIn('applied_coupon', self.client.session)

    def test_remove_coupon(self):
        make_coupon('SAVE10')
        self.add_to_cart(quantity=2)
        self.client.post(reverse('apply_coupon'), json.dumps({'coupon_code': 'SAVE10'}), content_type='application/json')
        data = self.client.post(reverse('remove_coupon'), '{}', content_type='application/json').json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 185.0)
        self.assertNotIn('applied_coupon', self.client.session)


class PaymentGatewayPayloadTests(StoreFlowTestCase):
    def assert_payload_matches_order(self, payload, order):
        lines_total = sum(Decimal(str(item['UnitPrice'])) * item['Quantity'] for item in payload['Items'])
        charged = lines_total - Decimal(str(payload.get('Discount', 0)))
        self.assertEqual(charged, order.total_price)

    def test_gateway_is_charged_exactly_the_order_total(self):
        make_coupon('SAVE10')
        self.add_to_cart(quantity=2)
        self.client.post(reverse('apply_coupon'), json.dumps({'coupon_code': 'SAVE10'}), content_type='application/json')
        self.checkout()
        order = Order.objects.get()

        fake = FakeICredit()
        with patch_icredit(fake):
            response = self.client.get(reverse('initiate_payment', args=[order.id]))

        self.assertRedirects(response, PAYMENT_PAGE_URL, fetch_redirect_response=False)
        payload = fake.payloads('GetUrl')[0]
        self.assert_payload_matches_order(payload, order)
        self.assertEqual(payload['Discount'], 16.0)
        self.assertEqual(payload['Custom1'], str(order.id))
        self.assertEqual([item['Description'] for item in payload['Items']][-1], 'משלוח עד הבית')

        order.refresh_from_db()
        self.assertEqual(order.payment_token, PRIVATE_TOKEN)
        self.assertEqual(order.status, 'pending')

    def test_pickup_order_has_no_shipping_line(self):
        order = self.pending_order(shipping_method='pickup', guest_address='', guest_city='')
        payload = icredit.build_payment_payload(order, 'https://a/s', 'https://a/f', 'https://a/n')
        self.assertEqual(len(payload['Items']), 1)
        self.assertNotIn('Discount', payload)
        self.assertEqual(payload['IPNURL'], 'https://a/n')
        self.assert_payload_matches_order(payload, order)

    def test_inconsistent_order_falls_back_to_a_single_line_with_the_order_total(self):
        order = self.pending_order()
        Order.objects.filter(pk=order.pk).update(total_price=Decimal('150.00'))
        order.refresh_from_db()
        payload = icredit.build_payment_payload(order, 'https://a/s', 'https://a/f')
        self.assertEqual(len(payload['Items']), 1)
        self.assertEqual(payload['Items'][0]['UnitPrice'], 150.0)
        self.assertNotIn('Discount', payload)

    @override_settings(ALLOWED_HOSTS=['shop.example.org'], PAYMENT_IPN_BASE_URL='')
    def test_ipn_url_is_sent_for_public_hosts(self):
        self.client.defaults['HTTP_HOST'] = 'shop.example.org'
        order = self.pending_order()
        fake = FakeICredit()
        with patch_icredit(fake):
            self.client.get(reverse('initiate_payment', args=[order.id]))
        payload = fake.payloads('GetUrl')[0]
        self.assertEqual(payload['IPNURL'], 'https://shop.example.org/payment/notify/')
        self.assertEqual(payload['RedirectURL'], 'https://shop.example.org/payment/success/')

    def test_only_the_session_that_created_the_order_can_pay_for_it(self):
        order = self.pending_order()
        fake = FakeICredit()
        other_client = self.client_class()
        with patch_icredit(fake):
            response = other_client.get(reverse('initiate_payment', args=[order.id]))
        self.assertRedirects(response, reverse('cart'), fetch_redirect_response=False)
        self.assertEqual(fake.calls, [])

    def test_gateway_failure_returns_to_checkout(self):
        order = self.pending_order()
        with mock.patch('store.services.icredit.requests.post', return_value=FakeResponse({'Status': 5, 'DebugMessage': 'bad'})):
            response = self.client.get(reverse('initiate_payment', args=[order.id]))
        self.assertRedirects(response, reverse('checkout'), fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_fully_discounted_order_skips_the_gateway(self):
        make_coupon('FREE', discount_type='fixed', value='500')
        self.add_to_cart(quantity=1)
        self.client.post(reverse('apply_coupon'), json.dumps({'coupon_code': 'FREE'}), content_type='application/json')
        self.checkout()
        order = Order.objects.get()
        self.assertEqual(order.total_price, Decimal('0.00'))

        fake = FakeICredit()
        with patch_icredit(fake):
            response = self.client.get(reverse('initiate_payment', args=[order.id]))
        self.assertRedirects(response, reverse('payment_success'), fetch_redirect_response=False)
        self.assertEqual(fake.calls, [])
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')


class PaymentConfirmationTests(StoreFlowTestCase):
    def assert_pending(self, order):
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.product.stock_quantity, 10)

    def assert_paid_once(self, order):
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertIsNotNone(order.paid_at)
        self.assertEqual(self.product.stock_quantity, 8)

    # --- דף ההצלחה ---

    def test_success_page_without_an_order_in_session_shows_nothing(self):
        order = self.pending_order()
        stranger = self.client_class()
        fake = FakeICredit()
        with patch_icredit(fake):
            response = stranger.get(reverse('payment_success'), {'order': order.id, 'SaleId': SALE_ID, 'Custom1': order.id})
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertEqual(fake.calls, [])
        self.assert_pending(order)

    def test_visiting_success_page_does_not_mark_order_as_paid(self):
        order = self.pending_order()
        fake = FakeICredit(verified=False)
        with patch_icredit(fake):
            response = self.client.get(reverse('payment_success'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_paid'])
        self.assertTrue(response.context['payment_pending'])
        self.assert_pending(order)
        # העגלה נשארת עד שהתשלום מאושר
        self.assertEqual(self.client.get(reverse('cart_data')).json()['total_items'], 2)

    def test_forged_sale_id_on_success_page_is_rejected(self):
        order = self.pending_order()
        fake = FakeICredit(verified=False)
        with patch_icredit(fake):
            response = self.client.get(reverse('payment_success'), {'SaleId': SALE_ID})
        self.assertFalse(response.context['is_paid'])
        self.assert_pending(order)
        self.assertEqual(fake.payloads('Verify')[0]['TotalAmount'], float(order.total_price))

    def test_verified_return_from_gateway_marks_order_paid(self):
        order = self.pending_order()
        fake = FakeICredit(verified=True)
        with patch_icredit(fake):
            response = self.client.get(reverse('payment_success'), {'SaleId': SALE_ID})
        self.assertTrue(response.context['is_paid'])
        self.assert_paid_once(order)
        self.assertEqual(order.payment_transaction_id, SALE_ID)
        self.assertEqual(OrderPayment.objects.get().sale_id, SALE_ID)

        verify = fake.payloads('Verify')[0]
        self.assertEqual(verify['SaleId'], SALE_ID)
        self.assertEqual(verify['TotalAmount'], 185.0)

        # העגלה והסשן נוקו
        self.assertEqual(self.client.get(reverse('cart_data')).json()['total_items'], 0)
        self.assertNotIn('pending_order_id', self.client.session)
        self.assertEqual(self.client.session['last_order_id'], order.id)

        # רענון הדף לא מוריד מלאי פעם נוספת
        with patch_icredit(FakeICredit()):
            self.client.get(reverse('payment_success'), {'SaleId': SALE_ID})
        self.assert_paid_once(order)

    def test_success_page_falls_back_to_sale_lookup_by_token(self):
        order = self.pending_order()
        Order.objects.filter(pk=order.pk).update(payment_token=PRIVATE_TOKEN)
        fake = FakeICredit(verified=True, sale_details_sale_id=SALE_ID.upper())
        with patch_icredit(fake):
            response = self.client.get(reverse('payment_success'))
        self.assertTrue(response.context['is_paid'])
        self.assert_paid_once(order)
        self.assertEqual(fake.payloads('SaleDetails')[0], {'SalePrivateToken': PRIVATE_TOKEN})
        self.assertEqual(fake.payloads('Verify')[0]['TotalAmount'], 185.0)

    def test_sale_lookup_without_a_sale_keeps_order_pending(self):
        order = self.pending_order()
        Order.objects.filter(pk=order.pk).update(payment_token=PRIVATE_TOKEN)
        fake = FakeICredit(verified=True, sale_details_sale_id='')
        with patch_icredit(fake):
            response = self.client.get(reverse('payment_success'))
        self.assertTrue(response.context['keep_checking'])
        self.assertEqual(fake.payloads('Verify'), [])
        self.assert_pending(order)

    def test_pending_page_stops_refreshing_eventually(self):
        self.pending_order()
        with patch_icredit(FakeICredit(verified=False)):
            response = self.client.get(reverse('payment_success'), {'check': 10})
        self.assertFalse(response.context['keep_checking'])
        self.assertTrue(response.context['payment_pending'])

    # --- IPN ---

    def test_ipn_must_be_post(self):
        self.assertEqual(self.client.get(reverse('payment_notify')).status_code, 405)

    def test_forged_ipn_is_rejected(self):
        order = self.pending_order()
        fake = FakeICredit(verified=False)
        with patch_icredit(fake):
            response = self.post_ipn(order.id)
        self.assertEqual(response.status_code, 400)
        self.assert_pending(order)

    def test_ipn_with_invalid_sale_id_never_reaches_the_gateway(self):
        order = self.pending_order()
        fake = FakeICredit(verified=True)
        with patch_icredit(fake):
            response = self.post_ipn(order.id, sale_id='not-a-guid')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fake.calls, [])
        self.assert_pending(order)

    def test_ipn_for_unknown_order(self):
        with patch_icredit(FakeICredit()):
            self.assertEqual(self.post_ipn(999999).status_code, 404)
            self.assertEqual(self.post_ipn('abc').status_code, 404)

    def test_ipn_with_garbage_body(self):
        response = self.client.post(reverse('payment_notify'), '{not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_verified_ipn_marks_order_paid_once(self):
        order = self.pending_order()
        fake = FakeICredit(verified=True)
        with patch_icredit(fake):
            self.assertEqual(self.post_ipn(order.id).status_code, 200)
            # iCredit עשוי לשלוח את אותה הודעה שוב
            self.assertEqual(self.post_ipn(order.id).status_code, 200)
        self.assert_paid_once(order)
        self.assertEqual(len(fake.payloads('Verify')), 1)

    def test_ipn_as_form_post_with_different_field_case(self):
        order = self.pending_order()
        with patch_icredit(FakeICredit(verified=True)):
            response = self.client.post(reverse('payment_notify'), {'saleid': SALE_ID.upper(), 'custom1': str(order.id)})
        self.assertEqual(response.status_code, 200)
        self.assert_paid_once(order)

    def test_ipn_verifies_the_order_total_not_the_amount_in_the_message(self):
        order = self.pending_order()
        fake = FakeICredit(verified=True)
        with patch_icredit(fake):
            self.post_ipn(order.id)
        self.assertEqual(fake.payloads('Verify')[0]['TotalAmount'], 185.0)

    def test_one_sale_cannot_pay_for_two_orders(self):
        first = self.pending_order()
        second = Order.objects.create(total_price=first.total_price, guest_name='אחר', status='pending')
        with patch_icredit(FakeICredit(verified=True)):
            self.assertEqual(self.post_ipn(first.id).status_code, 200)
            self.assertEqual(self.post_ipn(second.id).status_code, 400)
        second.refresh_from_db()
        self.assertEqual(second.status, 'pending')

    def test_database_rejects_a_reused_sale_even_without_the_precheck(self):
        first = self.pending_order()
        second = Order.objects.create(total_price=first.total_price, guest_name='אחר', status='pending')
        finalize_paid_order(first.id, SALE_ID)
        order, newly_paid = finalize_paid_order(second.id, SALE_ID.upper())
        self.assertFalse(newly_paid)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(OrderPayment.objects.count(), 1)

    def test_cancelled_order_cannot_be_paid(self):
        order = self.pending_order()
        Order.objects.filter(pk=order.pk).update(status='cancelled')
        order.refresh_from_db()
        fake = FakeICredit(verified=True)
        with patch_icredit(fake):
            self.assertFalse(confirm_order_payment(order, SALE_ID))
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.product.stock_quantity, 10)
        # הכסף נגבה למרות הביטול - נרשם כתשלום לזיכוי ומסומן לטיפול
        self.assertTrue(order.needs_attention)
        self.assertTrue(OrderPayment.objects.get(order=order).is_duplicate)

    def test_unverified_payment_on_a_closed_order_changes_nothing(self):
        order = self.pending_order()
        finalize_paid_order(order.id, SALE_ID)
        order.refresh_from_db()
        with patch_icredit(FakeICredit(verified=False)):
            self.assertTrue(confirm_order_payment(order, OTHER_SALE_ID))
        order.refresh_from_db()
        self.assertFalse(order.needs_attention)
        self.assertEqual(OrderPayment.objects.count(), 1)

    @override_settings(RESEND_API_KEY='test-key', CONTACT_EMAIL='owner@example.com')
    def test_second_payment_on_a_paid_order_is_recorded_and_reported(self):
        order = self.pending_order()
        with mock.patch('store.services.emails.resend.Emails.send') as send:
            finalize_paid_order(order.id, SALE_ID)
            send.reset_mock()
            with patch_icredit(FakeICredit(verified=True)):
                # אותה עסקה שוב (IPN כפול) - לא תשלום נוסף
                self.assertEqual(self.post_ipn(order.id).status_code, 200)
                self.assertEqual(send.call_count, 0)
                # עסקה אחרת על אותה הזמנה - הלקוח שילם פעמיים
                self.assertEqual(self.post_ipn(order.id, sale_id=OTHER_SALE_ID).status_code, 200)
                self.assertEqual(self.post_ipn(order.id, sale_id=OTHER_SALE_ID).status_code, 200)
        self.assert_paid_once(order)
        self.assertTrue(order.needs_attention)
        self.assertIn(OTHER_SALE_ID, order.attention_note)
        duplicate = OrderPayment.objects.get(sale_id=OTHER_SALE_ID)
        self.assertTrue(duplicate.is_duplicate)
        self.assertFalse(OrderPayment.objects.get(sale_id=SALE_ID).is_duplicate)
        self.assertEqual(send.call_count, 1)
        alert = send.call_args.args[0]
        self.assertEqual(alert['to'], ['owner@example.com'])
        self.assertIn('תשלום כפול', alert['subject'])

    @override_settings(RESEND_API_KEY='test-key', CONTACT_EMAIL='owner@example.com')
    def test_oversold_order_is_flagged_for_the_owner(self):
        order = self.pending_order()
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        with mock.patch('store.services.emails.resend.Emails.send') as send:
            finalize_paid_order(order.id, SALE_ID)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertTrue(order.needs_attention)
        self.assertIn('נמכר מעבר למלאי', order.attention_note)
        owner = send.call_args_list[1].args[0]
        self.assertTrue(owner['subject'].startswith('דורש טיפול'))
        self.assertIn('נמכר מעבר למלאי', owner['html'])

    def test_order_within_stock_is_not_flagged(self):
        order = self.pending_order()
        finalize_paid_order(order.id, SALE_ID)
        order.refresh_from_db()
        self.assertFalse(order.needs_attention)

    def test_gateway_error_during_verify_keeps_order_pending(self):
        order = self.pending_order()
        with mock.patch('store.services.icredit.requests.post', return_value=FakeResponse({}, status_code=500)):
            response = self.post_ipn(order.id)
        self.assertEqual(response.status_code, 400)
        self.assert_pending(order)

    # --- מה שקורה כשהזמנה משולמת ---

    def test_stock_never_goes_negative(self):
        order = self.pending_order()
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        finalize_paid_order(order.id, SALE_ID)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)

    def test_coupon_usage_is_recorded_only_when_paid(self):
        coupon = make_coupon('SAVE10')
        self.add_to_cart(quantity=2)
        self.client.post(reverse('apply_coupon'), json.dumps({'coupon_code': 'SAVE10'}), content_type='application/json')
        self.checkout()
        order = Order.objects.get()
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 0)

        finalize_paid_order(order.id, SALE_ID)
        finalize_paid_order(order.id, SALE_ID)
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)

    def test_newsletter_coupon_is_marked_used_when_paid(self):
        subscriber = NewsletterSubscriber.objects.create(email='a@example.com', coupon_code='ARYE-ABCDE')
        self.add_to_cart(quantity=2)
        self.client.post(reverse('apply_coupon'), json.dumps({'coupon_code': 'ARYE-ABCDE'}), content_type='application/json')
        self.checkout()
        finalize_paid_order(Order.objects.get().id, SALE_ID)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_used)

    @override_settings(RESEND_API_KEY='test-key', CONTACT_EMAIL='owner@example.com', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_emails_are_sent_once_to_customer_and_owner(self):
        order = self.pending_order(first_name='<b>דנה</b>')
        with mock.patch('store.services.emails.resend.Emails.send') as send:
            finalize_paid_order(order.id, SALE_ID)
            finalize_paid_order(order.id, SALE_ID)
        self.assertEqual(send.call_count, 2)
        customer, owner = [call.args[0] for call in send.call_args_list]
        self.assertEqual(customer['to'], ['dana@example.com'])
        self.assertEqual(owner['to'], ['owner@example.com'])
        self.assertIn('25.00', customer['html'])  # דמי המשלוח מופיעים במייל
        self.assertIn('052064219', customer['html'])
        self.assertIn('14 ימים', customer['html'])
        self.assertIn('https://arye-boutique.co.il/cancel/', customer['html'])
        self.assertIn('14 ימים ממועד קבלת הודעת הביטול', customer['html'])
        self.assertIn(f'/admin/store/order/{order.id}/change/', owner['html'])
        # ערכים שהלקוח הזין לא נכנסים כ-HTML
        self.assertNotIn('<b>דנה</b>', customer['html'])
        self.assertIn('&lt;b&gt;דנה&lt;/b&gt;', owner['html'])

    @override_settings(RESEND_API_KEY='test-key')
    def test_email_failure_does_not_undo_the_payment(self):
        order = self.pending_order()
        with mock.patch('store.services.emails.resend.Emails.send', side_effect=RuntimeError('mail down')):
            finalize_paid_order(order.id, SALE_ID)
        self.assert_paid_once(order)


class LegalPagesTests(TestCase):
    def test_terms_match_the_cancellation_cap(self):
        response = self.client.get(reverse('terms_of_service'))
        self.assertContains(response, '052064219')
        self.assertContains(response, 'iCredit')
        self.assertContains(response, 'id="privacy"')
        self.assertNotContains(response, 'PayPal')
        self.assertNotContains(response, 'דמי טיפול בסך')
        self.assertNotContains(response, '50 ש"ח')
        self.assertContains(response, '14 ימים ממועד קבלת הודעת הביטול')
        self.assertContains(response, 'שרתים מחוץ לישראל')
        self.assertContains(response, reverse('cancel_order'))
        self.assertNotContains(response, 'אין לשלוח את בקשת ההסרה')

    def test_shipping_page_matches_terms(self):
        response = self.client.get(reverse('shipping_and_returns'))
        self.assertContains(response, '5%')
        self.assertContains(response, '100 ש"ח')
        self.assertContains(response, 'שירות בחירה')
        self.assertContains(response, '14 ימים ממועד קבלת הודעת הביטול')
        self.assertContains(response, reverse('cancel_order'))
        self.assertNotContains(response, 'PayPal')
        self.assertNotContains(response, 'לוחות הזמנים של חברת האשראי')

    def test_footer_links_to_cancellation(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('cancel_order'))
        self.assertContains(response, 'ביטול עסקה')

    def test_cancellation_form_saves_the_request_even_if_email_fails(self):
        with override_settings(RESEND_API_KEY='test-key'), mock.patch(
            'store.views.resend.Emails.send', side_effect=RuntimeError('mail down')
        ):
            response = self.client.post(reverse('cancel_order'), {
                'full_name': 'דנה כהן',
                'phone': '0501234567',
                'email': 'dana@example.com',
                'order_number': '18',
                'note': 'מבקשת לבטל',
            })
        self.assertEqual(response.status_code, 302)
        saved = CancellationRequest.objects.get()
        self.assertEqual(saved.order_number, '18')
        receipt = self.client.get(response.url)
        self.assertContains(receipt, 'הודעת הביטול התקבלה')
        self.assertContains(receipt, '14 ימים ממועד זה')

    def test_cancellation_form_requires_an_order_number(self):
        response = self.client.post(reverse('cancel_order'), {
            'full_name': 'דנה כהן',
            'phone': '0501234567',
            'email': 'dana@example.com',
            'order_number': '',
            'note': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CancellationRequest.objects.exists())

    def test_accessibility_statement_has_a_fixed_date(self):
        response = self.client.get(reverse('accessibility_statement'))
        self.assertContains(response, '25.11.2026')
        self.assertNotContains(response, 'NVDA')


class ComingSoonTests(StoreFlowTestCase):
    def setUp(self):
        super().setUp()
        SiteSettings.objects.create(coming_soon_enabled=True)

    def test_visitors_are_sent_to_coming_soon(self):
        for name in ('home', 'cart', 'checkout', 'payment_success'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertRedirects(response, reverse('coming_soon'), fetch_redirect_response=False)

    def test_payment_notification_is_not_blocked(self):
        order = Order.objects.create(total_price=Decimal('110.00'), guest_name='דנה', status='pending')
        with patch_icredit(FakeICredit(verified=True)):
            response = self.post_ipn(order.id)
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')

    def test_robots_txt_is_served(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Disallow: /checkout/', response.content.decode())


class AdminPagesTests(StoreFlowTestCase):
    """כל דפי הניהול חייבים להיפתח - בעל האתר מנהל משם את ההזמנות."""

    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model
        self.admin_user = get_user_model().objects.create_superuser(
            username='owner', email='owner@example.com', password='not-a-real-password-1!',
        )

    def test_order_page_opens_in_admin(self):
        order = self.pending_order()
        self.assertTrue(order.items.exists())
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:store_order_change', args=[order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_empty_order_line_has_zero_subtotal(self):
        self.assertEqual(OrderItem().subtotal, Decimal('0.00'))

    def test_every_admin_page_opens(self):
        from django.contrib import admin
        order = self.pending_order()
        self.client.force_login(self.admin_user)
        for model in admin.site._registry:
            meta = model._meta
            base = f'admin:{meta.app_label}_{meta.model_name}'
            urls = [reverse(f'{base}_changelist'), reverse(f'{base}_add')]
            if meta.managed:
                urls += [reverse(f'{base}_change', args=[obj.pk]) for obj in model.objects.all()[:2]]
            for url in urls:
                with self.subTest(url=url):
                    # 403 = דף שאין בו הרשאת הוספה; מה שאסור הוא קריסה
                    self.assertIn(self.client.get(url).status_code, (200, 302, 403))
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())


class OrderAdminStatusTests(StoreFlowTestCase):
    """שינוי סטטוס ידני בניהול: בלי לעקוף תשלום, עם מלאי ומיילים."""

    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model
        self.admin_user = get_user_model().objects.create_superuser(
            username='owner', email='owner@example.com', password='not-a-real-password-1!',
        )

    def set_status(self, order, status):
        """שינוי סטטוס מרשימת ההזמנות, כמו שבעל האתר עושה."""
        self.client.force_login(self.admin_user)
        return self.client.post(reverse('admin:store_order_changelist'), {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-id': str(order.pk),
            'form-0-status': status,
            '_save': 'שמירה',
        }, follow=True)

    def paid_order(self, **overrides):
        order = self.pending_order(**overrides)
        finalize_paid_order(order.id, SALE_ID)
        order.refresh_from_db()
        return order

    def test_pending_order_cannot_be_marked_paid_by_hand(self):
        order = self.pending_order()
        response = self.set_status(order, 'paid')
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertContains(response, 'הסטטוס לא שונה')

    def test_pending_order_can_be_cancelled(self):
        order = self.pending_order()
        self.set_status(order, 'cancelled')
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        # המלאי לא ירד מעולם, ולכן גם לא מוחזר
        self.assertEqual(self.product.stock_quantity, 10)

    def test_cancelling_a_paid_order_returns_the_stock_once(self):
        order = self.paid_order()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
        self.set_status(order, 'cancelled')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        # הזמנה שבוטלה נשארת מבוטלת, והמלאי לא מוחזר שוב
        self.set_status(order, 'paid')
        self.set_status(order, 'cancelled')
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.product.stock_quantity, 10)

    def test_paid_order_cannot_go_back_to_pending(self):
        order = self.paid_order()
        self.set_status(order, 'pending')
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')

    @override_settings(RESEND_API_KEY='test-key', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_ready_for_pickup_emails_the_customer(self):
        order = self.paid_order(shipping_method='pickup')
        with mock.patch('store.services.emails.resend.Emails.send') as send:
            response = self.set_status(order, 'ready_for_pickup')
            # שמירה חוזרת בלי שינוי סטטוס לא שולחת שוב
            self.set_status(order, 'ready_for_pickup')
        order.refresh_from_db()
        self.assertEqual(order.status, 'ready_for_pickup')
        self.assertEqual(send.call_count, 1)
        email = send.call_args.args[0]
        self.assertEqual(email['to'], ['dana@example.com'])
        self.assertIn('מוכנה לאיסוף', email['subject'])
        self.assertIn(f'#{order.id}', email['html'])
        self.assertContains(response, 'נשלח מייל עדכון ללקוח')

    @override_settings(RESEND_API_KEY='test-key')
    def test_shipped_emails_the_customer(self):
        order = self.paid_order()
        with mock.patch('store.services.emails.resend.Emails.send') as send:
            self.set_status(order, 'shipped')
        self.assertEqual(send.call_count, 1)
        self.assertIn('נשלחה', send.call_args.args[0]['subject'])

    @override_settings(RESEND_API_KEY='test-key')
    def test_status_email_failure_keeps_the_status_and_warns(self):
        order = self.paid_order()
        with mock.patch('store.services.emails.resend.Emails.send', side_effect=RuntimeError('mail down')):
            response = self.set_status(order, 'shipped')
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertContains(response, 'לא נשלח')

    def test_order_total_and_lines_are_read_only(self):
        order = self.paid_order()
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:store_order_change', args=[order.pk]))
        self.assertNotContains(response, 'name="total_price"')
        self.assertNotContains(response, 'name="items-0-price"')
        self.assertNotContains(response, 'name="items-0-quantity"')
        self.assertEqual(self.client.get(reverse('admin:store_order_add')).status_code, 403)

    def test_ready_for_pickup_counts_as_paid_on_the_success_page(self):
        order = self.paid_order(shipping_method='pickup')
        Order.objects.filter(pk=order.pk).update(status='ready_for_pickup')
        order.refresh_from_db()
        with patch_icredit(FakeICredit(verified=False)):
            self.assertTrue(confirm_order_payment(order, SALE_ID))


class ProductCardHoverTests(TestCase):
    """תקריב שמוצג בריחוף על כרטיס מוצר בדף קטגוריה."""

    def setUp(self):
        self.category = Category.objects.create(name='חיתולי טטרה', slug='swaddles')
        self.product = make_product(category=self.category)
        self.folded = ProductImage.objects.create(product=self.product, image='products/folded.jpg')
        self.closeup = ProductImage.objects.create(product=self.product, image='products/closeup.jpg')

    def card_html(self):
        response = self.client.get(reverse('category_detail', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_card_has_no_hover_image_by_default(self):
        html = self.card_html()
        self.assertNotIn('class="product-card-print"', html)
        self.assertIn('closeup.jpg', html)  # עדיין חלק מגלריית החצים

    def test_marked_image_is_shown_on_hover_and_left_out_of_the_arrows(self):
        self.closeup.show_on_hover = True
        self.closeup.save()

        html = self.card_html()
        self.assertEqual(html.count('class="product-card-print"'), 1)
        hover_tag = html.split('class="product-card-print"')[0].rsplit('<img', 1)[1]
        self.assertIn('closeup.jpg', hover_tag)

        gallery = html.split("data-images='", 1)[1].split("'", 1)[0]
        self.assertIn('folded.jpg', gallery)
        self.assertNotIn('closeup.jpg', gallery)

        self.assertEqual(self.product.card_hover_image(), self.closeup)
        self.assertEqual(self.product.card_gallery_images(), [self.folded])

    def test_existing_print_closeups_are_marked_by_the_migration(self):
        import importlib
        from django.apps import apps as django_apps

        print_image = ProductImage.objects.create(product=self.product, image='media/products/set_print_ab12cd3')
        migration = importlib.import_module('store.migrations.0038_productimage_show_on_hover')
        migration.mark_existing_print_closeups(django_apps, None)

        print_image.refresh_from_db()
        self.closeup.refresh_from_db()
        self.assertTrue(print_image.show_on_hover)
        self.assertFalse(self.closeup.show_on_hover)


class SitePagesTests(TestCase):
    def test_not_found_page_is_in_hebrew(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'הדף שחיפשת לא נמצא', status_code=404)

    def test_category_has_a_url_for_footer_links(self):
        category = Category.objects.create(name='בגדים', slug='clothes')
        self.assertEqual(category.get_absolute_url(), reverse('category_detail', args=['clothes']))

    def test_home_page_renders(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_category_with_subcategories_shows_subcategory_tiles(self):
        category = Category.objects.create(name='בגדים', slug='clothes')
        subcategory = Subcategory.objects.create(name='בגדי גוף', slug='bodysuits', category=category)
        make_product(name='בגד גוף לבן', category=category, subcategory=subcategory)
        response = self.client.get(reverse('category_detail', args=['clothes']))
        self.assertTrue(response.context['has_subcategories'])
        self.assertNotContains(response, 'בגד גוף לבן')

    def test_category_can_show_all_products_instead_of_subcategories(self):
        category = Category.objects.create(name='בייסיקים', slug='basics', show_all_products=True)
        subcategory = Subcategory.objects.create(name='בגדי גוף', slug='bodysuits', category=category)
        make_product(name='בגד גוף לבן', category=category, subcategory=subcategory)
        make_product(name='מכנסיים', category=category)
        make_product(name='מוצר לא פעיל', category=category, is_active=False)
        response = self.client.get(reverse('category_detail', args=['basics']))
        self.assertFalse(response.context['has_subcategories'])
        self.assertEqual(
            sorted(p.name for p in response.context['products']),
            sorted(['בגד גוף לבן', 'מכנסיים']),
        )

    def test_product_page_shows_shipping_summary(self):
        product = make_product(slug='baby-suit')
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'יוצג כאן')
        self.assertContains(response, reverse('shipping_and_returns'))

    def test_product_page_hides_hover_closeup_from_gallery(self):
        product = make_product(slug='forest-set')
        ProductImage.objects.create(product=product, image='products/bodysuit.jpg')
        ProductImage.objects.create(product=product, image='products/prints.jpg', show_on_hover=True)
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bodysuit.jpg')
        self.assertNotContains(response, 'prints.jpg')

    def test_contact_email_escapes_user_input(self):
        with override_settings(RESEND_API_KEY='test-key'), mock.patch('store.views.resend.Emails.send') as send:
            self.client.post(reverse('contact'), {
                'full_name': '<script>alert(1)</script>',
                'phone': '0501234567',
                'email': 'dana@example.com',
                'order_number': '',
                'inquiry': 'שלום <img src=x>',
            })
        send.assert_called_once()
        html = send.call_args.args[0]['html']
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img src=x>', html)
        self.assertIn('&lt;script&gt;', html)


class NewsletterSubscribeTests(TestCase):
    def post_email(self, email):
        return self.client.post(
            reverse('newsletter_subscribe'),
            data=json.dumps({'email': email}),
            content_type='application/json',
        )

    @override_settings(RESEND_API_KEY='', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_missing_api_key_does_not_save_or_claim_success(self):
        response = self.post_email('new@example.com')
        self.assertFalse(response.json()['success'])
        self.assertFalse(NewsletterSubscriber.objects.filter(email='new@example.com').exists())

    @override_settings(RESEND_API_KEY='test-key', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_failed_send_removes_the_subscriber(self):
        with mock.patch('store.views.resend.Emails.send', side_effect=RuntimeError('down')):
            response = self.post_email('new@example.com')
        self.assertFalse(response.json()['success'])
        self.assertIn('לא הצלחנו לשלוח', response.json()['message'])
        self.assertFalse(NewsletterSubscriber.objects.filter(email='new@example.com').exists())

    @override_settings(RESEND_API_KEY='test-key', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_successful_send_saves_the_coupon(self):
        with mock.patch('store.views.resend.Emails.send') as send:
            response = self.post_email('new@example.com')
        self.assertTrue(response.json()['success'])
        subscriber = NewsletterSubscriber.objects.get(email='new@example.com')
        payload = send.call_args.args[0]
        self.assertEqual(payload['to'], ['new@example.com'])
        self.assertEqual(payload['from'], 'shop@example.com')
        self.assertIn(subscriber.coupon_code, payload['html'])


class ResendEmailBackendTests(TestCase):
    @override_settings(RESEND_API_KEY='test-key', DEFAULT_FROM_EMAIL='shop@example.com')
    def test_sends_through_resend(self):
        message = mail.EmailMessage('נושא', 'גוף ההודעה', None, ['dana@example.com'], reply_to=['owner@example.com'])
        with mock.patch('store.email_backend.resend.Emails.send') as send:
            sent = ResendEmailBackend().send_messages([message])
        self.assertEqual(sent, 1)
        params = send.call_args.args[0]
        self.assertEqual(params['from'], 'shop@example.com')
        self.assertEqual(params['to'], ['dana@example.com'])
        self.assertEqual(params['subject'], 'נושא')
        self.assertEqual(params['text'], 'גוף ההודעה')
        self.assertEqual(params['reply_to'], ['owner@example.com'])

    @override_settings(RESEND_API_KEY='test-key')
    def test_failure_raises_unless_fail_silently(self):
        message = mail.EmailMessage('נושא', 'גוף', 'shop@example.com', ['dana@example.com'])
        with mock.patch('store.email_backend.resend.Emails.send', side_effect=RuntimeError('down')):
            with self.assertRaises(RuntimeError):
                ResendEmailBackend().send_messages([message])
            self.assertEqual(ResendEmailBackend(fail_silently=True).send_messages([message]), 0)


class AddProductFromFolderTests(TestCase):
    def test_creates_product_with_gallery_in_the_given_order(self):
        category = Category.objects.create(name='ניובורן', slug='newborn')
        Size.objects.get_or_create(name='0-3')
        make_product(slug='taken')

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'תחבורה'
            source.mkdir()
            for filename in ('5PACK CARS.jpg', 'KIMONO AIRPLANE.jpg', 'KIMONO TRAIN.jpg'):
                Image.new('RGB', (4, 4), 'white').save(source / filename)
            args = dict(
                source_dir=str(source), main_image='5PACK CARS.jpg',
                gallery=['KIMONO TRAIN.jpg', 'KIMONO AIRPLANE.jpg'],
                name='מארז 5 בגדי גוף', subtitle='תחבורה', slug='5pack_transport',
                description='תיאור', price='150', stock=999, sizes='0-3',
                category_slug='newborn', stdout=StringIO(),
            )

            with override_settings(MEDIA_ROOT=str(Path(tmp) / 'media')):
                call_command('add_product_from_folder', dry_run=True, **args)
                self.assertFalse(Product.objects.filter(slug='5pack_transport').exists())

                call_command('add_product_from_folder', **args)
                product = Product.objects.get(slug='5pack_transport')
                self.assertTrue(product.image.storage.exists(product.image.name))

                with self.assertRaises(CommandError):
                    call_command('add_product_from_folder', **{**args, 'slug': 'taken'})
                with self.assertRaises(CommandError):
                    call_command('add_product_from_folder', **{**args, 'slug': 'other', 'main_image': 'missing.jpg'})

        self.assertEqual(product.price, Decimal('150'))
        self.assertEqual(product.stock_quantity, 999)
        self.assertEqual(product.category, category)
        self.assertEqual(product.subtitle, 'תחבורה')
        self.assertIn('5pack_cars', product.image.name)
        self.assertEqual(
            [(v.size.name, v.fabric_type) for v in product.variants.all()],
            [('0-3', None)],
        )
        gallery = list(product.images.all())
        self.assertEqual([img.order for img in gallery], [1, 2])
        self.assertIn('kimono_train', gallery[0].image.name)
        self.assertIn('kimono_airplane', gallery[1].image.name)
        self.assertEqual(Product.objects.count(), 2)


class RecommendedProductsTests(TestCase):
    """סקשן "מוצרים מומלצים" בתחתית דף המוצר."""

    def setUp(self):
        self.product = make_product(name='מוצר ראשי')

    def recommended_on_page(self, product=None):
        response = self.client.get(reverse('product_detail', args=[(product or self.product).slug]))
        self.assertEqual(response.status_code, 200)
        return response.context['recommended_products']

    def test_shows_products_chosen_in_admin(self):
        chosen = [make_product(name=f'נבחר {i}') for i in range(3)]
        make_product(name='הכי נמכר', is_bestseller=True)
        self.product.recommended_products.set(chosen)
        self.assertEqual(set(self.recommended_on_page()), set(chosen))

    def test_skips_inactive_chosen_products(self):
        active = make_product(name='פעיל')
        inactive = make_product(name='לא פעיל', is_active=False)
        self.product.recommended_products.set([active, inactive])
        self.assertEqual(self.recommended_on_page(), [active])

    def test_falls_back_to_home_page_bestsellers(self):
        bestsellers = [make_product(name=f'נמכר {i}', is_bestseller=True) for i in range(5)]
        make_product(name='רגיל')
        recommended = self.recommended_on_page()
        self.assertEqual(len(recommended), 4)
        self.assertTrue(set(recommended) <= set(bestsellers))

    def test_fallback_never_shows_the_product_itself(self):
        self.product.is_bestseller = True
        self.product.save()
        other = make_product(name='נמכר אחר', is_bestseller=True)
        self.assertEqual(self.recommended_on_page(), [other])

    def test_section_is_hidden_when_nothing_to_show(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertNotContains(response, 'recommended-products-section')

    def test_admin_allows_at_most_four(self):
        from .admin import ProductRecommendationsForm
        others = [make_product(name=f'אחר {i}') for i in range(5)]
        form = ProductRecommendationsForm(instance=self.product)
        data = {**form.initial, 'recommended_products': [p.pk for p in others]}
        data = {k: v for k, v in data.items() if v is not None}
        form = ProductRecommendationsForm(data=data, files={'image': None}, instance=self.product)
        form.is_valid()
        self.assertIn('recommended_products', form.errors)

        data['recommended_products'] = [p.pk for p in others[:4]]
        form = ProductRecommendationsForm(data=data, instance=self.product)
        form.is_valid()
        self.assertNotIn('recommended_products', form.errors)


class RateLimitTests(TestCase):
    """הגבלת קצב על טפסים ונקודות קצה ציבוריות."""

    def test_newsletter_is_limited_per_visitor(self):
        url = reverse('newsletter_subscribe')
        for _ in range(5):
            response = self.client.post(url, json.dumps({'email': 'not-an-email'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, json.dumps({'email': 'not-an-email'}), content_type='application/json')
        self.assertEqual(response.status_code, 429)

    def test_limit_is_counted_separately_per_visitor(self):
        url = reverse('newsletter_subscribe')
        for _ in range(6):
            self.client.post(url, json.dumps({'email': 'x'}), content_type='application/json', REMOTE_ADDR='10.0.0.1')
        response = self.client.post(
            url, json.dumps({'email': 'x'}), content_type='application/json', REMOTE_ADDR='10.0.0.2',
        )
        self.assertEqual(response.status_code, 200)

    def test_coupon_guessing_is_limited(self):
        product = make_product()
        self.client.post(reverse('add_to_cart', args=[product.id]), {'quantity': 1})
        url = reverse('apply_coupon')
        for _ in range(15):
            response = self.client.post(url, json.dumps({'coupon_code': 'NOPE'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, json.dumps({'coupon_code': 'NOPE'}), content_type='application/json')
        self.assertEqual(response.status_code, 429)

    def test_contact_form_is_limited(self):
        data = {'full_name': 'דנה', 'phone': '0501234567', 'email': 'd@example.com', 'inquiry': 'שלום'}
        for _ in range(5):
            self.client.post(reverse('contact'), data)
        self.assertEqual(ContactMessage.objects.count(), 5)
        self.client.post(reverse('contact'), data)
        self.assertEqual(ContactMessage.objects.count(), 5)

    def test_contact_honeypot_drops_bot_messages(self):
        data = {
            'full_name': 'bot', 'phone': '1', 'email': 'b@example.com', 'inquiry': 'spam',
            'extra_details': 'http://spam.example',
        }
        response = self.client.post(reverse('contact'), data)
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_admin_login_is_limited_per_account(self):
        url = reverse('admin:login')
        for _ in range(10):
            response = self.client.post(url, {'username': 'owner', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username': 'owner', 'password': 'wrong'}, REMOTE_ADDR='10.9.9.9')
        self.assertEqual(response.status_code, 429)


class ProductPagePrivacyTests(TestCase):
    def test_warehouse_location_is_not_exposed(self):
        product = make_product()
        size, _ = Size.objects.get_or_create(name='0-3')
        ProductVariant.objects.create(product=product, size=size, warehouse_location='SECRET-SHELF-7')
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'SECRET-SHELF-7')
        self.assertNotContains(response, 'warehouse_location')

    def test_newsletter_coupon_code_is_long(self):
        from .views import generate_coupon_code
        self.assertEqual(len(generate_coupon_code()), len('ARYE-') + 8)


class NewsletterPrivacyTests(TestCase):
    def setUp(self):
        self.subscriber = NewsletterSubscriber.objects.create(
            email='a@example.com', coupon_code='ARYE-ABCDEFGH', unsubscribe_token='t' * 32,
        )
        self.url = reverse('newsletter_unsubscribe', args=[self.subscriber.unsubscribe_token])

    def test_opening_the_unsubscribe_link_only_asks_for_confirmation(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<form method="post"')
        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)

    def test_confirming_unsubscribes(self):
        response = self.client.post(self.url)
        self.assertContains(response, 'ההרשמה בוטלה')
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.is_active)
        self.assertNotContains(self.client.get(self.url), '<form method="post"')

    def test_unknown_token(self):
        response = self.client.post(reverse('newsletter_unsubscribe', args=['nope']))
        self.assertContains(response, 'קישור לא תקין')

    def test_signup_does_not_reveal_existing_subscribers(self):
        response = self.client.post(
            reverse('newsletter_subscribe'), json.dumps({'email': 'A@example.com'}), content_type='application/json',
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertNotIn('already_exists', data)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)


class PageHardeningTests(TestCase):
    def test_payment_failure_page_ignores_text_from_the_url(self):
        response = self.client.get(reverse('payment_failure'), {'ErrorMessage': 'call-this-number-now'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'call-this-number-now')

    def test_category_page_has_no_buttons_inside_links_and_no_token_in_filter_form(self):
        category = Category.objects.create(name='ניובורן', slug='newborn-test')
        make_product(category=category)
        html = self.client.get(reverse('category_detail', args=[category.slug])).content.decode()
        for link in re.findall(r"<a [^>]*>.*?</a>", html, flags=re.S):
            self.assertNotIn('<button', link)
        filter_form = re.search(r'<form[^>]*id="filter-form".*?</form>', html, flags=re.S).group(0)
        self.assertNotIn('csrfmiddlewaretoken', filter_form)
        self.assertIn('csrfmiddlewaretoken', html)
