from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Product, Category, SiteSettings, ProductImage, Cart, CartItem


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
    
    context = {
        'product': product,
        'primary_image': primary_image,
        'additional_images': additional_images,
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
