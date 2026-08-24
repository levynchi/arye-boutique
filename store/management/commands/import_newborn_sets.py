"""
ייבוא סטי בגדים לתינוק מתיקייה מקומית לקטגוריית newborn.
"""
import os
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from PIL import Image

from store.models import Category, Product, ProductImage, ProductVariant, Size, Subcategory

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')
GALLERY_SUFFIXES = ('_bottom', '_extra', '_top', '_print')
PRINT_CROP_RATIO = 0.4
PRINT_OUTPUT_SIZE = 2000


class Command(BaseCommand):
    help = 'ייבוא סטי בגדים ליילוד: מחיר 85, מלאי 2, מידה 0-3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-dir',
            default=r'C:\Users\levyn\OneDrive\שולחן העבודה\סטים בגדים',
            help='תיקיית הסטים (כל סט בתיקיית משנה)',
        )
        parser.add_argument(
            '--category-slug',
            default='',
            help='סלאג קטגוריה. ריק = חיפוש newborn / new_born',
        )
        parser.add_argument(
            '--price',
            default='85.00',
        )
        parser.add_argument(
            '--stock',
            type=int,
            default=2,
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
        )
        parser.add_argument(
            '--replace-images',
            action='store_true',
            help='החלף תמונות למוצרים שכבר קיימים, בלי ליצור כפילויות',
        )
        parser.add_argument(
            '--main-only',
            action='store_true',
            help='עם --replace-images: החלף רק את תמונת הזוג הראשית, לא את הגלריה',
        )
        parser.add_argument(
            '--generate-print',
            action='store_true',
            help='ייצר תמונת תקריב דפוס מ-_top (או _extra / ראשית) והעלה כתמונת גלריה',
        )

    def handle(self, *args, **options):
        source_dir = Path(options['source_dir'])
        if not source_dir.is_dir():
            raise CommandError(f'תיקייה לא נמצאה: {source_dir}')

        self.use_cloudinary = bool(os.environ.get('CLOUDINARY_CLOUD_NAME'))
        if self.use_cloudinary:
            self._configure_cloudinary()

        category = self._resolve_category(options['category_slug'])
        subcategory = self._resolve_subcategory(category)
        size = Size.objects.filter(name='0-3', is_active=True).first()
        if not size:
            raise CommandError('מידה 0-3 לא נמצאה')

        set_dirs = sorted(
            [p for p in source_dir.iterdir() if p.is_dir()],
            key=lambda p: p.name.lower(),
        )
        if not set_dirs:
            raise CommandError(f'אין תיקיות סטים בתוך {source_dir}')

        self.stdout.write(
            f'קטגוריה: {category.name} ({category.slug}), '
            f'תת-קטגוריה: {subcategory.name if subcategory else "-"}, '
            f'מידה: {size.name}, סטים: {len(set_dirs)}, '
            f'cloudinary: {self.use_cloudinary}'
        )

        created = replaced = skipped = prints = 0
        for set_dir in set_dirs:
            name = set_dir.name.replace('_', ' ')
            slug = slugify(name, allow_unicode=True)
            main_image = self._find_main_image(set_dir)
            extra_images = self._find_extra_images(set_dir, main_image)
            product = Product.objects.filter(slug=slug).first()

            if product:
                if options['replace_images']:
                    if not main_image:
                        self.stdout.write(self.style.ERROR(f'אין תמונה ראשית: {set_dir.name}'))
                        continue
                    extras = [] if options['main_only'] else extra_images
                    label = 'ראשית בלבד' if options['main_only'] else f'{main_image.name} + {len(extras)}'
                    self.stdout.write(f'מחליף תמונות: {name} ({label})')
                    if not options['dry_run']:
                        self._replace_product_images(product, main_image, extras)
                    replaced += 1
                elif not options['generate_print']:
                    self.stdout.write(self.style.WARNING(f'דולג (קיים): {name}'))
                    skipped += 1
                    continue
            elif not main_image:
                self.stdout.write(self.style.ERROR(f'אין תמונה ראשית: {set_dir.name}'))
                continue
            else:
                self.stdout.write(f'יוצר: {name} ({main_image.name} + {len(extra_images)} תמונות)')
                if options['dry_run']:
                    created += 1
                    product = None
                else:
                    product = Product(
                        name=name,
                        slug=slug,
                        description='סט בגדים לתינוק',
                        price=options['price'],
                        stock_quantity=options['stock'],
                        category=category,
                        subcategory=subcategory,
                        gender='both',
                        is_active=True,
                        size_label='מידה',
                    )
                    product.save()
                    self._assign_image(product, main_image)

                    ProductVariant.objects.get_or_create(
                        product=product,
                        size=size,
                        fabric_type=None,
                        defaults={'is_available': True},
                    )

                    for order, extra in enumerate(extra_images, start=1):
                        extra_obj = ProductImage(product=product, is_primary=False, order=order)
                        extra_obj.save()
                        self._assign_image(extra_obj, extra)

                    created += 1

            if options['generate_print']:
                source = self._find_print_source(set_dir, main_image)
                if not source:
                    self.stdout.write(self.style.ERROR(f'אין מקור לתקריב: {name}'))
                elif options['dry_run'] or not product:
                    self.stdout.write(f'תקריב: {name} מ-{source.name}')
                    prints += 1
                elif self._generate_print(product, set_dir, source):
                    self.stdout.write(f'תקריב: {name} מ-{source.name}')
                    prints += 1
                else:
                    self.stdout.write(self.style.ERROR(f'נכשל תקריב: {name}'))

        self.stdout.write(self.style.SUCCESS(
            f'סיום. נוצרו: {created}, הוחלפו: {replaced}, דולגו: {skipped}, תקריבים: {prints}'
        ))

    def _configure_cloudinary(self):
        import cloudinary
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
            api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
        )

    def _replace_product_images(self, product, main_image, extra_images):
        self._assign_image(product, main_image)
        existing = list(product.images.all())
        main_stems = {
            main_image.stem.lower(),
            f'{main_image.stem.lower()}_sq',
            f'{main_image.stem.lower()}_pair',
            f'{main_image.stem.lower()}_pair2',
        }
        for img in existing:
            stem = Path(img.image.name).stem.lower()
            if stem in main_stems:
                self._assign_image(img, main_image)
        for extra in extra_images:
            match = next(
                (
                    img for img in existing
                    if Path(img.image.name).name.lower() == extra.name.lower()
                ),
                None,
            )
            if match:
                self._assign_image(match, extra)
            else:
                extra_obj = ProductImage(
                    product=product,
                    is_primary=False,
                    order=len(existing) + 1,
                )
                extra_obj.save()
                self._assign_image(extra_obj, extra)
                existing.append(extra_obj)

    def _assign_image(self, instance, path):
        if self.use_cloudinary:
            import cloudinary.uploader
            stem_lower = path.stem.lower()
            if stem_lower.endswith('_print'):
                public_stem = path.stem
            elif any(stem_lower.endswith(s) for s in GALLERY_SUFFIXES):
                public_stem = f'{path.stem}_sq'
            else:
                public_stem = f'{path.stem}_pair2'
            cloudinary.uploader.upload(
                str(path),
                public_id=f'media/products/{public_stem}',
                overwrite=True,
                invalidate=True,
                resource_type='image',
            )
            # New public_id so Cloudinary v1 URLs are not served from the old cache
            instance.image.name = f'media/products/{public_stem}.jpg'
            instance.save(update_fields=['image'])
            return

        with path.open('rb') as fh:
            instance.image.save(path.name, File(fh), save=True)

    def _find_print_source(self, set_dir, main_image):
        for suffix in ('_top', '_extra'):
            for ext in IMAGE_SUFFIXES:
                candidate = set_dir / f'{set_dir.name}{suffix}{ext}'
                if candidate.exists():
                    return candidate
            for path in sorted(set_dir.iterdir()):
                if path.suffix.lower() in IMAGE_SUFFIXES and path.stem.lower().endswith(suffix):
                    return path
        return main_image

    def _existing_print_image(self, product):
        for img in product.images.all():
            stem = Path(img.image.name).stem.lower()
            if stem.endswith('_print') or stem.endswith('_print_sq'):
                return img
        return None

    def _make_print_closeup(self, source, dest):
        with Image.open(source) as im:
            im = im.convert('RGB')
            width, height = im.size
            side = min(width, height)
            crop_side = max(1, int(side * PRINT_CROP_RATIO))
            left = (width - crop_side) // 2
            top = (height - crop_side) // 2
            cropped = im.crop((left, top, left + crop_side, top + crop_side))
            cropped = cropped.resize(
                (PRINT_OUTPUT_SIZE, PRINT_OUTPUT_SIZE),
                Image.Resampling.LANCZOS,
            )
            dest.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(dest, 'JPEG', quality=92, optimize=True)

    def _generate_print(self, product, set_dir, source):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / f'{set_dir.name}_print.jpg'
            self._make_print_closeup(source, dest)
            print_image = self._existing_print_image(product)
            if not print_image:
                existing_count = product.images.count()
                print_image = ProductImage(
                    product=product,
                    is_primary=False,
                    order=existing_count + 1,
                )
                print_image.save()
            self._assign_image(print_image, dest)
        return True

    def _resolve_category(self, slug):
        if slug:
            category = Category.objects.filter(slug=slug).first()
            if not category:
                raise CommandError(f'קטגוריה לא נמצאה: {slug}')
            return category

        for candidate in ('newborn', 'new_born'):
            category = Category.objects.filter(slug=candidate).first()
            if category:
                return category

        category = Category.objects.filter(name__icontains='יילוד').first()
        if category:
            return category

        raise CommandError('לא נמצאה קטגוריית newborn / new_born')

    def _resolve_subcategory(self, category):
        active_subs = list(category.subcategories.filter(is_active=True))
        if not active_subs:
            return None

        for slug in ('sets', 'setim', 'סטים'):
            match = next((s for s in active_subs if s.slug == slug or s.name == 'סטים'), None)
            if match:
                return match

        subcategory, created = Subcategory.objects.get_or_create(
            slug='sets',
            category=category,
            defaults={
                'name': 'סטים',
                'is_active': True,
            },
        )
        if created:
            self.stdout.write(self.style.WARNING('נוצרה תת-קטגוריה: סטים'))
        return subcategory

    def _find_main_image(self, set_dir):
        preferred = set_dir / f'{set_dir.name}.jpg'
        if preferred.exists():
            return preferred
        for path in sorted(set_dir.iterdir()):
            if path.suffix.lower() in IMAGE_SUFFIXES and not any(
                path.stem.lower().endswith(suffix) for suffix in GALLERY_SUFFIXES
            ):
                return path
        return None

    def _find_extra_images(self, set_dir, main_image):
        extras = []
        for path in sorted(set_dir.iterdir()):
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if main_image and path.resolve() == main_image.resolve():
                continue
            if path.stem.lower().endswith('_print'):
                continue
            extras.append(path)
        return extras
