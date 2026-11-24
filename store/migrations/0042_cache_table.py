from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    """טבלת ה-cache שבה נשמרת ספירת הגבלת הקצב (ראה CACHES בהגדרות)."""
    call_command('createcachetable', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0041_product_recommended_products'),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
