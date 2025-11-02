from django.contrib import admin
from .models import SiteSettings, Category, Product, ProductImage, Order, OrderItem, Cart, CartItem


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    ניהול הגדרות האתר והבאנר הראשי
    """
    list_display = ['site_name', 'is_active', 'has_banner']
    list_editable = ['is_active']
    
    fieldsets = (
        ('מידע כללי', {
            'fields': ('site_name', 'is_active')
        }),
        ('באנר ראשי', {
            'fields': ('hero_banner', 'hero_title', 'hero_subtitle')
        }),
    )
    
    def has_banner(self, obj):
        """האם יש תמונת באנר"""
        return bool(obj.hero_banner)
    has_banner.short_description = 'יש באנר'
    has_banner.boolean = True
    
    def has_add_permission(self, request):
        """מגביל יצירה - רק אם אין כרטיס קיים"""
        return not SiteSettings.objects.exists()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    ניהול קטגוריות
    """
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']


class OrderItemInline(admin.TabularInline):
    """
    הצגת פריטי הזמנה בתוך ההזמנה
    """
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


class ProductImageInline(admin.TabularInline):
    """
    הצגת תמונות נוספות בתוך המוצר
    """
    model = ProductImage
    extra = 1
    fields = ('image', 'is_primary', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    ניהול מוצרים
    """
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock_quantity', 'is_active', 'is_featured']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('מידע בסיסי', {
            'fields': ('name', 'slug', 'category', 'description', 'size')
        }),
        ('מחיר ומלאי', {
            'fields': ('price', 'stock_quantity')
        }),
        ('תמונה ראשית', {
            'fields': ('image',)
        }),
        ('הגדרות', {
            'fields': ('is_active', 'is_featured')
        }),
        ('תאריכים', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    ניהול הזמנות
    """
    list_display = ['id', 'get_customer_name', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'user__username', 'guest_name', 'guest_email', 'guest_phone']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('מידע הזמנה', {
            'fields': ('user', 'total_price', 'status', 'notes')
        }),
        ('מידע אורח', {
            'fields': ('guest_name', 'guest_email', 'guest_phone', 'guest_address', 'guest_city'),
            'classes': ('collapse',)
        }),
        ('תאריכים', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        """החזרת שם הלקוח"""
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return obj.guest_name or obj.guest_email
    get_customer_name.short_description = 'לקוח'


class CartItemInline(admin.TabularInline):
    """
    הצגת פריטי סל בתוך הסל
    """
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    ניהול סלי קניות
    """
    list_display = ['id', 'get_owner', 'total_items', 'total_price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at', 'updated_at', 'total_price', 'total_items']
    inlines = [CartItemInline]
    
    def get_owner(self, obj):
        """החזרת בעלים של הסל"""
        if obj.user:
            return obj.user.username
        return f'אורח ({obj.session_key[:10]}...)'
    get_owner.short_description = 'בעלים'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    ניהול פריטי הזמנה
    """
    list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['product__name', 'order__id']
    readonly_fields = ['subtotal']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    ניהול פריטי סל
    """
    list_display = ['cart', 'product', 'quantity', 'subtotal', 'added_at']
    list_filter = ['added_at']
    search_fields = ['product__name', 'cart__user__username']
    readonly_fields = ['subtotal', 'added_at']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    ניהול תמונות מוצרים
    """
    list_display = ['product', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name']
    list_editable = ['is_primary', 'order']
