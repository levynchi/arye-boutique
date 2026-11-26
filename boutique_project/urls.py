"""
URL configuration for boutique_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

from store.ratelimit import is_rate_limited
from store.sitemaps import sitemaps


def _rate_limited_admin_login(view):
    def wrapped(request, *args, **kwargs):
        if request.method == 'POST':
            limited = is_rate_limited(request, 'admin-login-ip', limit=20, window=15 * 60)
            username = request.POST.get('username', '')
            if username:
                limited = is_rate_limited(
                    request, 'admin-login-user', limit=10, window=15 * 60, identity=username
                ) or limited
            if limited:
                return HttpResponse(
                    'יותר מדי ניסיונות התחברות. נסו שוב בעוד כמה דקות.',
                    status=429, content_type='text/plain; charset=utf-8',
                )
        return view(request, *args, **kwargs)
    return wrapped


admin.site.login = _rate_limited_admin_login(admin.site.login)

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('store.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
