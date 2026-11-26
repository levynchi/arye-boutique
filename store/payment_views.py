"""
תשלום דרך iCredit: יצירת דף תשלום, חזרה מהתשלום ו-IPN.

הזמנה מסומנת כ"שולמה" אך ורק אחרי ש-iCredit אישר (Verify) שהעסקה שולמה
בסכום ההזמנה. שום פרמטר שמגיע מהדפדפן לא משנה סטטוס של הזמנה.
"""
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import Category, Order
from .seo import product_full_name
from .services import icredit
from .services.orders import (
    PAID_STATUSES,
    confirm_order_payment,
    confirm_order_payment_by_token,
    finalize_paid_order,
)
from .services.shipping import PICKUP_ADDRESS
from .views import get_or_create_cart

logger = logging.getLogger(__name__)

LOCAL_HOSTS = ('127.0.0.1', 'localhost', 'testserver')

# כמה פעמים דף ההצלחה מתרענן בזמן ההמתנה לאישור מ-iCredit
MAX_PENDING_CHECKS = 10


def _is_local_host(host):
    return host.split(':')[0] in LOCAL_HOSTS


def _callback_urls(request, order):
    """
    כתובות החזרה לדף התשלום, לפי הדומיין שממנו הלקוח גולש.
    iCredit לא מקבל כתובות localhost, ולכן בפיתוח מקומי אין IPN.
    """
    host = request.get_host()
    if _is_local_host(host):
        return 'https://example.com/success', 'https://example.com/failure', None

    base_url = f'https://{host}'
    ipn_base_url = (settings.PAYMENT_IPN_BASE_URL or base_url).rstrip('/')
    return (
        base_url + reverse('payment_success'),
        base_url + reverse('payment_failure'),
        ipn_base_url + reverse('payment_notify'),
    )


def initiate_payment(request, order_id):
    """
    יצירת דף תשלום ב-iCredit והפניית הלקוח אליו
    """
    # חסימה במצב דמו
    if request.session.get('demo_mode'):
        messages.info(request, 'זהו אתר דמו — רכישות אינן זמינות')
        return redirect('home')

    # רק מי שיצר את ההזמנה (באותו סשן) יכול לשלם עליה
    if request.session.get('pending_order_id') != order_id:
        messages.error(request, 'ההזמנה לא נמצאה. אנא נסו שוב מהעגלה.')
        return redirect('cart')

    order = Order.objects.filter(id=order_id).first()
    if not order or order.status != 'pending':
        messages.error(request, 'הזמנה זו כבר שולמה או בוטלה')
        return redirect('home')

    # הזמנה שהקופון מכסה במלואה - אין מה לסלוק
    if order.total_price <= 0:
        finalize_paid_order(order.id)
        return redirect('payment_success')

    success_url, failure_url, ipn_url = _callback_urls(request, order)
    result = icredit.create_payment_page(order, success_url, failure_url, ipn_url)

    if not result.ok:
        messages.error(request, 'לא הצלחנו לפתוח את דף התשלום. אנא נסו שוב בעוד רגע או צרו איתנו קשר.')
        return redirect('checkout')

    order.payment_reference = result.public_sale_token
    order.payment_token = result.private_sale_token
    order.save(update_fields=['payment_reference', 'payment_token', 'updated_at'])

    return redirect(result.url)


def _lookup(data, *names):
    """קריאת ערך מה-IPN בלי תלות באותיות גדולות/קטנות בשם השדה."""
    lowered = {str(key).lower(): value for key, value in data.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ''):
            return str(value).strip()
    return ''


def _session_order(request):
    """ההזמנה של הגולש הנוכחי: זו שממתינה לתשלום, או האחרונה ששולמה."""
    for key in ('pending_order_id', 'last_order_id'):
        order_id = request.session.get(key)
        if order_id:
            order = Order.objects.filter(id=order_id).first()
            if order:
                return order
    return None


def payment_success(request):
    """
    הדף שאליו הלקוח חוזר מ-iCredit אחרי תשלום.

    הדף מציג רק את ההזמנה השמורה בסשן של הגולש, ואינו מסמן הזמנה כ"שולמה"
    בלי אימות מול iCredit.
    """
    order = _session_order(request)

    if order is None:
        messages.info(request, 'לא נמצאה הזמנה להצגה.')
        return redirect('home')

    sale_id = _lookup(request.GET, 'SaleId')
    if not icredit.is_valid_sale_id(sale_id):
        sale_id = ''

    if order.status == 'pending':
        if sale_id:
            # אם iCredit צירף את מזהה העסקה לכתובת החזרה - נאמת מיד, בלי לחכות ל-IPN
            confirm_order_payment(order, sale_id)
        else:
            # גיבוי: שואלים את iCredit על העסקה לפי הטוקן של דף התשלום
            confirm_order_payment_by_token(order)
        order.refresh_from_db()

    is_paid = order.status in PAID_STATUSES

    if is_paid and request.session.get('pending_order_id') == order.id:
        # ניקוי העגלה והסשן - פעם אחת, כשהתשלום אושר
        get_or_create_cart(request).items.all().delete()
        for key in ('applied_coupon', 'pending_coupon', 'pending_order_id', 'pending_order_total'):
            request.session.pop(key, None)
        request.session['last_order_id'] = order.id

    try:
        check = max(0, int(request.GET.get('check', 0)))
    except (TypeError, ValueError):
        check = 0

    # כתובת הרענון בזמן ההמתנה לאישור. מזהה העסקה נשמר בה כדי שהאימות ינוסה שוב
    refresh_url = f"{reverse('payment_success')}?check={check + 1}"
    if sale_id:
        refresh_url += f'&SaleId={sale_id}'

    # נתוני הרכישה לפיקסלים (נשלחים מהדפדפן פעם אחת להזמנה, ורק אחרי אישור עוגיות)
    tracking_purchase = None
    if is_paid:
        tracking_purchase = {
            'order_id': order.id,
            'value': float(order.total_price),
            'items': [
                {
                    'id': item.product_id,
                    'name': product_full_name(item.product),
                    'price': float(item.price),
                    'quantity': item.quantity,
                }
                for item in order.items.select_related('product')
            ],
        }

    context = {
        'tracking_purchase': tracking_purchase,
        'order': order,
        'is_paid': is_paid,
        'payment_pending': order.status == 'pending',
        'keep_checking': order.status == 'pending' and check < MAX_PENDING_CHECKS,
        'refresh_url': refresh_url,
        'pickup_address': PICKUP_ADDRESS,
        'categories': Category.objects.filter(is_active=True),
    }

    return render(request, 'store/payment_success.html', context)


def payment_failure(request):
    """
    דף כישלון תשלום
    """
    context = {
        'categories': Category.objects.filter(is_active=True),
    }

    return render(request, 'store/payment_failure.html', context)


def _ipn_data(request):
    """גוף ה-IPN - JSON או טופס רגיל."""
    body = (request.body or b'').strip()
    if body.startswith(b'{'):
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None
    data = request.POST.dict()
    return data or None


@csrf_exempt
def payment_notify(request):
    """
    IPN (Instant Payment Notification) - הודעה מ-iCredit על תשלום.

    כל אחד יכול לשלוח בקשה לכתובת הזו, ולכן לא סומכים על התוכן שלה:
    לוקחים ממנה רק את מזהה ההזמנה ואת מזהה העסקה, ומאמתים מול iCredit.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    data = _ipn_data(request)
    if data is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid request body'}, status=400)

    sale_id = _lookup(data, 'SaleId')
    order_ref = _lookup(data, 'Custom1', 'Order')

    # שמות השדות בלבד (בלי ערכים) - כדי שאפשר יהיה לאבחן שינויים בפורמט ה-IPN
    logger.info('IPN received: order=%s fields=%s', order_ref or '-', sorted(str(key) for key in data.keys()))

    is_order_id = order_ref.isascii() and order_ref.isdigit() and len(order_ref) <= 12
    order = Order.objects.filter(id=int(order_ref)).first() if is_order_id else None
    if order is None:
        logger.warning('IPN ignored: no matching order (order=%r)', order_ref)
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)

    if confirm_order_payment(order, sale_id):
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'error', 'message': 'Payment not verified'}, status=400)
