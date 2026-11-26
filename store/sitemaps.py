"""
מפת האתר (sitemap.xml) - רשימת העמודים שגוגל אמור לסרוק.
הכתובות נבנות מ-SITE_URL, כך שהן תמיד מצביעות על הדומיין הראשי.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost, Category, Product, Subcategory


class _SiteDomain:
    def __init__(self):
        self.domain = urlsplit(settings.SITE_URL).netloc
        self.name = self.domain


class BaseSitemap(Sitemap):
    def get_urls(self, page=1, site=None, protocol=None):
        scheme = urlsplit(settings.SITE_URL).scheme or 'https'
        return super().get_urls(page=page, site=_SiteDomain(), protocol=scheme)


class StaticSitemap(BaseSitemap):
    changefreq = 'monthly'
    pages = {
        'home': 1.0,
        'about_us': 0.6,
        'blog_list': 0.6,
        'faq': 0.5,
        'shipping_and_returns': 0.5,
        'laundry_instructions': 0.4,
        'contact': 0.4,
        'accessibility_statement': 0.2,
        'terms_of_service': 0.2,
    }

    def items(self):
        return list(self.pages)

    def location(self, name):
        return reverse(name)

    def priority(self, name):
        return self.pages[name]


class CategorySitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True).order_by('id')

    def location(self, category):
        return category.get_absolute_url()


class SubcategorySitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Subcategory.objects.filter(
            is_active=True, category__is_active=True
        ).select_related('category').order_by('id')

    def location(self, subcategory):
        return reverse('subcategory_detail', args=[subcategory.category.slug, subcategory.slug])


class ProductSitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True).order_by('id')

    def location(self, product):
        return reverse('product_detail', args=[product.slug])

    def lastmod(self, product):
        return product.updated_at


class BlogSitemap(BaseSitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return BlogPost.objects.filter(is_active=True).order_by('id')

    def location(self, post):
        return post.get_absolute_url()

    def lastmod(self, post):
        return post.updated_at


sitemaps = {
    'static': StaticSitemap,
    'categories': CategorySitemap,
    'subcategories': SubcategorySitemap,
    'products': ProductSitemap,
    'blog': BlogSitemap,
}
