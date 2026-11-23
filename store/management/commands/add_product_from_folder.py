"""
יצירת מוצר חדש אחד מתיקיית תמונות (למשל תיקייה מסונכרנת של Google Drive).

התמונות נשמרות דרך ה-storage של Django: מקומית ב-media/, ובאתר החי ב-Cloudinary,
בדיוק כמו העלאה מהאדמין.
"""
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import Category, Product, ProductImage, ProductVariant, Size

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')


class Command(BaseCommand):
    help = 'יצירת מוצר חדש מתיקיית תמונות: תמונה ראשית + גלריה'

    def add_arguments(self, parser):
        parser.add_argument('--source-dir', required=True, help='תיקיית התמונות של המוצר')
        parser.add_argument('--main-image', required=True, help='שם קובץ התמונה הראשית')
        parser.add_argument(
            '--gallery',
            nargs='*',
            default=None,
            help='שמות קבצי הגלריה לפי סדר התצוגה. ריק = כל שאר התמונות, לפי שם',
        )
        parser.add_argument('--name', required=True)
        parser.add_argument('--subtitle', default='')
        parser.add_argument('--slug', required=True, help='אותיות לטיניות, ספרות, מקף וקו תחתון')
        parser.add_argument('--description', required=True)
        parser.add_argument('--price', required=True)
        parser.add_argument('--stock', type=int, required=True)
        parser.add_argument('--sizes', default='', help='שמות מידות מופרדים בפסיק, למשל 0-3,3-6')
        parser.add_argument('--category-slug', required=True)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        source_dir = Path(options['source_dir'])
        if not source_dir.is_dir():
            raise CommandError(f'תיקייה לא נמצאה: {source_dir}')

        slug = options['slug']
        if not re.fullmatch(r'[-a-zA-Z0-9_]+', slug):
            raise CommandError(f'סלאג לא חוקי לכתובת URL: {slug}')
        if Product.objects.filter(slug=slug).exists():
            raise CommandError(f'כבר קיים מוצר עם הסלאג {slug}')

        try:
            price = Decimal(options['price'])
        except InvalidOperation:
            raise CommandError(f'מחיר לא חוקי: {options["price"]}')
        if price <= 0:
            raise CommandError('המחיר חייב להיות חיובי')
        if options['stock'] < 0:
            raise CommandError('המלאי לא יכול להיות שלילי')

        category = Category.objects.filter(slug=options['category_slug']).first()
        if not category:
            raise CommandError(f'קטגוריה לא נמצאה: {options["category_slug"]}')

        sizes = []
        for size_name in [s.strip() for s in options['sizes'].split(',') if s.strip()]:
            size = Size.objects.filter(name=size_name, is_active=True).first()
            if not size:
                raise CommandError(f'מידה לא נמצאה: {size_name}')
            sizes.append(size)

        main_image = self._image_path(source_dir, options['main_image'])
        if options['gallery'] is None:
            gallery = sorted(
                (
                    p for p in source_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and p != main_image
                ),
                key=lambda p: p.name.lower(),
            )
        else:
            gallery = [self._image_path(source_dir, name) for name in options['gallery']]
            if main_image in gallery or len(set(gallery)) != len(gallery):
                raise CommandError('תמונה מופיעה יותר מפעם אחת')

        self.stdout.write(
            f'מוצר: {options["name"]} | {options["subtitle"] or "-"} | {slug}\n'
            f'קטגוריה: {category.name} ({category.slug}) | מחיר: {price} | מלאי: {options["stock"]} | '
            f'מידות: {", ".join(s.name for s in sizes) or "-"}\n'
            f'ראשית: {main_image.name}\n'
            f'גלריה: {", ".join(p.name for p in gallery) or "-"}'
        )
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('dry-run: לא נשמר דבר'))
            return

        saved_files = []
        try:
            with transaction.atomic():
                product = Product(
                    name=options['name'],
                    subtitle=options['subtitle'],
                    slug=slug,
                    description=options['description'],
                    price=price,
                    stock_quantity=options['stock'],
                    category=category,
                    gender='both',
                    is_active=True,
                )
                self._save_image(product, main_image, slug, 0, saved_files)

                for size in sizes:
                    ProductVariant.objects.create(product=product, size=size, fabric_type=None)

                for order, path in enumerate(gallery, start=1):
                    extra = ProductImage(product=product, is_primary=False, order=order)
                    self._save_image(extra, path, slug, order, saved_files)
        except Exception:
            # ה-DB חוזר אחורה לבד; קבצים שכבר הועלו צריך למחוק ידנית
            for storage, name in saved_files:
                try:
                    storage.delete(name)
                except Exception as exc:
                    self.stderr.write(f'לא נמחק קובץ {name}: {exc}')
            raise

        self.stdout.write(self.style.SUCCESS(
            f'נוצר מוצר #{product.pk} עם {len(gallery) + 1} תמונות: /product/{product.slug}/'
        ))

    def _image_path(self, source_dir, name):
        path = source_dir / name
        if not path.is_file():
            raise CommandError(f'תמונה לא נמצאה: {path}')
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            raise CommandError(f'סוג קובץ לא נתמך: {path.name}')
        return path

    def _save_image(self, instance, path, slug, index, saved_files):
        stem = re.sub(r'[^A-Za-z0-9]+', '_', path.stem).strip('_').lower() or f'{slug}_{index}'
        with path.open('rb') as fh:
            instance.image.save(f'{stem}{path.suffix.lower()}', File(fh), save=False)
        saved_files.append((instance.image.storage, instance.image.name))
        instance.save()
