from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
from decimal import Decimal
import json
import resend
from .models import (
    Product, Category, Subcategory, SiteSettings, ProductImage, 
    Cart, CartItem, ContactMessage, WishlistItem, Order, OrderItem, 
    BelowBestsellersGallery, RetailerStore, InstagramGallery,
    FabricType, ProductVariant, AboutPageSettings, FAQ, BlogPost,
    NewsletterSubscriber
)
import string
import random
from .forms import ContactForm, CheckoutForm


def coming_soon(request):
    """
    עמוד "בקרוב" - מוצג למשתמשים שאינם סופר-אדמין
    """
    return render(request, 'store/coming_soon.html')


def home(request):
    """
    עמוד הבית
    """
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    
    # Fetch bestseller products (limited to 4)
    bestseller_products = Product.objects.filter(is_active=True, is_bestseller=True)[:4]
    
    # Fetch all active categories for navigation and gallery
    categories = Category.objects.filter(is_active=True)
    
    site_settings = SiteSettings.get_settings()
    
    # Get gallery below bestsellers
    below_bestsellers_gallery = BelowBestsellersGallery.get_gallery()
    
    # Get retailer stores (active only, ordered)
    retailer_stores = RetailerStore.objects.filter(is_active=True).order_by('order', 'name')
    
    # Get Instagram gallery
    instagram_gallery = InstagramGallery.get_gallery()
    
    # Get wishlist product IDs for logged-in users
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    context = {
        'featured_products': featured_products,
        'bestseller_products': bestseller_products,
        'categories': categories,
        'site_settings': site_settings,
        'below_bestsellers_gallery': below_bestsellers_gallery,
        'retailer_stores': retailer_stores,
        'instagram_gallery': instagram_gallery,
        'wishlist_product_ids': wishlist_product_ids,
    }
    
    return render(request, 'store/home.html', context)


def product_detail(request, slug):
    """
    עמוד מוצר בודד
    """
    product = get_object_or_404(
        Product.objects.select_related('material_care_info'),
        slug=slug,
        is_active=True
    )
    
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
    
    # קבלת סוגי בד זמינים דרך הוריאנטים של המוצר
    fabric_types = FabricType.objects.filter(
        variants__product=product,
        variants__is_available=True,
        is_active=True
    ).distinct().order_by('order', 'name')
    
    # בניית מבנה נתונים לוריאנטים - לכל בד, רשימת המידות הזמינות
    variants_data = {}
    for fabric in fabric_types:
        variants_data[fabric.id] = {
            'name': fabric.name,
            'order': fabric.order,
            'sizes': []
        }
    
    # קבלת כל הוריאנטים
    all_variants = product.variants.select_related('fabric_type', 'size').filter(is_available=True)
    for variant in all_variants:
        if variant.fabric_type_id in variants_data:
            variants_data[variant.fabric_type_id]['sizes'].append({
                'id': variant.id,
                'size': str(variant.size),  # המרה למחרוזת עבור JSON
                'warehouse_location': variant.warehouse_location
            })
    
    # המרה ל-JSON עבור JavaScript
    variants_json = json.dumps(variants_data)
    
    # האם למוצר יש וריאנטים
    has_variants = fabric_types.exists()
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'product': product,
        'primary_image': primary_image,
        'additional_images': additional_images,
        'fabric_types': fabric_types,
        'variants_json': variants_json,
        'has_variants': has_variants,
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
    
    # קבלת וריאנט אם יש
    variant_id = request.POST.get('variant_id')
    variant = None
    
    if variant_id:
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, 
                product=product,
                is_available=True
            )
        except ProductVariant.DoesNotExist:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            error_msg = 'הוריאנט שנבחר אינו זמין'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('product_detail', slug=product.slug)
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if quantity < 1:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'הכמות חייבת להיות לפחות 1'})
        messages.error(request, 'הכמות חייבת להיות לפחות 1')
        return redirect('product_detail', slug=product.slug)
    
    # בדיקה אם המוצר במלאי
    if quantity > product.stock_quantity:
        error_msg = f'הכמות המבוקשת גדולה מהמלאי הזמין ({product.stock_quantity})'
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('product_detail', slug=product.slug)
    
    # קבלת או יצירת סל קניות
    cart = get_or_create_cart(request)
    
    # הוספה או עדכון פריט בסל
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={'quantity': quantity}
    )
    
    if not item_created:
        # הפריט כבר קיים בסל - עדכון הכמות
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            error_msg = f'הכמות הכוללת גדולה מהמלאי הזמין ({product.stock_quantity})'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('product_detail', slug=product.slug)
        cart_item.quantity = new_quantity
        cart_item.save()
    
    # Success response
    success_msg = f'המוצר "{product.name}"'
    if variant:
        success_msg += f' ({variant.get_display_name()})'
    success_msg += ' נוסף לסל בהצלחה!'
    
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': success_msg,
            'cart_count': cart.total_items
        })
    
    messages.success(request, success_msg)
    return redirect('product_detail', slug=product.slug)


def category_detail(request, slug):
    """
    עמוד קטגוריה - הצגת תת-קטגוריות או מוצרים
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # קבלת תת-קטגוריות פעילות
    subcategories = category.subcategories.filter(is_active=True)
    has_subcategories = subcategories.exists()
    
    # אם יש תת-קטגוריות - להציג רק אותן (ללא מוצרים)
    if has_subcategories:
        # קבלת קטגוריות לניווט
        categories = Category.objects.filter(is_active=True)
        
        context = {
            'category': category,
            'subcategories': subcategories,
            'has_subcategories': True,
            'categories': categories,
        }
        
        return render(request, 'store/category_detail.html', context)
    
    # אין תת-קטגוריות - להציג מוצרים
    products = Product.objects.filter(category=category, is_active=True).prefetch_related('images')
    
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
        # ברירת מחדל - לפי סדר תצוגה ואז תאריך יצירה
        products = products.order_by('order', '-created_at')
    
    # קבלת מוצרים ב-wishlist של המשתמש (אם מחובר)
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'category': category,
        'products': products,
        'has_subcategories': False,
        'current_gender': gender_filter,
        'current_price_sort': price_sort,
        'categories': categories,
        'wishlist_product_ids': wishlist_product_ids,
    }
    
    return render(request, 'store/category_detail.html', context)


def subcategory_detail(request, category_slug, subcategory_slug):
    """
    עמוד תת-קטגוריה - הצגת מוצרים של תת-קטגוריה ספציפית
    """
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    subcategory = get_object_or_404(
        Subcategory, 
        slug=subcategory_slug, 
        category=category,
        is_active=True
    )
    
    # קבלת מוצרים של התת-קטגוריה
    products = Product.objects.filter(subcategory=subcategory, is_active=True).prefetch_related('images')
    
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
        # ברירת מחדל - לפי סדר תצוגה ואז תאריך יצירה
        products = products.order_by('order', '-created_at')
    
    # קבלת מוצרים ב-wishlist של המשתמש (אם מחובר)
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'category': category,
        'subcategory': subcategory,
        'products': products,
        'current_gender': gender_filter,
        'current_price_sort': price_sort,
        'categories': categories,
        'wishlist_product_ids': wishlist_product_ids,
    }
    
    return render(request, 'store/subcategory_detail.html', context)


def contact(request):
    """
    דף צור קשר
    """
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            
            # שליחת מייל לבעל האתר דרך Resend API
            try:
                resend.api_key = settings.RESEND_API_KEY
                
                html_content = f'''
                <div dir="rtl" style="font-family: Arial, sans-serif;">
                    <h2>פנייה חדשה מטופס צור קשר</h2>
                    <p><strong>שם:</strong> {contact_message.full_name}</p>
                    <p><strong>טלפון:</strong> <a href="tel:{contact_message.phone}">{contact_message.phone}</a></p>
                    <p><strong>אימייל:</strong> <a href="mailto:{contact_message.email}">{contact_message.email}</a></p>
                    <p><strong>מספר הזמנה:</strong> {contact_message.order_number or 'לא צוין'}</p>
                    <hr>
                    <p><strong>תוכן הפנייה:</strong></p>
                    <p>{contact_message.inquiry}</p>
                    <hr>
                    <p style="color: gray; font-size: 12px;">הודעה זו נשלחה אוטומטית מאתר Arye Boutique</p>
                </div>
                '''
                
                resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [settings.CONTACT_EMAIL],
                    "subject": f"פנייה חדשה מ-{contact_message.full_name}",
                    "html": html_content,
                    "reply_to": contact_message.email,
                })
            except Exception as e:
                # אם יש בעיה במייל, ההודעה עדיין נשמרת בDB
                print(f'Error sending contact email: {e}')
            
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


def about_us(request):
    """
    דף אודות
    """
    categories = Category.objects.filter(is_active=True)
    
    # קבלת הגדרות התמונות לדף אודות
    try:
        about_settings = AboutPageSettings.objects.filter(is_active=True).first()
    except AboutPageSettings.DoesNotExist:
        about_settings = None
    
    context = {
        'categories': categories,
        'about_settings': about_settings,
    }
    return render(request, 'store/about_us.html', context)


def accessibility_statement(request):
    """
    הצהרת נגישות ומידע אודות התאמות לבעלי מוגבלויות
    """
    categories = Category.objects.filter(is_active=True)

    context = {
        'categories': categories,
        'accessibility_officer_name': 'ליאור לוי',
        'accessibility_officer_phone': '052-8086466',
        'accessibility_officer_email': 'arye.boutique@gmail.com',
    }

    return render(request, 'store/accessibility.html', context)


def laundry_instructions(request):
    """
    דף הוראות כביסה
    """
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'store/laundry_instructions.html', context)


def terms_of_service(request):
    """
    דף תקנון האתר
    """
    categories = Category.objects.filter(is_active=True)
    context = {'categories': categories}
    return render(request, 'store/terms.html', context)


def faq(request):
    """
    דף שאלות ותשובות
    """
    categories = Category.objects.filter(is_active=True)
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'id')
    
    context = {
        'categories': categories,
        'faqs': faqs,
    }
    return render(request, 'store/faq.html', context)


def shipping_and_returns(request):
    """
    דף משלוחים והחזרות
    """
    categories = Category.objects.filter(is_active=True)
    context = {'categories': categories}
    return render(request, 'store/shipping.html', context)


@login_required
def wishlist_view(request):
    """
    דף רשימת המשאלות - הצגת כל המוצרים המועדפים
    """
    # קבלת פריטי Wishlist של המשתמש עם התמונות הנוספות
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    products = [item.product for item in wishlist_items]
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
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
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'action': 'removed',
            'message': f'המוצר "{product.name}" הוסר מרשימת המשאלות',
            'wishlist_count': wishlist_count
        })
    else:
        # המוצר לא קיים - נוסיף אותו
        WishlistItem.objects.create(user=request.user, product=product)
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'action': 'added',
            'message': f'המוצר "{product.name}" נוסף לרשימת המשאלות',
            'wishlist_count': wishlist_count
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
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'message': f'המוצר "{product.name}" הוסר מרשימת המשאלות',
            'wishlist_count': wishlist_count
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
    categories = Category.objects.filter(is_active=True)
    
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
                    variant=cart_item.variant,
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
    categories = Category.objects.filter(is_active=True)
    
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


def cart_data(request):
    """
    API endpoint להחזרת נתוני העגלה בפורמט JSON
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    
    # חישוב סיכומים
    subtotal = cart.total_price
    shipping_fee = Decimal('0.00')
    
    # משלוח חינם מעל 75 ש"ח
    if subtotal > 0 and subtotal < 75:
        shipping_fee = Decimal('0.00')
    
    total = subtotal + shipping_fee
    
    # הכנת נתוני הפריטים
    items_data = []
    for item in cart_items:
        variant_display = ''
        if item.variant:
            variant_display = item.variant.get_display_name()
        
        items_data.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'product_subtitle': item.product.subtitle or '',
            'product_image': item.product.image.url if item.product.image else '',
            'product_price': float(item.product.price),
            'product_size': item.product.size or '',
            'variant_display': variant_display,
            'quantity': item.quantity,
            'max_quantity': item.product.stock_quantity,
            'subtotal': float(item.subtotal),
        })
    
    return JsonResponse({
        'success': True,
        'items': items_data,
        'subtotal': float(subtotal),
        'shipping_fee': float(shipping_fee),
        'total': float(total),
        'total_items': cart.total_items,
        'free_shipping_threshold': 75,
        'remaining_for_free_shipping': float(max(0, 75 - subtotal)),
    })


def product_variants_api(request, product_id):
    """
    API endpoint לקבלת נתוני וריאנטים של מוצר
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # קבלת סוגי בד זמינים דרך הוריאנטים של המוצר
    fabric_types = FabricType.objects.filter(
        variants__product=product,
        variants__is_available=True,
        is_active=True
    ).distinct().order_by('order', 'name')
    
    # בניית מבנה נתונים לוריאנטים
    variants_data = {}
    for fabric in fabric_types:
        variants_data[fabric.id] = {
            'name': fabric.name,
            'order': fabric.order,
            'sizes': []
        }
    
    # קבלת כל הוריאנטים
    all_variants = product.variants.select_related('fabric_type', 'size').filter(is_available=True)
    for variant in all_variants:
        if variant.fabric_type_id in variants_data:
            variants_data[variant.fabric_type_id]['sizes'].append({
                'id': variant.id,
                'size': str(variant.size),
                'size_display': variant.size.display_name or variant.size.name,
            })
    
    # בניית רשימת סוגי בד עם המידות
    fabrics_list = []
    for fabric_id, fabric_data in variants_data.items():
        fabrics_list.append({
            'id': fabric_id,
            'name': fabric_data['name'],
            'sizes': fabric_data['sizes']
        })
    
    # האם למוצר יש וריאנטים
    has_variants = fabric_types.exists()
    
    # קבלת כל המידות הזמינות (ללא תלות בבד)
    all_sizes = []
    if has_variants:
        # אם יש בד אחד בלבד, נציג את המידות שלו
        if len(fabrics_list) == 1:
            all_sizes = fabrics_list[0]['sizes']
    
    return JsonResponse({
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'subtitle': product.subtitle or '',
            'price': float(product.price),
            'image': product.image.url if product.image else '',
            'stock_quantity': product.stock_quantity,
            'is_in_stock': product.is_in_stock,
        },
        'has_variants': has_variants,
        'fabrics': fabrics_list,
        'variants': variants_data,
    })


def search(request):
    """
    חיפוש מוצרים
    """
    query = request.GET.get('q', '').strip()
    products = []
    
    if query:
        # חיפוש לפי שם, תת-כותרת, תיאור
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(subtitle__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        ).prefetch_related('images').distinct()
    
    # קבלת מוצרים ב-wishlist של המשתמש (אם מחובר)
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    # קבלת קטגוריות לניווט
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'query': query,
        'products': products,
        'results_count': products.count() if query else 0,
        'categories': categories,
        'wishlist_product_ids': wishlist_product_ids,
    }
    
    return render(request, 'store/search_results.html', context)


def search_api(request):
    """
    API לחיפוש חי - מחזיר JSON עם תוצאות
    """
    query = request.GET.get('q', '').strip()
    
    # דרוש לפחות 2 תווים לחיפוש
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # חיפוש מוצרים לפי שם ותת-כותרת
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(subtitle__icontains=query),
        is_active=True
    )[:5]
    
    # בניית רשימת תוצאות
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'subtitle': product.subtitle or '',
            'price': float(product.price),
            'slug': product.slug,
            'image': product.image.url if product.image else '',
        })
    
    return JsonResponse({'results': results})


def blog_list(request):
    """
    דף רשימת כל הפוסטים בבלוג
    """
    posts = BlogPost.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'posts': posts,
        'categories': Category.objects.filter(is_active=True),
    }
    
    return render(request, 'store/blog_list.html', context)


def blog_detail(request, slug):
    """
    דף פוסט בודד בבלוג
    """
    post = get_object_or_404(BlogPost, slug=slug, is_active=True)
    
    # פוסטים קשורים (3 האחרונים, לא כולל הנוכחי)
    related_posts = BlogPost.objects.filter(is_active=True).exclude(id=post.id)[:3]
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'categories': Category.objects.filter(is_active=True),
    }
    
    return render(request, 'store/blog_detail.html', context)


def generate_coupon_code():
    """
    יצירת קוד קופון ייחודי בפורמט ARYE-XXXXX
    """
    while True:
        code = 'ARYE-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if not NewsletterSubscriber.objects.filter(coupon_code=code).exists():
            return code


def newsletter_subscribe(request):
    """
    הרשמה לניוזלטר - יוצר קוד קופון ייחודי ושולח למייל
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'שיטת בקשה לא חוקית'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
    except json.JSONDecodeError:
        email = request.POST.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'success': False, 'message': 'נא להזין כתובת אימייל'})
    
    # בדיקה אם המייל כבר רשום
    existing = NewsletterSubscriber.objects.filter(email=email).first()
    if existing:
        return JsonResponse({
            'success': False, 
            'already_exists': True,
            'message': 'כתובת האימייל הזו כבר רשומה במערכת'
        })
    
    # יצירת קוד קופון ייחודי וטוקן לביטול הרשמה
    coupon_code = generate_coupon_code()
    unsubscribe_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    # שמירה במסד הנתונים
    subscriber = NewsletterSubscriber.objects.create(
        email=email,
        coupon_code=coupon_code,
        discount_percent=10,
        unsubscribe_token=unsubscribe_token
    )
    
    # שליחת מייל עם קוד הקופון
    try:
        resend.api_key = settings.RESEND_API_KEY
        
        html_content = f'''
        <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #333; margin-bottom: 10px;">ברוכים הבאים למשפחת Arye Boutique! 🎉</h1>
            </div>
            
            <p style="font-size: 16px; color: #555; line-height: 1.8;">
                תודה שהצטרפת לניוזלטר שלנו! אנחנו שמחים שבחרת להיות חלק מהמשפחה.
            </p>
            
            <div style="background: linear-gradient(135deg, #7594b1, #5a7a99); color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 30px 0;">
                <p style="font-size: 14px; margin-bottom: 10px;">קוד ההנחה האישי שלך:</p>
                <h2 style="font-size: 32px; letter-spacing: 3px; margin: 10px 0;">{coupon_code}</h2>
                <p style="font-size: 18px; margin-top: 10px;">10% הנחה על הרכישה הראשונה!</p>
            </div>
            
            <p style="font-size: 14px; color: #555; text-align: center;">
                הזינו את הקוד בעגלת הקניות כדי לקבל את ההנחה. הקופון תקף לשימוש חד פעמי.
            </p>
            
            <p style="font-size: 14px; color: #555; text-align: center; margin-top: 25px;">
                נשמח לראות אותך באתר שלנו: <a href="https://arye-boutique.co.il" style="color: #7594b1;">www.arye-boutique.co.il</a>
            </p>
            
            <p style="font-size: 13px; color: #555; text-align: center; margin-top: 30px;">
                קיבלת מייל זה כי נרשמת לניוזלטר. לביטול ההרשמה <a href="https://arye-boutique.co.il/newsletter/unsubscribe/{unsubscribe_token}" style="color: #7594b1;">לחצו כאן</a>.
            </p>
        </div>
        '''
        
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email],
            "subject": "ברוכים הבאים! קוד הנחה 10% מחכה לך 🎁",
            "html": html_content,
        })
    except Exception as e:
        # אם יש בעיה במייל, ההרשמה עדיין נשמרת בDB
        print(f'Error sending newsletter email: {e}')
    
    return JsonResponse({
        'success': True,
        'message': 'תודה שהצטרפת למשפחה! מייל עם קוד קופון נשלח אליך'
    })


def newsletter_unsubscribe(request, token):
    """
    ביטול הרשמה לניוזלטר
    """
    from django.http import HttpResponse
    
    print(f'Newsletter unsubscribe called with token: {token}')
    
    try:
        subscriber = NewsletterSubscriber.objects.filter(unsubscribe_token=token).first()
        print(f'Found subscriber: {subscriber}')
        
        if subscriber:
            subscriber.is_active = False
            subscriber.save()
            print(f'Subscriber {subscriber.email} deactivated successfully')
            title = '✓ ההרשמה בוטלה בהצלחה'
            message = 'לא תקבל יותר מיילים מאיתנו. תודה!'
            color = '#4CAF50'
        else:
            print(f'No subscriber found with token: {token}')
            title = '✗ קישור לא תקין'
            message = 'הקישור לא תקין או שההרשמה כבר בוטלה.'
            color = '#f44336'
    except Exception as e:
        print(f'Error in newsletter_unsubscribe: {e}')
        title = '✗ שגיאה'
        message = 'אירעה שגיאה. נסה שוב מאוחר יותר.'
        color = '#f44336'
    
    html = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ביטול הרשמה - Arye Boutique</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 40px 20px; text-align: center;">
    <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h1 style="color: {color}; margin-bottom: 20px;">{title}</h1>
        <p style="color: #555; font-size: 16px;">{message}</p>
        <a href="https://arye-boutique.co.il" style="display: inline-block; margin-top: 20px; padding: 12px 30px; background-color: #7594b1; color: white; text-decoration: none; border-radius: 6px;">חזרה לאתר</a>
    </div>
</body>
</html>'''
    
    return HttpResponse(html, content_type='text/html; charset=utf-8')
