"""
השלמה ל-0046: באתר החי שם הסטים כבר נערך באדמין ("סט בגד גוף מעטפת ורגלית"),
ושם ההדפס באנגלית נמצא בתת-הכותרת, ולכן 0046 לא עדכנה שם דבר.

כאן שם המוצר נשאר כמו שהוא, ומוחלפים רק:
- תת-כותרת שעדיין זהה לשם המקורי באנגלית, לשם ההדפס בעברית;
- תיאור הייבוא הקצר (פחות מ-40 תווים), לתיאור המלא.
תת-כותרת או תיאור שכבר נערכו לא נדרסים.
"""
from importlib import import_module

from django.db import migrations

copy = import_module('store.migrations.0046_newborn_sets_hebrew_copy')

PLACEHOLDER_MAX_LENGTH = 40


def apply_copy(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    MaterialCareInfo = apps.get_model('store', 'MaterialCareInfo')
    cotton_care = MaterialCareInfo.objects.filter(name='למוצרי הכותנה').first()

    for slug, (original_name, print_name, opening) in copy.SETS.items():
        product = Product.objects.filter(slug=slug).first()
        if product is None:
            continue
        fields = []
        if (product.subtitle or '').strip() == original_name:
            product.subtitle = print_name
            fields.append('subtitle')
        if len((product.description or '').strip()) < PLACEHOLDER_MAX_LENGTH:
            product.description = f'{opening}\n\n{copy.DETAILS}'
            fields.append('description')
        if cotton_care and product.material_care_info_id is None:
            product.material_care_info = cotton_care
            fields.append('material_care_info')
        if fields:
            product.save(update_fields=fields)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0046_newborn_sets_hebrew_copy'),
    ]

    operations = [
        migrations.RunPython(apply_copy, migrations.RunPython.noop),
    ]
