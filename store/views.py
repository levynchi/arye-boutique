from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from decimal import Decimal
from .models import Product, Category, Subcategory, SiteSettings, ProductImage, Cart, CartItem, ContactMessage, WishlistItem, Order, OrderItem
from .forms import ContactForm, CheckoutForm


def home(request):
    """
    עמוד הבית
    """
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    
    # Fetch specific categories in the desired order
    category_names = [
        'חיתולי בד / טטרה',
        'לחדר השינה',
        'מגבות לתינוק',
        'סינרי פליטה לתינוק'
    ]
    
    # Get categories by name, preserving order
    categories = []
    for name in category_names:
        try:
            category = Category.objects.get(name=name, is_active=True)
            categories.append(category)
        except Category.DoesNotExist:
            continue
    
    # If specific categories don't exist, fallback to all active categories
    if not categories:
        categories = list(Category.objects.filter(is_active=True)[:4])
    
    site_settings = SiteSettings.get_settings()
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'site_settings': site_settings,
    }
    
    return render(request, 'store/home.html', context)


def product_detail(request, slug):
    """
    עמוד מוצר בודד
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # קבלת כל התמונות הנלוות של המוצר
    additional_images = product.images.all()
    
    # קביעת תמונה ראשית - אם יש תמונה עם is_primary=True, נשתמש בה
    # אחרת, נשתמש בתמונה הראשית מהשדה image של המוצר
    primary_product_image = additional_images.filter(is_primary=True).first()
    if primary_product_image:
        primary_image = primary_product_image.image
    else:
        # אם אין תמונה ראשית במודל ProductImage, נשתמש בתמונה הראשית של המוצר
        primary_image = product.image
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'product': product,
        'primary_image': primary_image,
        'additional_images': additional_images,
        'categories': categories,
    }
    
    return render(request, 'store/product_detail.html', context)


def add_to_cart(request, product_id):
    """
    הוספת מוצר לסל הקניות
    """
    if request.method != 'POST':
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # קבלת הכמות מהטופס
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        messages.error(request, 'הכמות חייבת להיות לפחות 1')
        return redirect('product_detail', slug=product.slug)
    
    # בדיקה אם המוצר במלאי
    if quantity > product.stock_quantity:
        messages.error(request, f'הכמות המבוקשת גדולה מהמלאי הזמין ({product.stock_quantity})')
        return redirect('product_detail', slug=product.slug)
    
    # קבלת או יצירת סל קניות
    cart = get_or_create_cart(request)
    
    # הוספה או עדכון פריט בסל
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not item_created:
        # הפריט כבר קיים בסל - עדכון הכמות
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            messages.error(request, f'הכמות הכוללת גדולה מהמלאי הזמין ({product.stock_quantity})')
            return redirect('product_detail', slug=product.slug)
        cart_item.quantity = new_quantity
        cart_item.save()
    
    messages.success(request, f'המוצר "{product.name}" נוסף לסל בהצלחה!')
    return redirect('product_detail', slug=product.slug)


def category_detail(request, slug):
    """
    עמוד קטגוריה - הצגת מוצרים לפי קטגוריה עם סינון
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # קבלת מוצרים פעילים של הקטגוריה + כל תת-קטגוריות
    # אם יש תת-קטגוריות, נכלול גם את המוצרים שלהם
    subcategories = category.subcategories.filter(is_active=True)
    if subcategories.exists():
        # יש תת-קטגוריות - נציג את המוצרים מהקטגוריה הראשית + כל התת-קטגוריות
        products = Product.objects.filter(
            Q(category=category) | Q(subcategory__in=subcategories),
            is_active=True
        )
    else:
        # אין תת-קטגוריות - רק מוצרים מהקטגוריה עצמה
        products = Product.objects.filter(category=category, is_active=True)
    
    # סינון לפי מין
    gender_filter = request.GET.get('gender', '')
    if gender_filter:
        if gender_filter == 'both':
            # אם "שניהם", נציג את כל המוצרים
            pass
        else:
            # סינון לפי מין ספציפי
            products = products.filter(gender__in=[gender_filter, 'both'])
    
    # מיון לפי מחיר
    price_sort = request.GET.get('price', '')
    if price_sort == 'low_to_high':
        products = products.order_by('price')
    elif price_sort == 'high_to_low':
        products = products.order_by('-price')
    else:
        # ברירת מחדל - לפי תאריך יצירה
        products = products.order_by('-created_at')
    
    # קבלת מוצרים ב-wishlist של המשתמש (אם מחובר)
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'category': category,
        'products': products,
        'current_gender': gender_filter,
        'current_price_sort': price_sort,
        'categories': categories,
        'wishlist_product_ids': wishlist_product_ids,
    }
    
    return render(request, 'store/category_detail.html', context)


def contact(request):
    """
    דף צור קשר
    """
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            messages.success(request, 'הודעתך נשלחה בהצלחה! נחזור אליך תוך 2 ימי עסקים.')
            return redirect('contact')
        else:
            messages.error(request, 'אירעה שגיאה במילוי הטופס. אנא בדוק את השדות ומלא מחדש.')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
        'categories': categories,
    }
    
    return render(request, 'store/contact.html', context)


@login_required
def wishlist_view(request):
    """
    דף רשימת המשאלות - הצגת כל המוצרים המועדפים
    """
    # קבלת פריטי Wishlist של המשתמש
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product')
    products = [item.product for item in wishlist_items]
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'products': products,
        'wishlist_items': wishlist_items,
        'categories': categories,
    }
    
    return render(request, 'store/wishlist.html', context)


@login_required
def wishlist_toggle(request, product_id):
    """
    Toggle מוצר ב-Wishlist (הוספה/הסרה) - AJAX
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # בדיקה אם המוצר כבר ב-Wishlist
    wishlist_item = WishlistItem.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        # המוצר כבר קיים - נסיר אותו
        wishlist_item.delete()
        return JsonResponse({
            'success': True,
            'action': 'removed',
            'message': f'המוצר "{product.name}" הוסר מרשימת המשאלות'
        })
    else:
        # המוצר לא קיים - נוסיף אותו
        WishlistItem.objects.create(user=request.user, product=product)
        return JsonResponse({
            'success': True,
            'action': 'added',
            'message': f'המוצר "{product.name}" נוסף לרשימת המשאלות'
        })


@login_required
def wishlist_remove(request, product_id):
    """
    הסרת מוצר מ-Wishlist - AJAX
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    product = get_object_or_404(Product, id=product_id)
    
    # הסרת המוצר מ-Wishlist
    deleted_count, _ = WishlistItem.objects.filter(user=request.user, product=product).delete()
    
    if deleted_count > 0:
        return JsonResponse({
            'success': True,
            'message': f'המוצר "{product.name}" הוסר מרשימת המשאלות'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'המוצר לא נמצא ברשימת המשאלות'
        }, status=404)


def get_or_create_cart(request):
    """
    פונקציית עזר לקבלת או יצירת עגלת קניות
    """
    cart = None
    if request.user.is_authenticated:
        # משתמש מחובר - חיפוש או יצירת סל לפי משתמש
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'session_key': ''}
        )
    else:
        # משתמש לא מחובר - חיפוש או יצירת סל לפי session_key
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        try:
            cart = Cart.objects.get(session_key=session_key, user__isnull=True)
        except Cart.DoesNotExist:
            cart = Cart.objects.create(session_key=session_key, user=None)
    
    return cart


def cart_view(request):
    """
    עמוד עגלת הקניות
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    
    # חישוב סיכומים
    subtotal = cart.total_price
    shipping_fee = Decimal('0.00')
    
    # משלוח חינם מעל 75 ש"ח, אחרת 0 (או תעריף שתרצה)
    if subtotal > 0 and subtotal < 75:
        shipping_fee = Decimal('0.00')  # אפשר לשנות לתעריף משלוח
    
    total = subtotal + shipping_fee
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': total,
        'categories': categories,
    }
    
    return render(request, 'store/cart.html', context)


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
    
    # עדכון הכמות
    cart_item.quantity = new_quantity
    cart_item.save()
    
    # חישוב סיכומים מחדש
    cart = get_or_create_cart(request)
    subtotal = cart.total_price
    shipping_fee = Decimal('0.00')
    if subtotal > 0 and subtotal < 75:
        shipping_fee = Decimal('0.00')
    total = subtotal + shipping_fee
    
    return JsonResponse({
        'success': True,
        'item_subtotal': float(cart_item.subtotal),
        'cart_subtotal': float(subtotal),
        'shipping_fee': float(shipping_fee),
        'cart_total': float(total),
        'total_items': cart.total_items,
    })


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
    
    # חישוב סיכומים מחדש
    cart = get_or_create_cart(request)
    subtotal = cart.total_price
    shipping_fee = Decimal('0.00')
    if subtotal > 0 and subtotal < 75:
        shipping_fee = Decimal('0.00')
    total = subtotal + shipping_fee
    
    return JsonResponse({
        'success': True,
        'message': f'המוצר "{product_name}" הוסר מהעגלה',
        'cart_subtotal': float(subtotal),
        'shipping_fee': float(shipping_fee),
        'cart_total': float(total),
        'total_items': cart.total_items,
    })


def checkout(request):
    """
    עמוד ביצוע הזמנה
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    
    # בדיקה שהעגלה לא ריקה
    if not cart_items.exists():
        messages.warning(request, 'העגלה שלך ריקה')
        return redirect('cart')
    
    # חישוב סיכומים
    subtotal = cart.total_price
    shipping_fee = Decimal('0.00')
    if subtotal > 0 and subtotal < 75:
        shipping_fee = Decimal('0.00')
    total = subtotal + shipping_fee
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # יצירת הזמנה
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                guest_name=form.cleaned_data['guest_name'],
                guest_phone=form.cleaned_data['guest_phone'],
                guest_email=form.cleaned_data['guest_email'],
                guest_address=form.cleaned_data['guest_address'],
                guest_city=form.cleaned_data['guest_city'],
                notes=form.cleaned_data['notes'],
                total_price=total,
                status='pending'
            )
            
            # יצירת פריטי הזמנה
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                
                # עדכון מלאי
                product = cart_item.product
                product.stock_quantity -= cart_item.quantity
                product.save()
            
            # ניקוי העגלה
            cart_items.delete()
            
            messages.success(
                request, 
                f'ההזמנה שלך התקבלה בהצלחה! מספר הזמנה: {order.id}. נחזור אליך בהקדם.'
            )
            return redirect('home')
        else:
            messages.error(request, 'אנא תקן את השגיאות בטופס')
    else:
        # אם משתמש מחובר, מלא את הפרטים מראש
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'guest_name': request.user.get_full_name() or request.user.username,
                'guest_email': request.user.email,
            }
        form = CheckoutForm(initial=initial_data)
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'form': form,
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': total,
        'categories': categories,
    }
    
    return render(request, 'store/checkout.html', context)
