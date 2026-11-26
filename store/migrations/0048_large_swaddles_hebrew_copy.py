"""
שם הדפס בעברית ומשפט פתיחה ל-16 חיתולי הטטרה הגדולים, ופסקה על הייצור במפעל.

שם המוצר והתיאור הקיים נשארים. מה שמשתנה:
- תת-הכותרת (שם ההדפס באנגלית) מוחלפת בשם בעברית;
- לפני התיאור נוסף משפט על ההדפס, המשפט "הדפס <שם> קסום." בסופו מוסר,
  ובסוף נוספת פסקה על ההדפסה, הגזירה והתפירה אצלנו.
מוצר שתת-הכותרת שלו כבר לא באנגלית (נערך באדמין) לא משתנה.
"""
import re

from django.db import migrations

FACTORY = (
    'את ההדפס אנחנו מדפיסים על הבד בכמות קטנה, ואת החיתול גוזרים ותופרים אצלנו, '
    'במפעל המשפחתי שלנו בישראל. מכל הדפס יש רק כמות מוגבלת.'
)

# slug: (תת-כותרת מקורית באנגלית, שם ההדפס בעברית, משפט פתיחה)
SWADDLES = {
    'Blue_Shells_muslin_Baby_swaddles': (
        'Blue Shells', 'צדפים כחולים',
        'צדפים בכחול עמוק על רקע לבן, בסידור גרפי וקצבי.',
    ),
    'Little_Giraffe_muslin_Baby_swaddles': (
        'Little Giraffe', 'ג׳ירפה קטנה',
        'ג׳ירפות קטנות בקו אפור עדין, מפוזרות באווריריות על רקע לבן.',
    ),
    'Little_Jungle_muslin_Baby_swaddles': (
        'Little Jungle', 'ג׳ונגל קטן',
        'עצים, פרחים ובקתה קטנה בכחול-אפור, בהשראת הדפסי הטואל הצרפתיים הקלאסיים.',
    ),
    'Little_Polar_Bear_muslin_Baby_swaddles': (
        'Little Polar Bear', 'דוב קוטב קטן',
        'דובי קוטב קטנים בגוונים רכים ועדינים, מפוזרים על רקע לבן.',
    ),
    'Little_Tiger_muslin_Baby_swaddles': (
        'Little Tiger', 'נמר קטן',
        'נמרים קטנים ומנוקדים בגוון חול, פוסעים על רקע לבן.',
    ),
    'Little_Village_muslin_Baby_swaddles': (
        'Little Village', 'כפר קטן',
        'בתים קטנים וכוכבים באפור כהה – כפר קטן ושקט על רקע לבן.',
    ),
    'Peacock_Feathers_muslin_Baby_swaddles': (
        'Peacock Feathers', 'נוצות טווס',
        'נוצות טווס בכחול ותכלת עם "עין" בירוק-צהוב, בשורות צפופות.',
    ),
    'Peacock_Garden_muslin_Baby_swaddles': (
        'Peacock Garden', 'גן הטווסים',
        'טווסים בכחול, ירוק וחרדל, בין שיחים ועלים קטנים.',
    ),
    'Pine_Forest_muslin_Baby_swaddles': (
        'Pine Forest', 'יער אורנים',
        'ענפי אורן ואצטרובלים בירוק-מרווה עדין.',
    ),
    'Sea_Treasures_muslin_Baby_swaddles': (
        'Sea Treasures', 'אוצרות הים',
        'צבי ים, כוכבי ים, צדפים ואלמוגים בגווני טורקיז ובז׳.',
    ),
    'Seeds_in_the_Wind_muslin_Baby_swaddles': (
        'Seeds in the Wind', 'זרעים ברוח',
        'זרעי שן-ארי עפים ברוח, בקו כהה – הדפס גרפי ואוורירי.',
    ),
    'Seeds_of_Bloom_muslin_Baby_swaddles': (
        'Seeds of Bloom', 'זרעי פריחה',
        'עלים, זרעים ופרחים זעירים בגווני אפרסק, אפור ובז׳.',
    ),
    'Soft_Woods_muslin_Baby_swaddles': (
        'Soft Woods', 'יער רך',
        'עצים עגולים קטנים בגוון חום-בז׳, מפוזרים על רקע לבן.',
    ),
    'Tiny_Blue_muslin_Baby_swaddles': (
        'Tiny Blue', 'כחול קטן',
        'הדפס מופשט בגווני כחול ותכלת, כמו מרקם של צבעי מים.',
    ),
    'Tiny_King_muslin_Baby_swaddles': (
        'Tiny King', 'מלך קטן',
        'אריות קטנים עם רעמה זהובה, מפוזרים על רקע לבן.',
    ),
    'Winter_Trees_muslin_Baby_swaddles': (
        'Winter Trees', 'עצי חורף',
        'עצים וענפים דקים בקו אפור – הדפס שקט ומינימליסטי.',
    ),
}


def apply_copy(apps, schema_editor):
    Product = apps.get_model('store', 'Product')

    for slug, (original_subtitle, print_name, opening) in SWADDLES.items():
        product = Product.objects.filter(slug=slug).first()
        if product is None or (product.subtitle or '').strip() != original_subtitle:
            continue
        body = (product.description or '').strip()
        body = re.sub(r'\s*הדפס\s+[^.\n]{1,40}?קסום\.?\s*$', '', body)
        product.subtitle = print_name
        if FACTORY not in body:
            product.description = f'{opening}\n\n{body}\n\n{FACTORY}'
        product.save(update_fields=['subtitle', 'description'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0047_newborn_sets_hebrew_copy_live'),
    ]

    operations = [
        migrations.RunPython(apply_copy, migrations.RunPython.noop),
    ]
