"""
עזרי SEO: תיאורי meta, תגי שיתוף (Open Graph) ונתונים מובנים (JSON-LD).
"""
import re

from django.conf import settings
from django.urls import reverse

SITE_NAME = 'אריה בוטיק'
BRAND_NAME = 'Arye Boutique'
DESCRIPTION_LENGTH = 155


def absolute_url(url):
    """כתובת מלאה לשימוש בתגים שנקראים מחוץ לאתר (גוגל, וואטסאפ, פייסבוק)."""
    if not url:
        return ''
    if url.startswith(('http://', 'https://')):
        return url
    return settings.SITE_URL + (url if url.startswith('/') else '/' + url)


def summarize(text, length=DESCRIPTION_LENGTH):
    """טקסט בשורה אחת, מקוצר בגבול מילה."""
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0].rstrip(' ,.-–') + '…'


def image_url(image_field):
    try:
        return absolute_url(image_field.url) if image_field else ''
    except ValueError:
        return ''


def product_full_name(product):
    """שם המוצר יחד עם שם ההדפס - שמות מוצרים חוזרים על עצמם, ההדפס מבדיל ביניהם."""
    if product.subtitle and product.subtitle.strip().lower() != product.name.strip().lower():
        return f'{product.name} – {product.subtitle}'
    return product.name


def breadcrumbs(*crumbs):
    """BreadcrumbList מרשימת (שם, כתובת). דף הבית מתווסף ראשון."""
    items = [('דף הבית', reverse('home'))] + [crumb for crumb in crumbs if crumb]
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': index, 'name': name, 'item': absolute_url(url)}
            for index, (name, url) in enumerate(items, start=1)
        ],
    }


def product_schema(product, images, price_min, price_max):
    url = absolute_url(reverse('product_detail', args=[product.slug]))
    availability = 'https://schema.org/InStock' if product.is_in_stock else 'https://schema.org/OutOfStock'
    if price_min != price_max:
        offers = {
            '@type': 'AggregateOffer',
            'lowPrice': f'{price_min:.2f}',
            'highPrice': f'{price_max:.2f}',
        }
    else:
        offers = {'@type': 'Offer', 'price': f'{price_min:.2f}'}
    offers.update({
        'priceCurrency': 'ILS',
        'availability': availability,
        'itemCondition': 'https://schema.org/NewCondition',
        'url': url,
    })
    schema = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': product_full_name(product),
        'description': summarize(product.description, 500),
        'sku': str(product.id),
        'url': url,
        'brand': {'@type': 'Brand', 'name': BRAND_NAME},
        'offers': offers,
    }
    if images:
        schema['image'] = images
    return schema


def store_schema():
    """פרטי העסק - מוצגים בדף הבית."""
    return {
        '@context': 'https://schema.org',
        '@type': 'ClothingStore',
        'name': BRAND_NAME,
        'alternateName': SITE_NAME,
        'url': settings.SITE_URL + '/',
        'email': 'info@arye-boutique.co.il',
        'telephone': '+972-53-369-4264',
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': 'הקישון 6',
            'addressLocality': 'תל אביב',
            'addressCountry': 'IL',
        },
        'openingHoursSpecification': [{
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'],
            'opens': '09:00',
            'closes': '15:00',
        }],
        'sameAs': [
            'https://www.instagram.com/arye_boutique/',
            'https://www.facebook.com/people/Arye-boutique/61584148260575/',
        ],
    }


def website_schema():
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': BRAND_NAME,
        'alternateName': SITE_NAME,
        'url': settings.SITE_URL + '/',
        'inLanguage': 'he',
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {
                '@type': 'EntryPoint',
                'urlTemplate': settings.SITE_URL + reverse('search') + '?q={search_term_string}',
            },
            'query-input': 'required name=search_term_string',
        },
    }


def faq_schema(faqs):
    return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': faq.question,
                'acceptedAnswer': {'@type': 'Answer', 'text': faq.answer},
            }
            for faq in faqs
        ],
    }


def article_schema(post, description):
    schema = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'headline': post.title,
        'description': description,
        'datePublished': post.created_at.isoformat(),
        'dateModified': post.updated_at.isoformat(),
        'mainEntityOfPage': absolute_url(post.get_absolute_url()),
        'author': {'@type': 'Organization', 'name': BRAND_NAME},
        'publisher': {'@type': 'Organization', 'name': BRAND_NAME},
    }
    image = image_url(post.image)
    if image:
        schema['image'] = [image]
    return schema
