from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    ניהול משתמשים בפאנל הניהול
    """
    list_display = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'city', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'city']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    
    fieldsets = UserAdmin.fieldsets + (
        ('מידע נוסף', {'fields': ('phone_number', 'address', 'city')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('מידע נוסף', {'fields': ('phone_number', 'address', 'city')}),
    )
