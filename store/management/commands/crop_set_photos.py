"""
חיתוך תמונות RAW של סטי ניובורן לריבועים 2000x2000.

המיפוי הוא קובץ JSON: שם קובץ -> {product_dir, kind, rotate}
kind: main | top | bottom
rotate: מעלות אחרי תיקון EXIF. 90 = נגד כיוון השעון.
"""
import json
import math
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

OUTPUT_SIZE = 2000
KINDS = {
    'main': '',
    'top': '_top',
    'bottom': '_bottom',
}


class Command(BaseCommand):
    help = 'חיתוך תמונות סטים לריבוע, לפי מיפוי JSON'

    def add_arguments(self, parser):
        parser.add_argument('--source-dir', required=True)
        parser.add_argument(
            '--output-dir',
            default=r'C:\Users\levyn\OneDrive\שולחן העבודה\סטים בגדים 2023_10_23',
        )
        parser.add_argument('--mapping', required=True, help='נתיב לקובץ JSON')
        parser.add_argument('--threshold', type=int, default=16)
        parser.add_argument('--margin', type=float, default=0.04)
        parser.add_argument('--size', type=int, default=OUTPUT_SIZE)

    def handle(self, *args, **options):
        source_dir = Path(options['source_dir'])
        output_dir = Path(options['output_dir'])
        mapping_path = Path(options['mapping'])
        if not source_dir.is_dir():
            raise CommandError(f'תיקיית מקור לא נמצאה: {source_dir}')
        if not mapping_path.is_file():
            raise CommandError(f'קובץ מיפוי לא נמצא: {mapping_path}')

        mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
        if not isinstance(mapping, dict) or not mapping:
            raise CommandError('המיפוי חייב להיות אובייקט JSON לא ריק')

        prepared = []
        seen_outputs = set()
        for filename, spec in mapping.items():
            src = source_dir / filename
            if not src.is_file():
                raise CommandError(f'קובץ לא נמצא: {src}')
            kind = spec.get('kind')
            if kind not in KINDS:
                raise CommandError(f'{filename}: kind לא חוקי ({kind})')
            product_dir = spec.get('product_dir')
            if not product_dir:
                raise CommandError(f'{filename}: חסר product_dir')
            rotate = int(spec.get('rotate', 0))
            dest = output_dir / product_dir / f'{product_dir}{KINDS[kind]}.jpg'
            if dest in seen_outputs:
                raise CommandError(f'שני קבצים נכתבים לאותו יעד: {dest}')
            seen_outputs.add(dest)
            threshold = int(spec.get('threshold', options['threshold']))
            bbox = tuple(spec['bbox']) if spec.get('bbox') else None
            prepared.append((src, dest, product_dir, kind, rotate, threshold, bbox))

        output_dir.mkdir(parents=True, exist_ok=True)
        sheet_items = []
        for src, dest, product_dir, kind, rotate, threshold, bbox_override in prepared:
            image, bbox = self._crop_one(
                src,
                dest,
                rotate,
                threshold,
                options['margin'],
                options['size'],
                bbox_override,
            )
            self.stdout.write(
                f'{src.name} -> {dest.name} '
                f'rotate={rotate} bbox={bbox} out={image.size}'
            )
            sheet_items.append((f'{product_dir} {kind} ({src.name})', image))

        sheet_path = output_dir / '_contact_sheet.jpg'
        self._write_contact_sheet(sheet_items, sheet_path)
        self.stdout.write(self.style.SUCCESS(
            f'סיום. {len(prepared)} תמונות ב-{output_dir} | גיליון: {sheet_path}'
        ))

    def _crop_one(self, src, dest, rotate, threshold, margin, size, bbox_override=None):
        with Image.open(src) as raw:
            image = ImageOps.exif_transpose(raw).convert('RGB')
        image = self._rotate(image, rotate)
        if bbox_override:
            bbox = bbox_override
        else:
            bbox, _background = self._garment_bbox(image, threshold)
        cropped = self._square_crop(image, bbox, margin)
        if cropped.size != (size, size):
            cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(dest, 'JPEG', quality=92, optimize=True)
        return cropped, bbox

    def _rotate(self, image, degrees):
        degrees = int(degrees) % 360
        if degrees == 0:
            return image
        turns = {90: Image.Transpose.ROTATE_90, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_270}
        if degrees not in turns:
            raise CommandError(f'סיבוב נתמך: 0, 90, -90/270, 180 (התקבל {degrees})')
        return image.transpose(turns[degrees])

    def _garment_bbox(self, image, threshold):
        scale = 8
        small = image.resize(
            (max(1, image.width // scale), max(1, image.height // scale)),
            Image.Resampling.BOX,
        )
        background = self._border_color(small)
        diff = ImageChops.difference(small, Image.new('RGB', small.size, background))
        diff = diff.convert('L').filter(ImageFilter.MedianFilter(5))
        mask = diff.point(lambda value: 255 if value > threshold else 0)
        box = mask.getbbox()
        if not box:
            self.stdout.write(self.style.WARNING('לא זוהה בגד, נשמר הפריים המלא'))
            return (0, 0, image.width, image.height), background

        x0, y0, x1, y1 = [value * scale for value in box]
        pad = scale * 2
        x0 = max(0, x0 - pad)
        y0 = max(0, y0 - pad)
        x1 = min(image.width, x1 + pad)
        y1 = min(image.height, y1 + pad)
        area = (x1 - x0) * (y1 - y0)
        if area < image.width * image.height * 0.05:
            self.stdout.write(self.style.WARNING(f'חיתוך קטן מהצפוי: {(x0, y0, x1, y1)}'))
        return (x0, y0, x1, y1), background

    def _border_color(self, image):
        width, height = image.size
        samples = []
        for x in range(width):
            samples.append(image.getpixel((x, 0)))
            samples.append(image.getpixel((x, height - 1)))
        for y in range(height):
            samples.append(image.getpixel((0, y)))
            samples.append(image.getpixel((width - 1, y)))
        mid = len(samples) // 2
        return tuple(sorted(pixel[channel] for pixel in samples)[mid] for channel in range(3))

    def _square_crop(self, image, bbox, margin):
        x0, y0, x1, y1 = bbox
        box_w = max(1, x1 - x0)
        box_h = max(1, y1 - y0)
        x0 = max(0, x0 - int(box_w * margin))
        y0 = max(0, y0 - int(box_h * margin))
        x1 = min(image.width, x1 + int(box_w * margin))
        y1 = min(image.height, y1 + int(box_h * margin))
        box_w = x1 - x0
        box_h = y1 - y0
        side = max(box_w, box_h)
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        left = int(round(center_x - side / 2))
        top = int(round(center_y - side / 2))
        right = left + side
        bottom = top + side
        if left < 0:
            right -= left
            left = 0
        if top < 0:
            bottom -= top
            top = 0
        if right > image.width:
            left -= right - image.width
            right = image.width
        if bottom > image.height:
            top -= bottom - image.height
            bottom = image.height
        left = max(0, left)
        top = max(0, top)
        right = min(right, image.width)
        bottom = min(bottom, image.height)
        cropped = image.crop((left, top, right, bottom))
        if cropped.size == (side, side):
            return cropped
        # רוחב רצועות הרקע הנקיות (ללא בגד) בכל צד של החיתוך
        gx0, gy0, gx1, gy1 = bbox
        clean = (
            max(0, gx0 - left),
            max(0, gy0 - top),
            max(0, right - gx1),
            max(0, bottom - gy1),
        )
        return self._extend_background(cropped, side, clean)

    def _extend_background(self, cropped, side, clean):
        """
        ריפוד לריבוע ע"י המשך הרקע של הצילום עצמו: רצועת הרקע הנקייה שבין קצה
        הצילום לבגד משוקפת ונמתחת לרוחב הריפוד, ואז מטושטשת בעדינות. כך הגוון
        והטקסטורה תואמים לרקע הטבעי ולא נראים כפס אחיד, ובלי לשקף את הבגד.
        """
        clean_left, clean_top, clean_right, clean_bottom = clean
        offset_x = (side - cropped.width) // 2
        offset_y = (side - cropped.height) // 2
        canvas = Image.new('RGB', (side, side))
        canvas.paste(cropped, (offset_x, offset_y))

        if offset_x > 0:
            left_strip = self._mirror_strip(cropped, offset_x, clean_left, axis='x', from_start=True)
            canvas.paste(left_strip, (0, offset_y))
            right_width = side - offset_x - cropped.width
            right_strip = self._mirror_strip(cropped, right_width, clean_right, axis='x', from_start=False)
            canvas.paste(right_strip, (offset_x + cropped.width, offset_y))

        if offset_y > 0:
            band = canvas.crop((0, offset_y, side, offset_y + cropped.height))
            top_strip = self._mirror_strip(band, offset_y, clean_top, axis='y', from_start=True)
            canvas.paste(top_strip, (0, 0))
            bottom_height = side - offset_y - cropped.height
            bottom_strip = self._mirror_strip(band, bottom_height, clean_bottom, axis='y', from_start=False)
            canvas.paste(bottom_strip, (0, offset_y + cropped.height))

        # טשטוש רק באזורי הריפוד, עם מעבר רך לתמונה המקורית
        blur_radius = max(10, side // 80)
        blurred = canvas.filter(ImageFilter.GaussianBlur(blur_radius))
        mask = Image.new('L', (side, side), 255)
        inner = Image.new('L', (cropped.width, cropped.height), 0)
        mask.paste(inner, (offset_x, offset_y))
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
        return Image.composite(blurred, canvas, mask)

    def _mirror_strip(self, source, size, clean, axis, from_start):
        """רצועת רקע משוקפת ברוחב size, שנלקחת רק מתוך clean פיקסלים נקיים בקצה."""
        if size <= 0:
            return Image.new('RGB', (1, 1))
        min_take = 8
        if axis == 'x':
            take = max(min_take, min(size, clean, source.width))
            box = (0, 0, take, source.height) if from_start else (source.width - take, 0, source.width, source.height)
            strip = source.crop(box).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if strip.width != size:
                strip = strip.resize((size, source.height), Image.Resampling.LANCZOS)
            return strip
        take = max(min_take, min(size, clean, source.height))
        box = (0, 0, source.width, take) if from_start else (0, source.height - take, source.width, source.height)
        strip = source.crop(box).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if strip.height != size:
            strip = strip.resize((source.width, size), Image.Resampling.LANCZOS)
        return strip

    def _write_contact_sheet(self, items, dest):
        columns = 3
        thumb = 480
        label_h = 32
        pad = 12
        rows = math.ceil(len(items) / columns)
        sheet = Image.new(
            'RGB',
            (columns * (thumb + pad) + pad, rows * (thumb + label_h + pad) + pad),
            (245, 245, 245),
        )
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 18)
        for index, (label, image) in enumerate(items):
            row, column = divmod(index, columns)
            preview = image.copy()
            preview.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
            x0 = pad + column * (thumb + pad)
            y0 = pad + row * (thumb + label_h + pad)
            sheet.paste(preview, (x0 + (thumb - preview.width) // 2, y0 + (thumb - preview.height) // 2))
            draw.text((x0, y0 + thumb + 4), label[:42], fill=(20, 20, 20), font=font)
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest, 'JPEG', quality=85, optimize=True)
