from django.conf import settings

from .models import Cart, Category, WishlistItem


def seo_and_tracking(request):
    """
    כתובת קנונית לכל עמוד ומזהי המדידה (GA4, מטא, טיקטוק).
    במצב דמו המזהים ריקים, כדי שגלישת הדגמה לא תיספר כתנועה אמיתית.
    """
    tracking_ids = {}
    if not request.session.get('demo_mode'):
        tracking_ids = {
            name: value for name, value in (
                ('ga4', settings.GA4_MEASUREMENT_ID),
                ('meta', settings.META_PIXEL_ID),
                ('tiktok', settings.TIKTOK_PIXEL_ID),
            ) if value
        }
    return {
        'SITE_URL': settings.SITE_URL,
        'canonical_url': settings.SITE_URL + request.path,
        'tracking_ids': tracking_ids,
        'google_site_verification': settings.GOOGLE_SITE_VERIFICATION,
        'meta_domain_verification': settings.META_DOMAIN_VERIFICATION,
    }


def nav_categories(request):
    """
    קטגוריות לתפריט הניווט - ברירת מחדל לדפים שלא מעבירים categories בעצמם
    (למשל דף 404). ה-queryset עצל: אם ה-view מעביר categories משלו, אין שאילתה נוספת.
    """
    return {
        'categories': Category.objects.filter(is_active=True)
    }


def demo_mode(request):
    """
    Context processor להוספת מצב דמו לכל template
    """
    return {
        'demo_mode': request.session.get('demo_mode', False)
    }


def cart_items_count(request):
    """
    Context processor להוספת מספר הפריטים בעגלה לכל template
    """
    cart_count = 0
    
    try:
        if request.user.is_authenticated:
            # משתמש מחובר - חיפוש סל לפי משתמש
            cart = Cart.objects.filter(user=request.user).first()
        else:
            # משתמש לא מחובר - חיפוש סל לפי session_key
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
            else:
                cart = None
        
        if cart:
            cart_count = cart.total_items
    except:
        # במקרה של שגיאה, נחזיר 0
        pass
    
    return {
        'cart_count': cart_count
    }


def wishlist_count(request):
    """
    Context processor להוספת מספר הפריטים ברשימת המשאלות לכל template
    """
    count = 0
    
    try:
        if request.user.is_authenticated:
            count = WishlistItem.objects.filter(user=request.user).count()
    except:
        pass
    
    return {
        'wishlist_count': count
    }
