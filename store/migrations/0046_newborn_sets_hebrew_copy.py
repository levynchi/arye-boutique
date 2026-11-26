"""
שמות ותיאורים בעברית ל-15 סטי הניובורן המודפסים.

הסטים יובאו עם שם באנגלית ותיאור של שתי מילים. המיגרציה מעדכנת רק מוצר
שעדיין נושא את השם המקורי מהייבוא, כך שמוצר שכבר נערך באדמין לא יידרס.
כתובות העמודים (הסלאג) לא משתנות.
"""
from django.db import migrations

NAME = 'סט ניובורן מעטפת ומכנס'

DETAILS = (
    'הסט כולל בגד גוף מעטפת בשרוול ארוך ומכנס עם רגליות, מ-100% כותנה רכה ונעימה '
    'לעור העדין של התינוק. בגד הגוף נפתח בצד בגזרת מעטפת, כך שלא צריך להשחיל אותו '
    'מעל הראש – נוח במיוחד בשבועות הראשונים.\n\n'
    'את ההדפס אנחנו מדפיסים על הבד בכמות קטנה וגוזרים אצלנו, במפעל המשפחתי שלנו '
    'בישראל. מכל הדפס יש רק סטים בודדים.\n\n'
    'מידה: 0-3 חודשים. מתנה מושלמת ללידה.'
)

# slug: (שם מקורי מהייבוא, שם ההדפס בעברית, משפט פתיחה על ההדפס)
SETS = {
    'african-zebra': (
        'African zebra', 'זברות אפריקאיות',
        'זברות בשחור-לבן פוסעות ורובצות על רקע שמנת – הדפס נקי וגרפי שמתאים לבנים ולבנות.',
    ),
    'autumn-leaves': (
        'Autumn leaves', 'עלי שלכת',
        'עלים ופרחים קטנים בגווני חלודה, כתום וחרדל, בהשראת הסתיו.',
    ),
    'bare-tree': (
        'Bare tree', 'עצים בחורף',
        'עצים וענפים דקים בקו אפור עדין – הדפס שקט ומינימליסטי.',
    ),
    'constellations': (
        'Constellations', 'קבוצות כוכבים',
        'מפת שמיים בקו כהה: קבוצות כוכבים מחוברות בקווים דקים על רקע שמנת.',
    ),
    'giraffe': (
        'Giraffe', 'ג׳ירפות',
        'ג׳ירפות בגווני חום וקרמל, לבד ובזוגות, מפוזרות על רקע שמנת.',
    ),
    'leaves': (
        'Leaves', 'עלים קטנים',
        'עלים קטנים בגווני חום וקרמל, מפוזרים בעדינות על הבד.',
    ),
    'leaves-and-branches': (
        'Leaves and branches', 'עלים וענפים',
        'עלים, ענפים ותרמילים בגווני בז׳ ואפור רך – הדפס טבעי ורגוע.',
    ),
    'leopards-in-the-forest': (
        'Leopards in the forest', 'נמרים ביער',
        'סצנות יער מצוירות בכחול-אפור, בהשראת הדפסי הטואל הצרפתיים הקלאסיים.',
    ),
    'mermaids': (
        'Mermaids', 'בנות ים',
        'בנות ים ודגים שוחים בגווני ורוד, תכלת ומנטה.',
    ),
    'peacock-feathers': (
        'Peacock feathers', 'נוצות טווס',
        'נוצות טווס בירוק, טורקיז וחרדל, לצד עיגולים מנוקדים.',
    ),
    'polar-animals': (
        'Polar animals', 'חיות הקוטב',
        'דובי קוטב, איילים וארנבים בקו מצויר, בין פתיתי שלג קטנים.',
    ),
    'surfers-and-surfboards': (
        'Surfers and surfboards', 'גולשים וגלשנים',
        'גולשים קטנים וגלשנים בגווני פסטל, באווירת קיץ וים.',
    ),
    'vintage-strawberries': (
        'Vintage strawberries', 'תותי וינטג׳',
        'תותים אדמדמים עם עלים ירוקים, בציור בסגנון וינטג׳.',
    ),
    'windblown-seeds': (
        'Windblown seeds', 'זרעי שן-ארי',
        'זרעי שן-ארי עפים ברוח, בקו כהה – הדפס גרפי ואוורירי.',
    ),
    'windblown-seeds-pink': (
        'Windblown seeds pink', 'זרעי שן-ארי בוורוד',
        'זרעים עפים ברוח בגוון ורוד עדין – הגרסה הרכה של הדפס שן-ארי.',
    ),
}


def apply_copy(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    MaterialCareInfo = apps.get_model('store', 'MaterialCareInfo')
    cotton_care = MaterialCareInfo.objects.filter(name='למוצרי הכותנה').first()

    for slug, (original_name, print_name, opening) in SETS.items():
        product = Product.objects.filter(slug=slug, name=original_name).first()
        if product is None:
            continue
        product.name = NAME
        product.subtitle = print_name
        product.description = f'{opening}\n\n{DETAILS}'
        fields = ['name', 'subtitle', 'description']
        if cotton_care and product.material_care_info_id is None:
            product.material_care_info = cotton_care
            fields.append('material_care_info')
        product.save(update_fields=fields)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0045_order_campaign_source'),
    ]

    operations = [
        migrations.RunPython(apply_copy, migrations.RunPython.noop),
    ]
