"""
הגבלת קצב פשוטה לטפסים ולנקודות קצה ציבוריות.

הספירה נשמרת ב-cache של Django (טבלה במסד הנתונים), כך שהיא משותפת לכל
תהליכי השרת. כל קריאה ל-is_rate_limited נספרת כניסיון אחד.
"""
import hashlib

from django.core.cache import cache


def client_ip(request):
    """
    כתובת הגולש. האתר רץ מאחורי Cloudflare ו-Railway, ולכן REMOTE_ADDR הוא
    כתובת הפרוקסי. הכותרות האלה נקבעות בידי הפרוקסי, אבל מי שפונה ישירות
    לדומיין של Railway יכול לזייף אותן - לכן יש גם מגבלות לפי יעד (שם משתמש).
    """
    meta = request.META
    forwarded = meta.get('HTTP_X_FORWARDED_FOR', '')
    candidates = (
        meta.get('HTTP_CF_CONNECTING_IP', ''),
        meta.get('HTTP_X_REAL_IP', ''),
        forwarded.split(',')[-1] if forwarded else '',
        meta.get('REMOTE_ADDR', ''),
    )
    for value in candidates:
        value = value.strip()
        if value:
            return value[:64]
    return 'unknown'


def is_rate_limited(request, scope, limit, window, identity=None):
    """
    סופר ניסיון אחד ומחזיר True אם עברו את המגבלה: limit ניסיונות ב-window שניות.
    identity - לפי מה סופרים (ברירת מחדל: כתובת הגולש).
    """
    if identity is None:
        identity = client_ip(request)
    digest = hashlib.sha256(str(identity).strip().lower().encode('utf-8')).hexdigest()[:32]
    key = f'ratelimit:{scope}:{digest}'

    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        # המפתח פג בין שתי הפעולות
        cache.set(key, 1, window)
        count = 1
    return count > limit
