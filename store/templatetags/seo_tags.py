import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# אותן החלפות ש-json_script של Django עושה, כדי שתוכן מהאדמין לא יוכל לסגור את תג ה-script
_JSON_ESCAPES = {ord('<'): '\\u003C', ord('>'): '\\u003E', ord('&'): '\\u0026'}


@register.filter
def jsonld(value):
    """מילון פייתון -> JSON בטוח להטמעה בתוך <script type="application/ld+json">."""
    return mark_safe(json.dumps(value, ensure_ascii=False).translate(_JSON_ESCAPES))


@register.filter
def cdn_image(url, width=None):
    """
    גרסה קלה של תמונה מ-Cloudinary: פורמט ואיכות אוטומטיים, ורוחב מוגבל.
    כתובות אחרות (פיתוח מקומי, קבצים סטטיים) חוזרות כמו שהן.
    """
    url = str(url or '')
    marker = '/image/upload/'
    if 'res.cloudinary.com' not in url or marker not in url:
        return url
    transformation = 'f_auto,q_auto'
    if width:
        transformation += f',c_limit,w_{int(width)}'
    return url.replace(marker, f'{marker}{transformation}/', 1)
