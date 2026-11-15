"""
חישוב סכומי הזמנה: סכום ביניים, הנחת קופון, דמי משלוח וסה"כ.

כל מקום באתר שמציג או גובה סכום משתמש ב-calculate_totals, כדי שמה שמוצג
ללקוח יהיה תמיד זהה למה שנשלח לסליקה.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from ..models import Coupon, NewsletterSubscriber
from .shipping import (
    SHIPPING_DELIVERY,
    SHIPPING_PICKUP,
    amount_to_free_shipping,
    calculate_shipping_fee,
)

CENT = Decimal('0.01')
ZERO = Decimal('0.00')

COUPON_GENERAL = 'general'
COUPON_NEWSLETTER = 'newsletter'


def money(value):
    """עיגול לשתי ספרות אחרי הנקודה."""
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class CouponResult:
    code: str = ''
    coupon_type: str = ''
    discount: Decimal = ZERO
    percent: int = 0
    error: str = ''

    @property
    def is_valid(self):
        return bool(self.coupon_type) and not self.error


def evaluate_coupon(code, subtotal):
    """
    בדיקת קוד קופון מול סכום הביניים. מחזיר CouponResult; אם הקופון לא תקף,
    השדה error מכיל הודעה להצגה ללקוח.
    """
    code = (code or '').strip().upper()
    subtotal = money(subtotal)
    result = CouponResult(code=code)

    if not code:
        result.error = 'נא להזין קוד קופון'
        return result

    coupon = Coupon.objects.filter(code__iexact=code).first()
    if coupon:
        if not coupon.is_valid():
            result.error = 'הקופון אינו תקף או פג תוקפו'
            return result
        if coupon.minimum_order_amount > 0 and subtotal < coupon.minimum_order_amount:
            result.error = f'סכום מינימום להזמנה עם קופון זה: {coupon.minimum_order_amount}₪'
            return result
        result.coupon_type = COUPON_GENERAL
        result.discount = min(money(coupon.calculate_discount(subtotal)), subtotal)
        if coupon.discount_type == 'percent':
            result.percent = int(coupon.discount_value)
        return result

    subscriber = NewsletterSubscriber.objects.filter(coupon_code__iexact=code).first()
    if subscriber:
        if not subscriber.is_active:
            result.error = 'הקופון אינו פעיל'
            return result
        if subscriber.is_used:
            result.error = 'הקופון כבר נוצל'
            return result
        result.coupon_type = COUPON_NEWSLETTER
        result.percent = subscriber.discount_percent
        result.discount = min(money(subtotal * Decimal(subscriber.discount_percent) / 100), subtotal)
        return result

    result.error = 'קוד קופון לא נמצא'
    return result


@dataclass
class Totals:
    subtotal: Decimal = ZERO
    discount: Decimal = ZERO
    shipping_method: str = SHIPPING_DELIVERY
    shipping_fee: Decimal = ZERO
    delivery_fee: Decimal = ZERO  # דמי המשלוח אילו נבחר משלוח עד הבית
    remaining_for_free_shipping: Decimal = ZERO
    total: Decimal = ZERO
    coupon: CouponResult = field(default_factory=CouponResult)

    @property
    def coupon_code(self):
        return self.coupon.code if self.coupon.is_valid else ''

    def as_json(self):
        """ערכים מספריים לשימוש ב-JavaScript."""
        return {
            'subtotal': float(self.subtotal),
            'discount_amount': float(self.discount),
            'discount_percent': self.coupon.percent if self.coupon.is_valid else 0,
            'coupon_code': self.coupon_code,
            'shipping_method': self.shipping_method,
            'shipping_fee': float(self.shipping_fee),
            'delivery_fee': float(self.delivery_fee),
            'remaining_for_free_shipping': float(self.remaining_for_free_shipping),
            'total': float(self.total),
        }


def calculate_totals(subtotal, coupon_code='', shipping_method=SHIPPING_DELIVERY):
    """
    חישוב כל סכומי ההזמנה. מדרגת המשלוח נקבעת לפי הסכום אחרי הנחת הקופון.
    """
    if shipping_method not in (SHIPPING_DELIVERY, SHIPPING_PICKUP):
        shipping_method = SHIPPING_DELIVERY

    subtotal = money(subtotal)
    coupon = evaluate_coupon(coupon_code, subtotal) if coupon_code else CouponResult()
    discount = coupon.discount if coupon.is_valid else ZERO

    after_discount = subtotal - discount
    delivery_fee = calculate_shipping_fee(after_discount, SHIPPING_DELIVERY)
    shipping_fee = calculate_shipping_fee(after_discount, shipping_method)

    return Totals(
        subtotal=subtotal,
        discount=discount,
        shipping_method=shipping_method,
        shipping_fee=shipping_fee,
        delivery_fee=delivery_fee,
        remaining_for_free_shipping=amount_to_free_shipping(after_discount),
        total=after_discount + shipping_fee,
        coupon=coupon,
    )
