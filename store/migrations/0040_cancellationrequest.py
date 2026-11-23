from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0039_category_show_all_products'),
    ]

    operations = [
        migrations.CreateModel(
            name='CancellationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200, verbose_name='שם מלא')),
                ('phone', models.CharField(max_length=20, verbose_name='טלפון')),
                ('email', models.EmailField(max_length=254, verbose_name='אימייל')),
                ('order_number', models.CharField(max_length=50, verbose_name='מספר הזמנה')),
                ('note', models.TextField(blank=True, verbose_name='הערה')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='מועד קבלת ההודעה')),
                ('is_read', models.BooleanField(default=False, verbose_name='טופל')),
            ],
            options={
                'verbose_name': 'בקשת ביטול עסקה',
                'verbose_name_plural': 'בקשות ביטול עסקה',
                'ordering': ['-created_at'],
            },
        ),
    ]
