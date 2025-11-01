from django.shortcuts import render
from .models import Product, Category, SiteSettings


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
