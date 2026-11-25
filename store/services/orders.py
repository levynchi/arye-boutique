"""
סגירת הזמנה אחרי תשלום: סימון כ"שולם", הורדת מלאי, רישום שימוש בקופון ומיילים.
"""
import logging

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ..models import Coupon, NewsletterSubscriber, Order, OrderPayment, Product
from . import icredit
from .emails import send_new_order_notification, send_order_confirmation_email, send_owner_alert

logger = logging.getLogger(__name__)

# סטטוסים של הזמנה שהתשלום עליה כבר אושר
PAID_STATUSES = ('paid', 'confirmed', 'ready_for_pickup', 'shipped', 'delivered')


def _normalize_sale_id(sale_id):
    return str(sale_id or '').strip().lower()


def _append_note(existing, note):
    return f'{existing}\n{note}' if existing else note


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

        # הורדת מלאי - רק עכשיו, כשהתשלום אושר
        oversold = []
        for item in order.items.all():
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if product.stock_quantity < item.quantity:
                logger.warning(
                    'Order %s: product %s oversold (stock %s, ordered %s)',
                    order.id, product.id, product.stock_quantity, item.quantity,
                )
                oversold.append(
                    f'"{product.name}": הוזמנו {item.quantity}, במלאי היו {product.stock_quantity}'
                )
            product.stock_quantity = max(0, product.stock_quantity - item.quantity)
            product.save(update_fields=['stock_quantity', 'updated_at'])

        # המלאי לא שמור בזמן התשלום, ולכן שני לקוחות יכולים לשלם על הפריט האחרון.
        # ההזמנה כבר שולמה - מסמנים אותה כדי שבעל האתר יטפל (אספקה או זיכוי).
        if oversold:
            order.needs_attention = True
            order.attention_note = _append_note(
                order.attention_note, 'נמכר מעבר למלאי - ' + '; '.join(oversold)
            )
        order.save(update_fields=[
            'status', 'paid_at', 'payment_transaction_id', 'needs_attention', 'attention_note', 'updated_at',
        ])

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


def _record_extra_payment(order, sale_id):
    """
    תשלום שהגיע על הזמנה שכבר שולמה או בוטלה (למשל שני דפי תשלום פתוחים).
    ההזמנה לא משתנה, אבל אם iCredit מאשר שהעסקה שולמה - רושמים אותה כתשלום
    כפול ומתריעים לבעל האתר כדי שיזכה את הלקוח.
    """
    if not icredit.is_valid_sale_id(sale_id):
        return False
    sale_id = _normalize_sale_id(sale_id)
    if sale_id == _normalize_sale_id(order.payment_transaction_id):
        return False
    if OrderPayment.objects.filter(sale_id=sale_id).exists():
        return False
    if not icredit.verify_payment(sale_id, order.total_price):
        return False

    note = f'תשלום נוסף על הזמנה סגורה - עסקה {sale_id} על סך {order.total_price} ₪. יש לזכות את הלקוח ב-iCredit.'
    try:
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=order.pk)
            OrderPayment.objects.create(order=locked, sale_id=sale_id, amount=locked.total_price, is_duplicate=True)
            locked.needs_attention = True
            locked.attention_note = _append_note(locked.attention_note, note)
            locked.save(update_fields=['needs_attention', 'attention_note', 'updated_at'])
    except IntegrityError:
        # אותה עסקה כבר נרשמה בבקשה מקבילה
        return False

    logger.warning('Order %s: extra payment %s on a closed order', order.id, sale_id)
    try:
        send_owner_alert(locked, 'תשלום כפול', note)
    except Exception:
        logger.exception('Order %s: duplicate payment alert failed', order.id)
    return True


def confirm_order_payment(order, sale_id):
    """
    אישור תשלום להזמנה לפי SaleId שהתקבל מ-iCredit.
    ההזמנה מסומנת כ"שולמה" רק אם iCredit מאשר (Verify) שהעסקה שולמה
    בסכום ההזמנה, ורק אם אותה עסקה לא שויכה כבר להזמנה אחרת.

    מחזיר True אם ההזמנה שולמה (עכשיו או קודם).
    """
    if order.status != 'pending':
        # ההזמנה כבר סגורה (שולמה או בוטלה). אם זו עסקה אחרת - הלקוח חויב שוב
        _record_extra_payment(order, sale_id)
        return order.status in PAID_STATUSES

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
