"""
עגלת קניות, קופה וקופונים.
"""
import json
import logging
from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CheckoutForm
from .models import CartItem, Category, Order, OrderItem
from .ratelimit import is_rate_limited
from .seo import product_full_name
from .services.pricing import calculate_totals, evaluate_coupon
from .services.shipping import FREE_SHIPPING_FROM, PICKUP_ADDRESS, SHIPPING_DELIVERY, SHIPPING_PICKUP
from .views import get_or_create_cart

logger = logging.getLogger(__name__)


def _cart_items(cart):
    return cart.items.all().select_related('product', 'variant', 'variant__product')


def get_cart_totals(request, cart, shipping_method=SHIPPING_DELIVERY):
    """
    סכומי העגלה, כולל קופון שהוחל (מהסשן) ודמי משלוח.
    קופון שכבר לא תקף מוסר מהסשן.
    """
    applied_coupon = request.session.get('applied_coupon') or {}
    coupon_code = applied_coupon.get('code', '')
    totals = calculate_totals(cart.total_price, coupon_code, shipping_method)
    if coupon_code and not totals.coupon.is_valid:
        request.session.pop('applied_coupon', None)
    return totals


def _clean_shipping_method(value):
    return value if value in (SHIPPING_DELIVERY, SHIPPING_PICKUP) else SHIPPING_DELIVERY


def cart_view(request):
    """
    עמוד עגלת הקניות
    """
    cart = get_or_create_cart(request)
    totals = get_cart_totals(request, cart)

    context = {
        'cart': cart,
        'cart_items': _cart_items(cart),
        'totals': totals,
        'subtotal': totals.subtotal,
        'shipping_fee': totals.shipping_fee,
        'total': totals.total,
        'pickup_address': PICKUP_ADDRESS,
        'categories': Category.objects.filter(is_active=True),
    }

    return render(request, 'store/cart.html', context)


def _cart_summary_json(request, cart):
    totals = get_cart_totals(request, cart)
    return {
        'cart_subtotal': float(totals.subtotal),
        'discount_amount': float(totals.discount),
        'shipping_fee': float(totals.shipping_fee),
        'remaining_for_free_shipping': float(totals.remaining_for_free_shipping),
        'cart_total': float(totals.total),
        'total_items': cart.total_items,
    }


def cart_update_quantity(request, item_id):
    """
    עדכון כמות פריט בעגלה - AJAX
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        new_quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'כמות לא תקינה'}, status=400)

    if new_quantity < 1:
        return JsonResponse({'success': False, 'error': 'הכמות חייבת להיות לפחות 1'}, status=400)

    # בדיקת מלאי
    if new_quantity > cart_item.product.stock_quantity:
        return JsonResponse({
            'success': False,
            'error': f'הכמות המבוקשת גדולה מהמלאי הזמין ({cart_item.product.stock_quantity})'
        }, status=400)

    cart_item.quantity = new_quantity
    cart_item.save()

    response = {'success': True, 'item_subtotal': float(cart_item.subtotal)}
    response.update(_cart_summary_json(request, cart))
    return JsonResponse(response)


def cart_remove_item(request, item_id):
    """
    הסרת פריט מהעגלה - AJAX
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    product_name = cart_item.product.name
    cart_item.delete()

    response = {'success': True, 'message': f'המוצר "{product_name}" הוסר מהעגלה'}
    response.update(_cart_summary_json(request, cart))
    return JsonResponse(response)


def cart_data(request):
    """
    API endpoint להחזרת נתוני העגלה בפורמט JSON
    """
    cart = get_or_create_cart(request)
    totals = get_cart_totals(request, cart)

    items_data = []
    for item in _cart_items(cart):
        unit_price = item.variant.effective_price if item.variant else item.product.price
        items_data.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'product_subtitle': item.product.subtitle or '',
            'product_image': item.product.image.url if item.product.image else '',
            'product_price': float(unit_price),
            'product_size': item.product.size or '',
            'variant_display': item.variant.get_display_name() if item.variant else '',
            'quantity': item.quantity,
            'max_quantity': item.product.stock_quantity,
            'subtotal': float(item.subtotal),
        })

    return JsonResponse({
        'success': True,
        'items': items_data,
        'subtotal': float(totals.subtotal),
        'discount_amount': float(totals.discount),
        'shipping_fee': float(totals.shipping_fee),
        'total': float(totals.total),
        'total_items': cart.total_items,
        'free_shipping_threshold': float(FREE_SHIPPING_FROM),
        'remaining_for_free_shipping': float(totals.remaining_for_free_shipping),
    })


def _order_lines(cart_items):
    """שורות ההזמנה כפי שהן בעגלה כרגע: (product_id, variant_id, quantity, price)."""
    lines = []
    for cart_item in cart_items:
        price = cart_item.variant.effective_price if cart_item.variant else cart_item.product.price
        lines.append((cart_item.product_id, cart_item.variant_id, cart_item.quantity, price))
    return sorted(lines, key=lambda line: (line[0], line[1] or 0))


def _tracking_item(cart_item):
    price = cart_item.variant.effective_price if cart_item.variant else cart_item.product.price
    return {
        'id': cart_item.product_id,
        'name': product_full_name(cart_item.product),
        'price': float(price),
        'quantity': cart_item.quantity,
    }


def _find_reusable_order(request, lines, totals):
    """
    הזמנה ממתינה מאותו סשן עם אותם פריטים ואותו סכום (למשל שליחה כפולה של
    הטופס או חזרה מדף התשלום) - נשתמש בה שוב במקום ליצור הזמנה כפולה.
    """
    order_id = request.session.get('pending_order_id')
    if not order_id:
        return None
    order = Order.objects.filter(id=order_id, status='pending').first()
    if not order:
        return None
    if (
        order.total_price != totals.total
        or order.shipping_method != totals.shipping_method
        or order.shipping_fee != totals.shipping_fee
        or order.discount_amount != totals.discount
        or order.coupon_code != totals.coupon_code
    ):
        return None
    existing = sorted(
        ((item.product_id, item.variant_id, item.quantity, item.price) for item in order.items.all()),
        key=lambda line: (line[0], line[1] or 0),
    )
    return order if existing == lines else None


def _save_pending_order(request, form, cart_items, totals):
    """
    יצירת הזמנה ממתינה לתשלום (או עדכון פרטי הלקוח בהזמנה ממתינה זהה).
    המלאי לא יורד כאן - רק אחרי שהתשלום אושר.
    """
    data = form.cleaned_data
    is_pickup = totals.shipping_method == SHIPPING_PICKUP
    lines = _order_lines(cart_items)

    fields = {
        'user': request.user if request.user.is_authenticated else None,
        'guest_name': f"{data['first_name']} {data['last_name']}",
        'guest_phone': data['guest_phone'],
        'guest_email': data['guest_email'],
        'guest_address': '' if is_pickup else data['guest_address'],
        'guest_city': '' if is_pickup else data['guest_city'],
        'notes': data['notes'],
    }

    with transaction.atomic():
        order = _find_reusable_order(request, lines, totals)
        if order:
            for name, value in fields.items():
                setattr(order, name, value)
            order.save()
            return order

        source = request.session.get('campaign_source') or {}
        order = Order.objects.create(
            utm_source=source.get('utm_source', ''),
            utm_medium=source.get('utm_medium', ''),
            utm_campaign=source.get('utm_campaign', ''),
            total_price=totals.total,
            coupon_code=totals.coupon_code,
            discount_amount=totals.discount,
            shipping_method=totals.shipping_method,
            shipping_fee=totals.shipping_fee,
            status='pending',
            **fields,
        )
        OrderItem.objects.bulk_create([
            OrderItem(order=order, product_id=product_id, variant_id=variant_id, quantity=quantity, price=price)
            for product_id, variant_id, quantity, price in lines
        ])
    return order


def _out_of_stock_product(cart_items):
    """המוצר הראשון שהכמות המבוקשת שלו (בכל המידות יחד) גדולה מהמלאי, אם יש."""
    requested = defaultdict(int)
    products = {}
    for cart_item in cart_items:
        requested[cart_item.product_id] += cart_item.quantity
        products[cart_item.product_id] = cart_item.product
    for product_id, quantity in requested.items():
        product = products[product_id]
        product.refresh_from_db(fields=['stock_quantity', 'is_active'])
        if not product.is_active or product.stock_quantity < quantity:
            return product
    return None


def checkout(request):
    """
    עמוד ביצוע הזמנה
    """
    # חסימה במצב דמו
    if request.session.get('demo_mode'):
        messages.info(request, 'זהו אתר דמו — רכישות אינן זמינות')
        return redirect('cart')

    cart = get_or_create_cart(request)
    cart_items = _cart_items(cart)

    if not cart_items.exists():
        messages.warning(request, 'העגלה שלך ריקה')
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        shipping_method = _clean_shipping_method(request.POST.get('shipping_method'))
        totals = get_cart_totals(request, cart, shipping_method)

        if form.is_valid():
            unavailable = _out_of_stock_product(cart_items)
            if unavailable:
                messages.error(request, f'המוצר "{unavailable.name}" אזל מהמלאי או שהכמות המבוקשת גדולה מהמלאי הזמין')
                return redirect('cart')

            order = _save_pending_order(request, form, cart_items, totals)
            request.session['pending_order_id'] = order.id
            logger.info('Checkout: order %s pending payment, total %s', order.id, order.total_price)

            # הפניה לדף התשלום. העגלה תנוקה רק אחרי תשלום מוצלח
            return redirect('initiate_payment', order_id=order.id)

        messages.error(request, 'אנא תקן את השגיאות בטופס')
    else:
        # אם משתמש מחובר, מלא את הפרטים מראש
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name or request.user.username,
                'last_name': request.user.last_name or '',
                'guest_email': request.user.email,
            }
        form = CheckoutForm(initial=initial_data)
        totals = get_cart_totals(request, cart, SHIPPING_DELIVERY)

    context = {
        # נתוני העגלה לפיקסלים (אירוע "כניסה לקופה")
        'tracking_checkout': {
            'value': float(totals.subtotal - totals.discount),
            'items': [_tracking_item(cart_item) for cart_item in cart_items],
        },
        'form': form,
        'cart': cart,
        'cart_items': cart_items,
        'totals': totals,
        'totals_json': totals.as_json(),
        'subtotal': totals.subtotal,
        'shipping_fee': totals.shipping_fee,
        'discount_amount': totals.discount,
        'coupon_code': totals.coupon_code,
        'applied_coupon': totals.coupon.is_valid,
        'total': totals.total,
        'shipping_method': totals.shipping_method,
        'pickup_address': PICKUP_ADDRESS,
        'categories': Category.objects.filter(is_active=True),
    }

    return render(request, 'store/checkout.html', context)


def _json_body(request):
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def apply_coupon(request):
    """
    API endpoint לאימות והחלת קופון
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'שיטה לא חוקית'}, status=405)

    if is_rate_limited(request, 'coupon', limit=15, window=10 * 60):
        return JsonResponse({'success': False, 'message': 'יותר מדי ניסיונות. נסו שוב בעוד כמה דקות'}, status=429)

    data = _json_body(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'נתונים לא חוקיים'}, status=400)

    coupon_code = str(data.get('coupon_code', '')).strip().upper()
    if not coupon_code:
        return JsonResponse({'success': False, 'message': 'נא להזין קוד קופון'})

    cart = get_or_create_cart(request)
    if cart.total_price <= 0:
        return JsonResponse({'success': False, 'message': 'העגלה ריקה'})

    coupon = evaluate_coupon(coupon_code, cart.total_price)
    if not coupon.is_valid:
        return JsonResponse({'success': False, 'message': coupon.error})

    request.session['applied_coupon'] = {
        'code': coupon.code,
        'type': coupon.coupon_type,
        'discount_amount': float(coupon.discount),
        'discount_percent': coupon.percent,
    }

    shipping_method = _clean_shipping_method(data.get('shipping_method'))
    totals = calculate_totals(cart.total_price, coupon.code, shipping_method)

    response = totals.as_json()
    response.update({
        'success': True,
        'message': 'הקופון הוחל בהצלחה!',
        'original_total': float(totals.subtotal),
        'new_total': float(totals.total),
    })
    return JsonResponse(response)


def remove_coupon(request):
    """
    API endpoint להסרת קופון
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'שיטה לא חוקית'}, status=405)

    request.session.pop('applied_coupon', None)

    data = _json_body(request) or {}
    cart = get_or_create_cart(request)
    totals = calculate_totals(cart.total_price, '', _clean_shipping_method(data.get('shipping_method')))

    response = totals.as_json()
    response.update({'success': True, 'message': 'הקופון הוסר'})
    return JsonResponse(response)
