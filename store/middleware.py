from django.shortcuts import redirect
from django.urls import reverse


class ComingSoonMiddleware:
    """
    Middleware שמציג עמוד "בקרוב" לכל המשתמשים שאינם סופר-אדמין.
    מחריג את פאנל הניהול ודף ההתחברות.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # נתיבים שתמיד מותרים (גם למשתמשים לא מחוברים)
        allowed_paths = [
            '/admin/',
            '/users/login/',
            '/coming-soon/',
        ]
        
        # בדיקה אם הנתיב מותר
        path = request.path
        
        # אפשר גישה לקבצים סטטיים ומדיה
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)
        
        # אפשר גישה לנתיבים המותרים
        for allowed_path in allowed_paths:
            if path.startswith(allowed_path):
                return self.get_response(request)
        
        # אם המשתמש הוא סופר-אדמין - אפשר גישה מלאה
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)
        
        # כל השאר - הפניה לעמוד "בקרוב"
        return redirect('coming_soon')

