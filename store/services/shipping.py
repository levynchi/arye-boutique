"""
חישוב דמי משלוח - מקור אמת יחיד לכל האתר (עגלה, קופה, מיילים, סליקה).

המדיניות המפורסמת בדף "משלוחים והחזרות":
    עד 99 ש"ח      - 39 ש"ח
    100-299 ש"ח    - 25 ש"ח
    מעל 299 ש"ח    - חינם
    איסוף עצמי     - ללא עלות
"""
from decimal import Decimal

SHIPPING_DELIVERY = 'delivery'
SHIPPING_PICKUP = 'pickup'

SHIPPING_METHOD_CHOICES = [
    (SHIPPING_DELIVERY, 'משלוח עד הבית'),
    (SHIPPING_PICKUP, 'איסוף עצמי'),
]

# (סכום הזמנה קטן מ-, דמי משלוח)
DELIVERY_TIERS = [
    (Decimal('100'), Decimal('39.00')),
    (Decimal('300'), Decimal('25.00')),
]

FREE_SHIPPING_FROM = Decimal('300')

PICKUP_ADDRESS = 'רחוב הקישון 6, תל אביב'

ZERO = Decimal('0.00')


def calculate_shipping_fee(amount, method=SHIPPING_DELIVERY):
    """
    דמי משלוח לפי סכום ההזמנה (אחרי הנחת קופון) ושיטת המשלוח.
    """
    amount = Decimal(amount or 0)
    if method == SHIPPING_PICKUP or amount <= 0:
        return ZERO
    for limit, fee in DELIVERY_TIERS:
        if amount < limit:
            return fee
    return ZERO


def amount_to_free_shipping(amount):
    """
    כמה חסר כדי להגיע למשלוח חינם (0 אם כבר הגענו).
    """
    amount = Decimal(amount or 0)
    if amount <= 0 or amount >= FREE_SHIPPING_FROM:
        return ZERO
    return FREE_SHIPPING_FROM - amount
