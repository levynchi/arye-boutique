from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.html import format_html
from .models import (
    SiteSettings, Category, Subcategory, Product, ProductImage, 
    Order, OrderItem, Cart, CartItem, ContactMessage, WishlistItem, 
    BelowBestsellersGallery, RetailerStore, InstagramGallery, AboutPageSettings,
    GalleriesHub, Size, SizeGroup, FabricType, ProductVariant, FAQ, BlogPost, BlogSection,
    MaterialCareInfo, NewsletterSubscriber, Coupon
)
from .forms import BulkVariantCreationForm, ProductAdminForm


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    ניהול גלריה ראשית - הבאנר הראשי של דף הבית
    """
    list_display = ['site_name', 'is_active', 'has_banner']
    list_editable = ['is_active']
    
    def has_module_permission(self, request):
        """הסתר מרשימת Store - נגיש רק דרך GalleriesHub"""
        return False
    
    def response_add(self, request, obj, post_url_continue=None):
        """חזרה לגלריות אחרי הוספה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """חזרה לגלריות אחרי עריכה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            if '_continue' not in request.POST and '_addanother' not in request.POST and '_saveasnew' not in request.POST:
                return redirect('/admin/store/gallerieshub/')
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """חזרה לגלריות אחרי מחיקה"""
        if 'from_galleries_hub' in request.META.get('HTTP_REFERER', ''):
            return redirect('/admin/store/gallerieshub/')
        return super().response_delete(request, obj_display, obj_id)
    
    fieldsets = (
        ('מידע כללי', {
            'fields': ('site_name', 'is_active')
        }),
        ('באנר ראשי', {
            'fields': ('hero_banner', 'hero_title', 'hero_subtitle')
        }),
        ('הגדרות אתר', {
            'fields': ('coming_soon_enabled',),
            'description': 'הפעל כדי להציג דף Coming Soon לכל המבקרים (מלבד אדמין)'
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


@admin.register(BelowBestsellersGallery)
class BelowBestsellersGalleryAdmin(admin.ModelAdmin):
    """
    ניהול גלריה מתחת להכי נמכרים - 2 תמונות
    """
    list_display = ['__str__', 'is_active', 'has_images']
    list_editable = ['is_active']
    
    def has_module_permission(self, request):
        """הסתר מרשימת Store - נגיש רק דרך GalleriesHub"""
        return False
    
    def response_add(self, request, obj, post_url_continue=None):
        """חזרה לגלריות אחרי הוספה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """חזרה לגלריות אחרי עריכה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            if '_continue' not in request.POST and '_addanother' not in request.POST and '_saveasnew' not in request.POST:
                return redirect('/admin/store/gallerieshub/')
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """חזרה לגלריות אחרי מחיקה"""
        if 'from_galleries_hub' in request.META.get('HTTP_REFERER', ''):
            return redirect('/admin/store/gallerieshub/')
        return super().response_delete(request, obj_display, obj_id)
    
    fieldsets = (
        ('תמונות', {
            'fields': ('right_image', 'left_image')
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
    )
    
    def has_images(self, obj):
        """בדיקה אם יש תמונות"""
        return bool(obj.right_image and obj.left_image)
    has_images.short_description = 'יש תמונות'
    has_images.boolean = True
    
    def has_add_permission(self, request):
        """מגביל יצירה - רק אם אין רשומה קיימת"""
        return not BelowBestsellersGallery.objects.exists()


class SubcategoryInline(admin.TabularInline):
    """
    הצגת תת-קטגוריות בתוך הקטגוריה
    """
    model = Subcategory
    extra = 1
    fields = ('name', 'slug', 'is_active')


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
    readonly_fields = ['created_at']
    inlines = [SubcategoryInline]
    
    fieldsets = (
        ('מידע בסיסי', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
        ('תאריכים', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    """
    ניהול תת-קטגוריות
    """
    list_display = ['name', 'category', 'slug', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('מידע בסיסי', {
            'fields': ('name', 'slug', 'category', 'description', 'image')
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
        ('תאריכים', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """שיפור ביצועים - טעינה מראש של category"""
        return super().get_queryset(request).select_related('category')


class OrderItemInline(admin.TabularInline):
    """
    הצגת פריטי הזמנה בתוך ההזמנה
    """
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal', 'get_warehouse_location']
    fields = ['product', 'variant', 'quantity', 'price', 'subtotal', 'get_warehouse_location']
    
    def get_warehouse_location(self, obj):
        """הצגת מיקום תא במחסן למלקט"""
        if obj.variant and obj.variant.warehouse_location:
            return f'📦 {obj.variant.warehouse_location}'
        return '-'
    get_warehouse_location.short_description = 'מיקום במחסן'


class ProductImageInline(admin.TabularInline):
    """
    הצגת תמונות נוספות בתוך המוצר
    """
    model = ProductImage
    extra = 1
    fields = ('image', 'is_primary', 'order')


class ProductVariantInline(admin.TabularInline):
    """
    הצגת וריאנטים (בד + מידה) בתוך המוצר
    """
    model = ProductVariant
    extra = 0
    can_delete = True
    show_change_link = False
    fields = ('fabric_type', 'size', 'is_available', 'warehouse_location', 'price_override')
    ordering = ['size__order']
    
    # אפשר הוספת related objects (אייקון +)
    def has_add_permission(self, request, obj=None):
        return True
    
    def get_readonly_fields(self, request, obj=None):
        """
        הגדרת שדות לקריאה בלבד
        בווריאנטים קיימים - לא ניתן לשנות בד או מידה (ללא X ועיפרון)
        """
        return []
    
    def get_formset(self, request, obj=None, **kwargs):
        """
        התאמת formset - ווריאנטים קיימים לא יאפשרו עריכת בד ומידה
        ווריאנטים חדשים - יהיה אייקון + להוספת בד/מידה חדשה
        """
        # הסרת variant_display_name מה-fields שנשלחים ל-formset
        # כי זה readonly field בלבד
        kwargs.setdefault('fields', ('fabric_type', 'size', 'is_available', 'warehouse_location', 'price_override'))
        formset = super().get_formset(request, obj, **kwargs)
        original_form = formset.form
        
        class VariantFormReadonly(original_form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                # רק אם זה ווריאנט קיים ממש (יש instance עם pk)
                if self.instance and self.instance.pk:
                    # הפיכת הבד והמידה ל-readonly (אבל שומרים את האייקונים!)
                    self.fields['fabric_type'].disabled = True
                    self.fields['size'].disabled = True
                    # אייקון + ו-👁️ יישארו, אבל נסיר ✏️ ו-X
                    for field_name in ['fabric_type', 'size']:
                        field = self.fields[field_name]
                        if hasattr(field, 'widget') and hasattr(field.widget, 'can_add_related'):
                            field.widget.can_add_related = True  # ✅ שומרים את אייקון ה-+
                            field.widget.can_change_related = False  # ❌ מסירים עיפרון
                            field.widget.can_delete_related = False  # ❌ מסירים X
                            field.widget.can_view_related = True  # ✅ שומרים את העין
                # אם זה שורה חדשה - Django יוסיף את האייקונים אוטומטית
        
        formset.form = VariantFormReadonly
        return formset
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """סינון בדים ומידות פעילים בלבד"""
        if db_field.name == "fabric_type":
            kwargs["queryset"] = FabricType.objects.filter(is_active=True)
        elif db_field.name == "size":
            kwargs["queryset"] = Size.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    ניהול מוצרים
    """
    list_display = ['image_preview', 'name', 'category', 'subcategory', 'gender', 'price', 'stock_quantity', 'order', 'is_active', 'is_featured', 'is_bestseller', 'created_at']
    list_display_links = ['image_preview', 'name']
    
    def image_preview(self, obj):
        """תצוגה מקדימה של תמונת המוצר ברשימה"""
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'תמונה'
    list_filter = ['category', 'subcategory', 'is_active', 'is_featured', 'is_bestseller', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock_quantity', 'order', 'is_active', 'is_featured', 'is_bestseller']
    readonly_fields = ['created_at', 'updated_at', 'variant_creation_button']
    inlines = [ProductImageInline, ProductVariantInline]
    
    class Media:
        js = ('admin/js/product_variants.js',)
        css = {
            'all': ('admin/css/variant_display.css',)
        }
    
    fieldsets = (
        ('מידע בסיסי', {
            'fields': ('name', 'subtitle', 'slug', 'category', 'subcategory', 'description', 'gender'),
            'description': 'מידע כללי על המוצר'
        }),
        ('מחיר ומלאי', {
            'fields': ('price', 'stock_quantity'),
            'description': 'מחיר ומלאי כללי של המוצר (לא תלוי בוריאנט)'
        }),
        ('תמונה ראשית', {
            'fields': ('image',)
        }),
        ('הגדרות', {
            'fields': ('is_active', 'is_featured', 'is_bestseller', 'order', 'size_label'),
            'description': 'מספר נמוך יותר = יופיע קודם בתצוגה. תווית מידה: "מידה" לבגדים, "סוג" לסדינים'
        }),
        ('הרכב חומרים וטיפול', {
            'fields': ('material_care_info',),
            'description': 'בחר הרכב חומרים וטיפול להצגה בדף המוצר'
        }),
        ('יצירת וריאנטים', {
            'fields': ('variant_creation_button',),
            'description': 'צור וריאנטים למוצר בצורה אוטומטית'
        }),
        ('תאריכים', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def variant_creation_button(self, obj):
        """כפתור ליצירת וריאנטים - עובד גם בלי שמירה"""
        # בדיקה אם המוצר באמת נשמר במסד הנתונים
        if obj and obj.pk and not obj._state.adding:
            # אם המוצר כבר נשמר - קישור ישיר
            url = reverse('admin:create_product_variants', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="padding: 10px 15px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">➕ צור וריאנטים אוטומטית</a>',
                url
            )
        else:
            # אם זה מוצר חדש - כפתור שישמור ויעביר
            return format_html(
                '<button type="button" id="create-variants-btn" class="button" style="padding: 10px 15px; background-color: #417690; color: white; border: none; border-radius: 4px; cursor: pointer; display: inline-block;">➕ צור וריאנטים אוטומטית</button>'
                '<p style="color: #666; font-size: 12px; margin-top: 5px;">המוצר יישמר אוטומטית</p>'
            )
    variant_creation_button.short_description = 'יצירת וריאנטים'
    
    def response_add(self, request, obj, post_url_continue=None):
        """תגובה מותאמת לאחר הוספת מוצר"""
        if '_continue_to_variants' in request.POST:
            # הפניה לדף יצירת וריאנטים
            return redirect('admin:create_product_variants', product_id=obj.pk)
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """תגובה מותאמת לאחר עריכת מוצר"""
        if '_continue_to_variants' in request.POST:
            # הפניה לדף יצירת וריאנטים
            return redirect('admin:create_product_variants', product_id=obj.pk)
        return super().response_change(request, obj)
    
    def get_urls(self):
        """הוספת URL מותאם ליצירת וריאנטים"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:product_id>/create-variants/',
                self.admin_site.admin_view(self.create_variants_view),
                name='create_product_variants',
            ),
        ]
        return custom_urls + urls
    
    def create_variants_view(self, request, product_id):
        """View ליצירת וריאנטים אוטומטית"""
        product = get_object_or_404(Product, pk=product_id)
        
        if request.method == 'POST':
            form = BulkVariantCreationForm(request.POST)
            if form.is_valid():
                sizes_list = form.get_sizes_list()
                fabric_types = form.cleaned_data['fabric_types']
                
                created_count = 0
                skipped_count = 0
                
                # יצירת וריאנטים עבור כל שילוב של בד + מידה
                for fabric in fabric_types:
                    for size in sizes_list:
                        # בדיקה אם הוריאנט כבר קיים
                        variant, created = ProductVariant.objects.get_or_create(
                            product=product,
                            fabric_type=fabric,
                            size=size,
                            defaults={
                                'is_available': True,
                                'warehouse_location': ''
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            skipped_count += 1
                
                messages.success(
                    request,
                    f'נוצרו {created_count} וריאנטים חדשים. '
                    f'{skipped_count} וריאנטים כבר היו קיימים.'
                )
                
                # חזרה לעמוד עריכת המוצר
                return redirect('admin:store_product_change', product_id)
        else:
            form = BulkVariantCreationForm()
        
        context = {
            'form': form,
            'product': product,
            'title': f'יצירת וריאנטים - {product.name}',
            'site_title': 'ניהול אתר',
            'site_header': 'ניהול אתר',
            'has_permission': True,
        }
        
        return render(request, 'admin/store/create_variants.html', context)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    ניהול הזמנות
    """
    list_display = ['id', 'get_customer_name', 'total_price', 'get_discount_display', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'user__username', 'guest_name', 'guest_email', 'guest_phone', 'coupon_code']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'coupon_code', 'discount_amount']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('מידע הזמנה', {
            'fields': ('user', 'total_price', 'status', 'notes')
        }),
        ('קופון', {
            'fields': ('coupon_code', 'discount_amount'),
            'classes': ('collapse',)
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
    
    def get_discount_display(self, obj):
        """הצגת הנחה"""
        if obj.discount_amount and obj.discount_amount > 0:
            return format_html('<span style="color: #2e7d32;">-{}₪ ({})</span>', obj.discount_amount, obj.coupon_code)
        return '-'
    get_discount_display.short_description = 'הנחה'


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
    list_display = ['order', 'product', 'get_variant_display', 'quantity', 'price', 'get_warehouse_location', 'subtotal']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['product__name', 'order__id']
    readonly_fields = ['subtotal']
    
    def get_variant_display(self, obj):
        """הצגת פרטי הוריאנט"""
        if obj.variant:
            return obj.variant.get_display_name()
        return '-'
    get_variant_display.short_description = 'וריאנט'
    
    def get_warehouse_location(self, obj):
        """הצגת מיקום תא במחסן למלקט"""
        if obj.variant and obj.variant.warehouse_location:
            return f'📦 {obj.variant.warehouse_location}'
        return '-'
    get_warehouse_location.short_description = 'מיקום במחסן'


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


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """
    ניהול הודעות צור קשר
    """
    list_display = ['full_name', 'email', 'phone', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'order_number']
    list_editable = ['is_read']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('מידע אישי', {
            'fields': ('full_name', 'phone', 'email', 'order_number')
        }),
        ('הודעה', {
            'fields': ('inquiry',)
        }),
        ('סטטוס', {
            'fields': ('is_read', 'created_at')
        }),
    )


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    """
    ניהול פריטי רשימת משאלות
    """
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'user__email', 'product__name']
    readonly_fields = ['added_at']
    
    fieldsets = (
        ('מידע', {
            'fields': ('user', 'product', 'added_at')
        }),
    )


@admin.register(RetailerStore)
class RetailerStoreAdmin(admin.ModelAdmin):
    """
    ניהול חנויות משווקות - לוגואים
    """
    list_display = ['name', 'logo_preview', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'logo_preview_large']
    
    fieldsets = (
        ('פרטי החנות', {
            'fields': ('name', 'logo', 'logo_preview_large', 'website_url')
        }),
        ('הגדרות', {
            'fields': ('order', 'is_active', 'created_at')
        }),
    )
    
    def has_module_permission(self, request):
        """הסתר מרשימת Store - נגיש רק דרך GalleriesHub"""
        return False
    
    def response_add(self, request, obj, post_url_continue=None):
        """חזרה לגלריות אחרי הוספה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """חזרה לגלריות אחרי עריכה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_change(request, obj)
    
    def logo_preview(self, obj):
        """תצוגה מקדימה של הלוגו ברשימה"""
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 40px; max-width: 80px;" />', obj.logo.url)
        return '-'
    logo_preview.short_description = 'לוגו'
    
    def logo_preview_large(self, obj):
        """תצוגה מקדימה גדולה של הלוגו"""
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 200px;" />', obj.logo.url)
        return 'אין לוגו'
    logo_preview_large.short_description = 'תצוגה מקדימה'


@admin.register(InstagramGallery)
class InstagramGalleryAdmin(admin.ModelAdmin):
    """
    ניהול גלריית אינסטגרם - 4 תמונות וקישור
    """
    list_display = ['__str__', 'instagram_url', 'is_active', 'has_images']
    list_editable = ['is_active']
    
    def has_module_permission(self, request):
        """הסתר מרשימת Store - נגיש רק דרך GalleriesHub"""
        return False
    
    def response_add(self, request, obj, post_url_continue=None):
        """חזרה לגלריות אחרי הוספה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """חזרה לגלריות אחרי עריכה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            if '_continue' not in request.POST and '_addanother' not in request.POST and '_saveasnew' not in request.POST:
                return redirect('/admin/store/gallerieshub/')
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """חזרה לגלריות אחרי מחיקה"""
        if 'from_galleries_hub' in request.META.get('HTTP_REFERER', ''):
            return redirect('/admin/store/gallerieshub/')
        return super().response_delete(request, obj_display, obj_id)
    
    fieldsets = (
        ('תמונות', {
            'fields': ('image_1', 'image_2', 'image_3', 'image_4')
        }),
        ('קישור', {
            'fields': ('instagram_url',)
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
    )
    
    def has_images(self, obj):
        """בדיקה אם יש תמונות"""
        return bool(obj.image_1 and obj.image_2 and obj.image_3)
    has_images.short_description = 'יש תמונות'
    has_images.boolean = True
    
    def has_add_permission(self, request):
        """מגביל יצירה - רק אם אין רשומה קיימת"""
        return not InstagramGallery.objects.exists()


@admin.register(AboutPageSettings)
class AboutPageSettingsAdmin(admin.ModelAdmin):
    """
    ניהול תמונות דף אודות - באנר ו-4 תמונות תוכן
    """
    list_display = ['__str__', 'is_active', 'has_all_images']
    list_editable = ['is_active']
    
    def has_module_permission(self, request):
        """הסתר מרשימת Store - נגיש רק דרך GalleriesHub"""
        return False
    
    def response_add(self, request, obj, post_url_continue=None):
        """חזרה לגלריות אחרי הוספה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            return redirect('/admin/store/gallerieshub/')
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """חזרה לגלריות אחרי עריכה"""
        if '_changelist_filters' in request.GET and request.GET['_changelist_filters'] == 'from_galleries_hub':
            if '_continue' not in request.POST and '_addanother' not in request.POST and '_saveasnew' not in request.POST:
                return redirect('/admin/store/gallerieshub/')
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """חזרה לגלריות אחרי מחיקה"""
        if 'from_galleries_hub' in request.META.get('HTTP_REFERER', ''):
            return redirect('/admin/store/gallerieshub/')
        return super().response_delete(request, obj_display, obj_id)
    
    fieldsets = (
        ('תמונת באנר', {
            'fields': ('banner_image',),
            'description': 'תמונה לבאנר בראש דף האודות'
        }),
        ('תמונות תוכן', {
            'fields': ('content_image_1', 'content_image_2', 'content_image_3', 'content_image_4'),
            'description': 'תמונות לכל אחד מהסקשנים בדף'
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
    )
    
    def has_all_images(self, obj):
        """בדיקה אם כל התמונות מועלות"""
        return bool(
            obj.banner_image and 
            obj.content_image_1 and 
            obj.content_image_2 and 
            obj.content_image_3 and 
            obj.content_image_4
        )
    has_all_images.short_description = 'כל התמונות קיימות'
    has_all_images.boolean = True
    
    def has_add_permission(self, request):
        """מגביל יצירה - רק אם אין רשומה קיימת"""
        return not AboutPageSettings.objects.exists()


@admin.register(GalleriesHub)
class GalleriesHubAdmin(admin.ModelAdmin):
    """
    דף מרכזי לניהול כל הגלריות
    """
    
    def has_add_permission(self, request):
        """לא ניתן להוסיף - זה רק דף תצוגה"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """לא ניתן למחוק - זה רק דף תצוגה"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """תצוגה מותאמת אישית - מציגה את כל הגלריות"""
        extra_context = extra_context or {}
        
        # קבלת כל הגלריות
        site_settings = SiteSettings.objects.first()
        below_bestsellers = BelowBestsellersGallery.objects.first()
        instagram_gallery = InstagramGallery.objects.first()
        about_settings = AboutPageSettings.objects.first()
        retailer_stores_count = RetailerStore.objects.filter(is_active=True).count()
        
        # הכנת נתונים לטמפלייט
        galleries = [
            {
                'name': 'גלריה ראשית',
                'description': 'הבאנר הראשי של דף הבית',
                'model_name': 'sitesettings',
                'obj_id': site_settings.id if site_settings else None,
                'exists': bool(site_settings),
                'has_content': bool(site_settings and site_settings.hero_banner),
            },
            {
                'name': 'גלריה מתחת להכי נמכרים',
                'description': '2 תמונות מתחת לסקשן המוצרים הנמכרים',
                'model_name': 'belowbestsellersgallery',
                'obj_id': below_bestsellers.id if below_bestsellers else None,
                'exists': bool(below_bestsellers),
                'has_content': bool(below_bestsellers and below_bestsellers.right_image and below_bestsellers.left_image),
            },
            {
                'name': 'גלריית אינסטגרם',
                'description': '3 תמונות וקישור לאינסטגרם',
                'model_name': 'instagramgallery',
                'obj_id': instagram_gallery.id if instagram_gallery else None,
                'exists': bool(instagram_gallery),
                'has_content': bool(instagram_gallery and instagram_gallery.image_1),
            },
            {
                'name': 'הגדרות דף אודות',
                'description': 'באנר ו-4 תמונות תוכן לדף אודות',
                'model_name': 'aboutpagesettings',
                'obj_id': about_settings.id if about_settings else None,
                'exists': bool(about_settings),
                'has_content': bool(about_settings and about_settings.banner_image),
            },
            {
                'name': 'חנויות משווקות',
                'description': 'לוגואים של חנויות שמוכרות את המוצרים',
                'model_name': 'retailerstore',
                'obj_id': None,
                'exists': retailer_stores_count > 0,
                'has_content': retailer_stores_count > 0,
                'is_list': True,
                'count': retailer_stores_count,
            },
        ]
        
        extra_context['galleries'] = galleries
        extra_context['title'] = 'ניהול גלריות'
        
        return render(request, 'admin/store/galleries_hub.html', extra_context)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    """
    ניהול מידות
    """
    list_display = ['name', 'display_name', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    list_editable = ['order', 'is_active']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('מידע מידה', {
            'fields': ('name', 'display_name', 'order', 'is_active')
        }),
    )


@admin.register(SizeGroup)
class SizeGroupAdmin(admin.ModelAdmin):
    """
    ניהול קבוצות מידות
    """
    list_display = ['name', 'get_sizes_count', 'get_sizes_preview', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    list_editable = ['order', 'is_active']
    filter_horizontal = ['sizes']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('מידע קבוצה', {
            'fields': ('name', 'order', 'is_active')
        }),
        ('מידות בקבוצה', {
            'fields': ('sizes',),
            'description': 'בחר את המידות שישתייכו לקבוצה זו'
        }),
    )
    
    def get_sizes_count(self, obj):
        """החזרת מספר המידות בקבוצה"""
        return obj.sizes.count()
    get_sizes_count.short_description = 'מספר מידות'
    
    def get_sizes_preview(self, obj):
        """תצוגה מקוצרת של המידות"""
        sizes = list(obj.sizes.all()[:5])
        preview = ', '.join([s.name for s in sizes])
        if obj.sizes.count() > 5:
            preview += '...'
        return preview
    get_sizes_preview.short_description = 'מידות'


@admin.register(FabricType)
class FabricTypeAdmin(admin.ModelAdmin):
    """
    ניהול סוגי בד גלובליים
    """
    list_display = ['name', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    list_editable = ['order', 'is_active']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('מידע בד', {
            'fields': ('name', 'order', 'is_active')
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    ניהול וריאנטים של מוצרים
    """
    list_display = ['product', 'fabric_type', 'size', 'is_available', 'warehouse_location']
    list_filter = ['is_available', 'product', 'fabric_type']
    search_fields = ['product__name', 'fabric_type__name', 'size', 'warehouse_location']
    list_editable = ['is_available', 'warehouse_location']
    
    fieldsets = (
        ('פרטי וריאנט', {
            'fields': ('product', 'fabric_type', 'size')
        }),
        ('זמינות ומיקום', {
            'fields': ('is_available', 'warehouse_location'),
            'description': 'מיקום תא במחסן למלקט (למשל: A12, B05, C23)'
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """סינון סוגי הבד לפי המוצר שנבחר"""
        if db_field.name == "fabric_type":
            # כאן נוכל להוסיף לוגיקה מתקדמת יותר אם נדרש
            pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(MaterialCareInfo)
class MaterialCareInfoAdmin(admin.ModelAdmin):
    """
    ניהול הרכב חומרים וטיפול
    """
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('מידע', {
            'fields': ('name', 'description')
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
        ('תאריכים', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    ניהול שאלות ותשובות
    """
    list_display = ['question', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['question', 'answer']
    list_editable = ['is_active', 'order']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('תוכן', {
            'fields': ('question', 'answer')
        }),
        ('הגדרות', {
            'fields': ('is_active', 'order')
        }),
        ('תאריכים', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BlogSectionInline(admin.TabularInline):
    """
    הצגת סקשנים בתוך פוסט בלוג
    """
    model = BlogSection
    extra = 1
    fields = ('order', 'title', 'content', 'image')
    ordering = ['order']


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """
    ניהול פוסטים בבלוג
    """
    list_display = ['title', 'image_preview', 'sections_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'sections__title', 'sections__content']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at', 'image_preview_large']
    inlines = [BlogSectionInline]
    
    fieldsets = (
        ('באנר ראשי', {
            'fields': ('title', 'slug', 'image', 'image_preview_large'),
            'description': 'כותרת ותמונה ראשית של הפוסט'
        }),
        ('הגדרות', {
            'fields': ('is_active',)
        }),
        ('תאריכים', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """תצוגה מקדימה של התמונה ברשימה"""
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 80px; object-fit: cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'תמונה'
    
    def image_preview_large(self, obj):
        """תצוגה מקדימה גדולה של התמונה"""
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 400px; object-fit: cover;" />', obj.image.url)
        return 'אין תמונה'
    image_preview_large.short_description = 'תצוגה מקדימה'
    
    def sections_count(self, obj):
        """מספר הסקשנים בפוסט"""
        return obj.sections.count()
    sections_count.short_description = 'סקשנים'


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    """
    ניהול מנויי ניוזלטר
    """
    list_display = ['email', 'coupon_code', 'discount_percent', 'is_used', 'is_active', 'created_at']
    list_filter = ['is_used', 'is_active', 'created_at']
    search_fields = ['email', 'coupon_code']
    readonly_fields = ['email', 'coupon_code', 'unsubscribe_token', 'created_at']
    list_editable = ['is_active']
    list_per_page = 50
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """לא לאפשר הוספה ידנית - רק דרך הטופס"""
        return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """
    ניהול קופונים כלליים
    """
    list_display = ['code', 'discount_type', 'discount_value', 'times_used', 'max_uses', 'is_valid_display', 'is_active', 'valid_until']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code']
    list_editable = ['is_active']
    list_per_page = 50
    ordering = ['-created_at']
    readonly_fields = ['times_used', 'created_at']
    
    fieldsets = (
        ('פרטי קופון', {
            'fields': ('code', 'is_active')
        }),
        ('הגדרות הנחה', {
            'fields': ('discount_type', 'discount_value', 'minimum_order_amount')
        }),
        ('תקופת תוקף', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('הגבלות שימוש', {
            'fields': ('max_uses', 'times_used')
        }),
        ('מידע נוסף', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def is_valid_display(self, obj):
        """הצגת סטטוס תקינות"""
        if obj.is_valid():
            return format_html('<span style="color: #2e7d32; font-weight: bold;">✓ תקף</span>')
        return format_html('<span style="color: #c62828;">✗ לא תקף</span>')
    is_valid_display.short_description = 'סטטוס'
    is_valid_display.admin_order_field = 'is_active'
