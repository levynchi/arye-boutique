from django.shortcuts import redirect
from django.urls import reverse

from .models import SiteSettings


class ComingSoonMiddleware:
    """
    Middleware שמציג עמוד "בקרוב" לכל המשתמשים שאינם סופר-אדמין.
    מחריג את פאנל הניהול ודף ההתחברות.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # בדיקה אם דף Coming Soon מופעל
        site_settings = SiteSettings.get_settings()
        if not site_settings or not site_settings.coming_soon_enabled:
            return self.get_response(request)  # האתר פעיל, אין הפניה
        
        # נתיבים שתמיד מותרים (גם למשתמשים לא מחוברים)
        allowed_prefixes = [
            '/admin',  # פאנל הניהול (כולל /admin ו-/admin/)
            '/users/login',
            '/coming-soon',
            '/newsletter/unsubscribe',  # ביטול הרשמה לניוזלטר
        ]
        
        # בדיקה אם הנתיב מותר
        path = request.path
        
        # אפשר גישה לקבצים סטטיים ומדיה
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)
        
        # אפשר גישה לנתיבים המותרים
        for allowed_prefix in allowed_prefixes:
            if path.startswith(allowed_prefix):
                return self.get_response(request)
        
        # אם המשתמש הוא סופר-אדמין - אפשר גישה מלאה
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)
        
        # כל השאר - הפניה לעמוד "בקרוב"
        return redirect('coming_soon')


