from django.db import models
from django.conf import settings
from django.utils.text import slugify


class SiteSettings(models.Model):
    """
    גלריה ראשית - באנר ראשי של דף הבית
    """
    site_name = models.CharField(max_length=200, default='בוטיק אריה', verbose_name='שם האתר')
    hero_banner = models.ImageField(upload_to='banners/', verbose_name='באנר ראשי')
    hero_title = models.CharField(max_length=200, blank=True, verbose_name='כותרת באנר')
    hero_subtitle = models.TextField(blank=True, verbose_name='תת-כותרת באנר')
    is_active = models.BooleanField(default=True, verbose_name='באנר פעיל')
    
    class Meta:
        verbose_name = 'גלריות - גלריה ראשית'
        verbose_name_plural = 'גלריות - גלריה ראשית'
    
    def __str__(self):
        return 'גלריה ראשית'
    
    @classmethod
    def get_settings(cls):
        """מחזיר את ההגדרות הפעילות של האתר"""
        return cls.objects.filter(is_active=True).first()


class BelowBestsellersGallery(models.Model):
    """
    גלריה של 2 תמונות מתחת לסקשן הכי נמכרים
    """
    right_image = models.ImageField(upload_to='gallery/', verbose_name='תמונה ימנית')
    left_image = models.ImageField(upload_to='gallery/', verbose_name='תמונה שמאלית')
    is_active = models.BooleanField(default=True, verbose_name='גלריה פעילה')
    
    class Meta:
        verbose_name = 'גלריות - גלריה מתחת להכי נמכרים'
        verbose_name_plural = 'גלריות - גלריה מתחת להכי נמכרים'
    
    def __str__(self):
        return 'גלריה מתחת להכי נמכרים'
    
    @classmethod
    def get_gallery(cls):
        """מחזיר את הגלריה הפעילה"""
        return cls.objects.filter(is_active=True).first()


class RetailerStore(models.Model):
    """
    חנות משווקת - לוגואים של חנויות שמוכרות את המוצרים
    """
    name = models.CharField(max_length=100, verbose_name='שם החנות')
    logo = models.ImageField(upload_to='retailers/', verbose_name='לוגו החנות')
    website_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='קישור לאתר', help_text='אופציונלי - קישור לאתר החנות')
    order = models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'גלריות - חנות משווקת'
        verbose_name_plural = 'גלריות - חנויות משווקות'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class InstagramGallery(models.Model):
    """
    גלריית אינסטגרם - 4 תמונות שמובילות לפרופיל האינסטגרם
    """
    image_1 = models.ImageField(upload_to='instagram/', verbose_name='תמונה 1')
    image_2 = models.ImageField(upload_to='instagram/', verbose_name='תמונה 2')
    image_3 = models.ImageField(upload_to='instagram/', verbose_name='תמונה 3')
    image_4 = models.ImageField(upload_to='instagram/', verbose_name='תמונה 4', blank=True, null=True)
    instagram_url = models.URLField(max_length=500, verbose_name='קישור לאינסטגרם', help_text='קישור לפרופיל האינסטגרם של החברה')
    is_active = models.BooleanField(default=True, verbose_name='גלריה פעילה')
    
    class Meta:
        verbose_name = 'גלריות - גלריית אינסטגרם'
        verbose_name_plural = 'גלריות - גלריית אינסטגרם'
    
    def __str__(self):
        return 'גלריית אינסטגרם'
    
    @classmethod
    def get_gallery(cls):
        """מחזיר את הגלריה הפעילה"""
        return cls.objects.filter(is_active=True).first()


class AboutPageSettings(models.Model):
    """
    הגדרות תמונות לדף אודות
    """
    banner_image = models.ImageField(upload_to='about/', verbose_name='תמונת באנר ראשי', help_text='תמונה לבאנר בראש דף האודות')
    content_image_1 = models.ImageField(upload_to='about/', verbose_name='תמונה 1 - אריה', help_text='תמונה לסקשן אריה (משמאל)')
    content_image_2 = models.ImageField(upload_to='about/', verbose_name='תמונה 2 - אריה בוטיק', help_text='תמונה לסקשן אריה בוטיק (מימין)')
    content_image_3 = models.ImageField(upload_to='about/', verbose_name='תמונה 3 - הייחוד שלנו', help_text='תמונה לסקשן הייחוד שלנו (משמאל)')
    content_image_4 = models.ImageField(upload_to='about/', verbose_name='תמונה 4 - האיכות שלנו', help_text='תמונה לסקשן האיכות שלנו (מימין)')
    is_active = models.BooleanField(default=True, verbose_name='הגדרות פעילות')
    
    class Meta:
        verbose_name = 'גלריות - הגדרות דף אודות'
        verbose_name_plural = 'גלריות - הגדרות דף אודות'
    
    def __str__(self):
        return 'הגדרות דף אודות'
    
    @classmethod
    def get_settings(cls):
        """מחזיר את ההגדרות הפעילות"""
        return cls.objects.filter(is_active=True).first()


class GalleriesHub(models.Model):
    """
    מודל וירטואלי לניהול כל הגלריות מדף אחד באדמין
    לא מחזיק נתונים בפועל - רק נקודת כניסה
    """
    class Meta:
        verbose_name = 'גלריות'
        verbose_name_plural = 'גלריות'
        managed = False  # לא ליצור טבלה במסד הנתונים
        default_permissions = ()  # ללא הרשאות
    
    def __str__(self):
        return 'גלריות'


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


class Subcategory(models.Model):
    """
    תת-קטגוריה של מוצרים - שייכת לקטגוריה ראשית
    """
    name = models.CharField(max_length=200, verbose_name='שם תת-קטגוריה')
    slug = models.SlugField(max_length=200, verbose_name='סלאג')
    description = models.TextField(blank=True, verbose_name='תיאור')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='קטגוריה'
    )
    image = models.ImageField(upload_to='subcategories/', blank=True, verbose_name='תמונה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'תת-קטגוריה'
        verbose_name_plural = 'תת-קטגוריות'
        ordering = ['name']
        unique_together = [['slug', 'category']]  # slug צריך להיות unique רק בתוך אותה קטגוריה
    
    def __str__(self):
        return f'{self.category.name} > {self.name}'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    מוצר בחנות
    """
    name = models.CharField(max_length=200, verbose_name='שם מוצר')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='תת כותרת')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='סלאג')
    description = models.TextField(verbose_name='תיאור')
    size = models.CharField(max_length=200, blank=True, verbose_name='גודל')
    
    GENDER_CHOICES = [
        ('boy', 'בן'),
        ('girl', 'בת'),
        ('both', 'שניהם'),
    ]
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='both',
        blank=True,
        verbose_name='מין'
    )
    
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='מחיר')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='כמות במחסן')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', null=True, blank=True, verbose_name='קטגוריה')
    subcategory = models.ForeignKey(
        'Subcategory',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
        verbose_name='תת-קטגוריה'
    )
    image = models.ImageField(upload_to='products/', verbose_name='תמונה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    is_featured = models.BooleanField(default=False, verbose_name='מוצר מומלץ')
    is_bestseller = models.BooleanField(default=False, verbose_name='הכי נמכר')
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


class ProductImage(models.Model):
    """
    תמונות נוספות של מוצר
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='מוצר')
    image = models.ImageField(upload_to='products/', verbose_name='תמונה')
    is_primary = models.BooleanField(default=False, verbose_name='תמונה ראשית')
    order = models.PositiveIntegerField(default=0, verbose_name='סדר')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'תמונת מוצר'
        verbose_name_plural = 'תמונות מוצר'
        ordering = ['-is_primary', 'order', 'created_at']
    
    def __str__(self):
        return f'{self.product.name} - תמונה #{self.id}'


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
    variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='וריאנט'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='כמות')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='מחיר')
    
    class Meta:
        verbose_name = 'פריט בהזמנה'
        verbose_name_plural = 'פריטים בהזמנה'
    
    def __str__(self):
        if self.variant:
            return f'{self.product.name} ({self.variant.get_display_name()}) x {self.quantity}'
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
    variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_items',
        verbose_name='וריאנט'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='כמות')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך הוספה')
    
    class Meta:
        verbose_name = 'פריט בסל'
        verbose_name_plural = 'פריטים בסל'
        unique_together = ('cart', 'product', 'variant')
    
    def __str__(self):
        if self.variant:
            return f'{self.product.name} ({self.variant.get_display_name()}) x {self.quantity}'
        return f'{self.product.name} x {self.quantity}'
    
    @property
    def subtotal(self):
        """סכום ביניים של הפריט"""
        return self.product.price * self.quantity


class ContactMessage(models.Model):
    """
    הודעת צור קשר
    """
    full_name = models.CharField(max_length=200, verbose_name='שם מלא')
    phone = models.CharField(max_length=20, verbose_name='טלפון')
    email = models.EmailField(verbose_name='אימייל')
    order_number = models.CharField(max_length=50, blank=True, verbose_name='מספר הזמנה')
    inquiry = models.TextField(verbose_name='מהות הפנייה')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    is_read = models.BooleanField(default=False, verbose_name='נקרא')
    
    class Meta:
        verbose_name = 'הודעת צור קשר'
        verbose_name_plural = 'הודעות צור קשר'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.full_name} - {self.email} ({self.created_at.strftime("%d/%m/%Y")})'


class Size(models.Model):
    """
    מידה גלובלית - ניתנת לשימוש חוזר בכל המוצרים
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='שם מידה')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='סלאג')
    display_name = models.CharField(max_length=200, blank=True, verbose_name='שם מלא לתצוגה')
    order = models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'מידה'
        verbose_name_plural = 'מידות'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name or self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)


class SizeGroup(models.Model):
    """
    קבוצת מידות - למשל "בגדי גוף", "תינוק שנולד"
    מאפשרת להוסיף מספר מידות במכה אחת למוצר
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='שם קבוצה')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='סלאג')
    sizes = models.ManyToManyField(
        Size, 
        related_name='size_groups',
        verbose_name='מידות',
        help_text='בחר את המידות שנכללות בקבוצה זו'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'קבוצת מידות'
        verbose_name_plural = 'קבוצות מידות'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_sizes_list(self):
        """החזרת רשימת המידות בקבוצה"""
        return ', '.join([size.name for size in self.sizes.all()])


class FabricType(models.Model):
    """
    סוג בד גלובלי - ניתן לשימוש חוזר בכל המוצרים
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='סוג בד')
    order = models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    
    class Meta:
        verbose_name = 'סוג בד'
        verbose_name_plural = 'סוגי בד'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """
    וריאנט מוצר - שילוב של בד + מידה
    כל שילוב מסומן כזמין/לא זמין ויש לו מיקום תא במחסן
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='מוצר'
    )
    fabric_type = models.ForeignKey(
        FabricType,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name='סוג בד'
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name='מידה'
    )
    is_available = models.BooleanField(default=True, verbose_name='זמין')
    warehouse_location = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='מיקום תא במחסן',
        help_text='למשל: A12, B05, C23'
    )
    
    class Meta:
        verbose_name = 'וריאנט מוצר'
        verbose_name_plural = 'וריאנטים של מוצרים'
        ordering = ['fabric_type__order', 'size__order']
        unique_together = ['product', 'fabric_type', 'size']
    
    def __str__(self):
        return f'{self.product.name} - {self.fabric_type.name} - {self.size.name}'
    
    def get_display_name(self):
        """שם לתצוגה ללקוח"""
        return f'{self.fabric_type.name}, מידה {self.size.display_name}'


class WishlistItem(models.Model):
    """
    פריט ברשימת המשאלות של משתמש
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='משתמש'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name='מוצר'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך הוספה')
    
    class Meta:
        verbose_name = 'פריט ברשימת משאלות'
        verbose_name_plural = 'פריטים ברשימת משאלות'
        unique_together = ['user', 'product']
        ordering = ['-added_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.product.name}'


class FAQ(models.Model):
    """
    שאלות ותשובות
    """
    question = models.CharField(max_length=500, verbose_name='שאלה')
    answer = models.TextField(verbose_name='תשובה')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    order = models.IntegerField(default=0, verbose_name='סדר תצוגה')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='תאריך עדכון')
    
    class Meta:
        verbose_name = 'שאלה ותשובה'
        verbose_name_plural = 'שאלות ותשובות'
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.question


class BlogPost(models.Model):
    """
    פוסט בבלוג - כולל באנר ראשי וסקשנים גמישים
    """
    title = models.CharField(max_length=200, verbose_name='כותרת ראשית')
    image = models.ImageField(upload_to='blog/', verbose_name='תמונת באנר ראשי')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='כתובת URL', help_text='יופיע בכתובת הדף (באנגלית, ללא רווחים)')
    is_active = models.BooleanField(default=True, verbose_name='פעיל')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='תאריך יצירה')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='תאריך עדכון')
    
    class Meta:
        verbose_name = 'פוסט בבלוג'
        verbose_name_plural = 'פוסטים בבלוג'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_detail', kwargs={'slug': self.slug})


class BlogSection(models.Model):
    """
    סקשן בפוסט בלוג - כולל כותרת, תוכן ותמונה אופציונלית
    """
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name='פוסט'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')
    title = models.CharField(max_length=200, verbose_name='כותרת הסקשן')
    content = models.TextField(verbose_name='תוכן/פיסקה')
    image = models.ImageField(
        upload_to='blog/sections/',
        blank=True,
        null=True,
        verbose_name='תמונה',
        help_text='תמונה אופציונלית לסקשן'
    )
    
    class Meta:
        verbose_name = 'סקשן בפוסט'
        verbose_name_plural = 'סקשנים בפוסט'
        ordering = ['order']
    
    def __str__(self):
        return f'{self.post.title} - {self.title}'