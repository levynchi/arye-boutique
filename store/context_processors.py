from .models import Cart


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


