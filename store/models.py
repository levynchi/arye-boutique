from django.db import models
from django.conf import settings
from django.utils.text import slugify


class SiteSettings(models.Model):
    """
    הגדרות כלליות של האתר - באנרים, טקסטים וכו'
    """
    site_name = models.CharField(max_length=200, default='בוטיק אריה', verbose_name='שם האתר')
    hero_banner = models.ImageField(upload_to='banners/', verbose_name='באנר ראשי')
    hero_title = models.CharField(max_length=200, blank=True, verbose_name='כותרת באנר')
    hero_subtitle = models.TextField(blank=True, verbose_name='תת-כותרת באנר')
    is_active = models.BooleanField(default=True, verbose_name='באנר פעיל')
    
    class Meta:
        verbose_name = 'הגדרות אתר'
        verbose_name_plural = 'הגדרות אתר'
    
    def __str__(self):
        return f'הגדרות אתר - {self.site_name}'
    
    @classmethod
    def get_settings(cls):
        """מחזיר את ההגדרות הפעילות של האתר"""
        return cls.objects.filter(is_active=True).first()


class Category(models.Model):
    """
    קטגוריה של מוצרים
    """
    name = models.CharField(max_length=200, unique=True, verbose_name='שם קטגוריה')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='סלאג')
    description = models.TextField(blank=True, verbose_name='תיאור')
    image = models.ImageField(upload_to='categories/', blank=True, verbose_name='תמונה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'קטגוריה'
        verbose_name_plural = 'קטגוריות'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    מוצר בחנות
    """
    name = models.CharField(max_length=200, verbose_name='שם מוצר')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='סלאג')
    description = models.TextField(verbose_name='תיאור')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='מחיר')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='כמות במחסן')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='קטגוריה')
    image = models.ImageField(upload_to='products/', verbose_name='תמונה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    is_featured = models.BooleanField(default=False, verbose_name='מוצר מומלץ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='תאריך עדכון')
    
    class Meta:
        verbose_name = 'מוצר'
        verbose_name_plural = 'מוצרים'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
    
    @property
    def is_in_stock(self):
        """בדיקה אם המוצר במלאי"""
        return self.stock_quantity > 0


class Order(models.Model):
    """
    הזמנה
    """
    STATUS_CHOICES = [
        ('pending', 'ממתין'),
        ('confirmed', 'אושר'),
        ('shipped', 'נשלח'),
        ('delivered', 'נמסר'),
        ('cancelled', 'בוטל'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='orders',
        verbose_name='משתמש'
    )
    # שדות עבור קניה ללא הרשמה
    guest_email = models.EmailField(blank=True, verbose_name='אימייל אורח')
    guest_phone = models.CharField(max_length=20, blank=True, verbose_name='טלפון אורח')
    guest_name = models.CharField(max_length=100, blank=True, verbose_name='שם אורח')
    guest_address = models.CharField(max_length=255, blank=True, verbose_name='כתובת אורח')
    guest_city = models.CharField(max_length=100, blank=True, verbose_name='עיר אורח')
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='סכום כולל')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='סטטוס')
    notes = models.TextField(blank=True, verbose_name='הערות')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='תאריך עדכון')
    
    class Meta:
        verbose_name = 'הזמנה'
        verbose_name_plural = 'הזמנות'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.user:
            return f'הזמנה #{self.id} - {self.user.username}'
        return f'הזמנה #{self.id} - {self.guest_name or self.guest_email}'


class OrderItem(models.Model):
    """
    פריט בהזמנה
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='הזמנה')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='מוצר')
    quantity = models.PositiveIntegerField(default=1, verbose_name='כמות')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='מחיר')
    
    class Meta:
        verbose_name = 'פריט בהזמנה'
        verbose_name_plural = 'פריטים בהזמנה'
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
    @property
    def subtotal(self):
        """סכום ביניים של הפריט"""
        return self.price * self.quantity


class Cart(models.Model):
    """
    סל קניות
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart',
        verbose_name='משתמש'
    )
    session_key = models.CharField(max_length=40, blank=True, verbose_name='מפתח סשן')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='תאריך עדכון')
    
    class Meta:
        verbose_name = 'סל קניות'
        verbose_name_plural = 'סלי קניות'
    
    def __str__(self):
        if self.user:
            return f'סל של {self.user.username}'
        return f'סל #{self.id}'
    
    @property
    def total_price(self):
        """סכום כולל של הסל"""
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def total_items(self):
        """כמות פריטים בסל"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    פריט בסל קניות
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='סל')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='מוצר')
    quantity = models.PositiveIntegerField(default=1, verbose_name='כמות')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך הוספה')
    
    class Meta:
        verbose_name = 'פריט בסל'
        verbose_name_plural = 'פריטים בסל'
        unique_together = ('cart', 'product')
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
    @property
    def subtotal(self):
        """סכום ביניים של הפריט"""
        return self.product.price * self.quantity
