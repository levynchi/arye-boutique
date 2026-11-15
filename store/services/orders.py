"""
סגירת הזמנה אחרי תשלום: סימון כ"שולם", הורדת מלאי, רישום שימוש בקופון ומיילים.
"""
import logging

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ..models import Coupon, NewsletterSubscriber, Order, OrderPayment, Product
from . import icredit
from .emails import send_new_order_notification, send_order_confirmation_email

logger = logging.getLogger(__name__)

# סטטוסים של הזמנה שהתשלום עליה כבר אושר
PAID_STATUSES = ('paid', 'confirmed', 'shipped', 'delivered')


def _normalize_sale_id(sale_id):
    return str(sale_id or '').strip().lower()


def _mark_paid(order_id, sale_id):
    """
    החלק האטומי: סטטוס, רישום התשלום, מלאי וקופון - הכול או כלום.
    מחזיר (order, newly_paid).
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.status != 'pending':
            return order, False

        order.status = 'paid'
        order.paid_at = timezone.now()
        if sale_id:
            order.payment_transaction_id = sale_id
            # sale_id ייחודי במסד הנתונים: אם אותה עסקה כבר שולמה על הזמנה אחרת,
            # השורה הזו נכשלת וכל הפעולה מתבטלת
            OrderPayment.objects.create(order=order, sale_id=sale_id, amount=order.total_price)
        order.save(update_fields=['status', 'paid_at', 'payment_transaction_id', 'updated_at'])

        # הורדת מלאי - רק עכשיו, כשהתשלום אושר
        for item in order.items.all():
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if product.stock_quantity < item.quantity:
                logger.warning(
                    'Order %s: product %s oversold (stock %s, ordered %s)',
                    order.id, product.id, product.stock_quantity, item.quantity,
                )
            product.stock_quantity = max(0, product.stock_quantity - item.quantity)
            product.save(update_fields=['stock_quantity', 'updated_at'])

        # רישום שימוש בקופון
        if order.coupon_code:
            updated = Coupon.objects.filter(code__iexact=order.coupon_code).update(times_used=F('times_used') + 1)
            if not updated:
                NewsletterSubscriber.objects.filter(coupon_code__iexact=order.coupon_code).update(is_used=True)

    return order, True


def finalize_paid_order(order_id, sale_id=''):
    """
    סימון הזמנה כ"שולמה". הפעולה אטומית ורצה פעם אחת בלבד לכל הזמנה:
    קריאה חוזרת (למשל IPN כפול) לא משנה דבר.

    מחזיר (order, newly_paid).
    """
    sale_id = _normalize_sale_id(sale_id)

    try:
        order, newly_paid = _mark_paid(order_id, sale_id)
    except IntegrityError:
        logger.warning('Order %s: sale %s is already attached to another order', order_id, sale_id)
        return Order.objects.get(pk=order_id), False

    if not newly_paid:
        return order, False

    logger.info('Order %s marked as paid', order.id)

    # מיילים - כישלון בשליחה לא מבטל את ההזמנה
    for send in (send_order_confirmation_email, send_new_order_notification):
        try:
            send(order)
        except Exception:
            logger.exception('Order %s: %s failed', order.id, send.__name__)

    return order, True


def _sale_already_used(sale_id, order):
    return (
        OrderPayment.objects.filter(sale_id=sale_id).exclude(order=order).exists()
        or Order.objects.filter(payment_transaction_id__iexact=sale_id).exclude(pk=order.pk).exists()
    )


def confirm_order_payment(order, sale_id):
    """
    אישור תשלום להזמנה לפי SaleId שהתקבל מ-iCredit.
    ההזמנה מסומנת כ"שולמה" רק אם iCredit מאשר (Verify) שהעסקה שולמה
    בסכום ההזמנה, ורק אם אותה עסקה לא שויכה כבר להזמנה אחרת.

    מחזיר True אם ההזמנה שולמה (עכשיו או קודם).
    """
    if order.status in PAID_STATUSES:
        return True
    if order.status != 'pending':
        return False

    if not icredit.is_valid_sale_id(sale_id):
        logger.warning('Order %s: payment confirmation with an invalid sale id', order.id)
        return False

    sale_id = _normalize_sale_id(sale_id)
    if _sale_already_used(sale_id, order):
        logger.warning('Order %s: sale %s is already attached to another order', order.id, sale_id)
        return False

    if not icredit.verify_payment(sale_id, order.total_price):
        logger.warning('Order %s: payment for sale %s was NOT verified by iCredit', order.id, sale_id)
        return False

    order, _ = finalize_paid_order(order.pk, sale_id)
    return order.status in PAID_STATUSES


def confirm_order_payment_by_token(order):
    """
    גיבוי למקרה שה-IPN לא הגיע: שואלים את iCredit על העסקה לפי הטוקן שקיבלנו
    כשיצרנו את דף התשלום, ואם יש עסקה - מאמתים אותה כרגיל (Verify).
    """
    if order.status in PAID_STATUSES:
        return True
    if order.status != 'pending' or not order.payment_token:
        return False

    sale_id = icredit.find_sale_id(order.payment_token)
    if not sale_id:
        return False
    return confirm_order_payment(order, sale_id)
