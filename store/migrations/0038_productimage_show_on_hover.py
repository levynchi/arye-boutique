from django.db import migrations, models


def mark_existing_print_closeups(apps, schema_editor):
    """תקריבי הדפוס הקיימים זוהו עד עכשיו לפי '_print' בשם הקובץ."""
    ProductImage = apps.get_model('store', 'ProductImage')
    ProductImage.objects.filter(image__contains='_print').update(show_on_hover=True)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0037_order_shipping_and_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='show_on_hover',
            field=models.BooleanField(
                default=False,
                help_text='התמונה תוצג כשעומדים עם העכבר על המוצר בדפי הקטגוריה (זום על ההדפס), '
                          'ולא תופיע בין החצים של כרטיס המוצר. מומלץ לסמן תמונה אחת לכל מוצר.',
                verbose_name='תקריב בריחוף',
            ),
        ),
        migrations.RunPython(mark_existing_print_closeups, migrations.RunPython.noop),
    ]
