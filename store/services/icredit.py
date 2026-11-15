"""
iCredit Payment Gateway Service
שירות תשלומים באמצעות iCredit API (Rivhit)

הזרימה:
1. create_payment_page - יוצר דף תשלום (GetUrl) בסכום הזהה ל-order.total_price.
2. iCredit שולח IPN לשרת אחרי תשלום, עם SaleId.
3. verify_payment - שואל את iCredit (Verify) אם העסקה באמת שולמה בסכום ההזמנה.
   רק תשובת VERIFIED מאפשרת לסמן הזמנה כ"שולמה".
"""
import json
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
MAX_DESCRIPTION_LENGTH = 120

# iCredit דוחה בקשות ללא User-Agent של לקוח HTTP מוכר
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'PostmanRuntime/7.32.0',
    'Accept': '*/*',
}


@dataclass
class PaymentPageResult:
    ok: bool
    url: str = ''
    private_sale_token: str = ''
    public_sale_token: str = ''
    error: str = ''


def is_valid_sale_id(sale_id):
    """SaleId של iCredit הוא GUID."""
    try:
        uuid.UUID(str(sale_id))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def _split_name(full_name):
    parts = (full_name or '').split()
    first_name = parts[0] if parts else 'לקוח'
    last_name = ' '.join(parts[1:]) if len(parts) > 1 else 'לקוח'
    return first_name, last_name


def build_items(order):
    """
    שורות החיוב של ההזמנה: פריטים + שורת משלוח.
    מחזיר (items, discount). אם סכום השורות פחות ההנחה אינו שווה בדיוק
    ל-order.total_price, מוחזרת שורה מסכמת אחת בסכום ההזמנה - כך שהלקוח
    לעולם לא יחויב בסכום שונה ממה שהוצג לו.
    """
    items = []
    lines_total = Decimal('0.00')

    for item in order.items.select_related('product', 'variant__size', 'variant__fabric_type'):
        description = item.product.name
        if item.variant:
            description = f'{description} - {item.variant.get_display_name()}'
        items.append({
            'UnitPrice': float(item.price),
            'Quantity': int(item.quantity),
            'Description': description[:MAX_DESCRIPTION_LENGTH],
        })
        lines_total += item.price * item.quantity

    if order.shipping_fee and order.shipping_fee > 0:
        items.append({
            'UnitPrice': float(order.shipping_fee),
            'Quantity': 1,
            'Description': 'משלוח עד הבית',
        })
        lines_total += order.shipping_fee

    discount = order.discount_amount or Decimal('0.00')

    if lines_total - discount != order.total_price:
        logger.warning(
            'Order %s: line items (%s) minus discount (%s) do not match total (%s); sending a single summary line',
            order.id, lines_total, discount, order.total_price,
        )
        return [{
            'UnitPrice': float(order.total_price),
            'Quantity': 1,
            'Description': f'הזמנה #{order.id} - אריה בוטיק',
        }], Decimal('0.00')

    return items, discount


def build_payment_payload(order, success_url, failure_url, ipn_url=None):
    """בניית גוף הבקשה ל-GetUrl."""
    items, discount = build_items(order)
    first_name, last_name = _split_name(order.guest_name)

    payload = {
        'GroupPrivateToken': settings.ICREDIT_GROUP_PRIVATE_TOKEN,
        'Items': items,
        'RedirectURL': success_url,
        'FailRedirectURL': failure_url,
        'Currency': 1,  # 1 = ILS
        'MaxPayments': 1,
        'DocumentLanguage': 'he',
        'CustomerFirstName': first_name,
        'CustomerLastName': last_name,
        'EmailAddress': order.guest_email or '',
        'PhoneNumber': order.guest_phone or '',
        'Address': order.guest_address or '',
        'City': order.guest_city or '',
        # מזהה ההזמנה - חוזר אלינו ב-IPN
        'Custom1': str(order.id),
        'Order': str(order.id),
    }
    if discount > 0:
        payload['Discount'] = float(discount)
    if ipn_url:
        payload['IPNURL'] = ipn_url
    return payload


def create_payment_page(order, success_url, failure_url, ipn_url=None):
    """
    יצירת דף תשלום ב-iCredit עבור ההזמנה.
    """
    payload = build_payment_payload(order, success_url, failure_url, ipn_url)

    try:
        response = requests.post(
            settings.ICREDIT_API_URL,
            data=json.dumps(payload),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error('iCredit GetUrl request failed for order %s: %s', order.id, exc)
        return PaymentPageResult(ok=False, error='connection')

    if response.status_code != 200:
        logger.error('iCredit GetUrl returned HTTP %s for order %s', response.status_code, order.id)
        return PaymentPageResult(ok=False, error=f'http {response.status_code}')

    try:
        data = response.json()
    except ValueError:
        logger.error('iCredit GetUrl returned a non-JSON response for order %s', order.id)
        return PaymentPageResult(ok=False, error='invalid response')

    if data.get('Status') != 0 or not data.get('URL'):
        error = data.get('DebugMessage') or data.get('ErrorMessage') or data.get('StatusDescription') or f"status {data.get('Status')}"
        logger.error('iCredit GetUrl error for order %s: %s', order.id, error)
        return PaymentPageResult(ok=False, error=str(error))

    logger.info('iCredit payment page created for order %s (amount %s)', order.id, order.total_price)
    return PaymentPageResult(
        ok=True,
        url=data['URL'],
        private_sale_token=str(data.get('PrivateSaleToken') or ''),
        public_sale_token=str(data.get('PublicSaleToken') or ''),
    )


EMPTY_GUID = '00000000-0000-0000-0000-000000000000'


def find_sale_id(sale_private_token):
    """
    שליפת מזהה העסקה (SaleId) של דף תשלום לפי ה-PrivateSaleToken שקיבלנו ב-GetUrl.
    מחזיר '' אם עדיין אין עסקה. התשובה אינה הוכחת תשלום - את זה קובע רק verify_payment.
    """
    if not is_valid_sale_id(sale_private_token):
        return ''

    try:
        response = requests.post(
            settings.ICREDIT_SALE_DETAILS_URL,
            data=json.dumps({'SalePrivateToken': str(sale_private_token)}),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        data = response.json() if response.status_code == 200 else {}
    except (requests.RequestException, ValueError) as exc:
        logger.error('iCredit SaleDetails request failed: %s', exc)
        return ''

    if not isinstance(data, dict):
        return ''
    sale_id = str(data.get('SaleId') or '').strip().lower()
    if not sale_id or sale_id == EMPTY_GUID or not is_valid_sale_id(sale_id):
        return ''
    return sale_id


def verify_payment(sale_id, amount):
    """
    אימות מול iCredit שהעסקה sale_id שולמה בסכום amount.
    מחזיר True רק אם iCredit ענה VERIFIED.
    """
    if not is_valid_sale_id(sale_id):
        return False

    payload = {
        'GroupPrivateToken': settings.ICREDIT_GROUP_PRIVATE_TOKEN,
        'SaleId': str(sale_id),
        'TotalAmount': float(amount),
    }

    try:
        response = requests.post(
            settings.ICREDIT_VERIFY_URL,
            data=json.dumps(payload),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        data = response.json() if response.status_code == 200 else {}
    except (requests.RequestException, ValueError) as exc:
        logger.error('iCredit Verify request failed for sale %s: %s', sale_id, exc)
        return False

    status = str(data.get('Status') or '').strip().upper()
    if status != 'VERIFIED':
        logger.warning('iCredit Verify for sale %s amount %s returned %r', sale_id, amount, status or response.status_code)
        return False
    return True
