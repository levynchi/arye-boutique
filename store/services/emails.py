"""
מיילים של הזמנות - אישור ללקוח והתראה לבעל האתר (דרך Resend API).
"""
import logging

import resend
from django.conf import settings
from django.utils.html import escape

from .shipping import PICKUP_ADDRESS, SHIPPING_PICKUP

logger = logging.getLogger(__name__)


def _items_rows(order):
    rows = ''
    for item in order.items.select_related('product', 'variant__size', 'variant__fabric_type'):
        name = escape(item.product.name)
        if item.variant:
            name += f'<br><span style="color: #777; font-size: 13px;">{escape(item.variant.get_display_name())}</span>'
        rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{name}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: left;">{item.subtotal} ₪</td>
        </tr>
        """
    return rows


def _totals_block(order):
    lines = ''
    if order.discount_amount and order.discount_amount > 0:
        lines += f'<p style="margin: 5px 0; color: #2e7d32;">הנחה ({escape(order.coupon_code)}): -{order.discount_amount} ₪</p>'
    if order.shipping_method == SHIPPING_PICKUP:
        lines += '<p style="margin: 5px 0;">איסוף עצמי: ללא עלות</p>'
    elif order.shipping_fee and order.shipping_fee > 0:
        lines += f'<p style="margin: 5px 0;">משלוח עד הבית: {order.shipping_fee} ₪</p>'
    else:
        lines += '<p style="margin: 5px 0;">משלוח עד הבית: חינם</p>'
    lines += f'<p style="margin: 5px 0;"><strong>סה״כ שולם:</strong> {order.total_price} ₪</p>'
    return lines


def _delivery_block(order):
    if order.shipping_method == SHIPPING_PICKUP:
        return f"""
            <h3 style="color: #7594b1; margin-top: 0;">איסוף עצמי</h3>
            <p style="margin: 5px 0;">{escape(PICKUP_ADDRESS)}, ימים א'-ה' בין 09:00 ל-15:00.</p>
            <p style="margin: 5px 0;">נשלח הודעה כשההזמנה מוכנה לאיסוף. יש להציג את מספר ההזמנה.</p>
            <p style="margin: 5px 0;">{escape(order.guest_name)} | טלפון: {escape(order.guest_phone)}</p>
        """
    return f"""
            <h3 style="color: #7594b1; margin-top: 0;">כתובת למשלוח</h3>
            <p style="margin: 5px 0;">{escape(order.guest_name)}</p>
            <p style="margin: 5px 0;">{escape(order.guest_address)}</p>
            <p style="margin: 5px 0;">{escape(order.guest_city)}</p>
            <p style="margin: 5px 0;">טלפון: {escape(order.guest_phone)}</p>
        """


def _cancellation_notice():
    return """
            <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #7594b1; margin-top: 0;">ביטול עסקה</h3>
                <p style="margin: 5px 0;">אריה בוטיק, עוסק מורשה 052064219, רחוב הקישון 6, תל אביב, מיקוד 6609306.</p>
                <p style="margin: 5px 0;">אפשר לבטל את העסקה בתוך 14 ימים מיום קבלת המוצר או מיום קבלת מייל זה, לפי המאוחר.</p>
                <p style="margin: 5px 0;">הודעת ביטול: info@arye-boutique.co.il. החזרת המוצר: אריה בוטיק, רחוב הקישון 6, תל אביב, מיקוד 6609306, עם מספר ההזמנה בתוך החבילה.</p>
                <p style="margin: 5px 0;">מהסכום ששולם, כולל דמי משלוח שנגבו, ינוכו דמי ביטול של 5% ממחיר העסקה או 100 ש"ח, לפי הנמוך מביניהם. משלוח ההחזרה על הלקוח.</p>
                <p style="margin: 5px 0;">במוצר פגום, באי-התאמה או באיחור באספקה לא ייגבו דמי ביטול, ועלות ההחזרה עלינו.</p>
                <p style="margin: 5px 0;">המחיר ששולם כולל מע"מ.</p>
            </div>
    """


def _order_table(order):
    return f"""
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #7594b1; margin-top: 0;">פרטי הזמנה #{order.id}</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 10px; text-align: right;">מוצר</th>
                        <th style="padding: 10px; text-align: center;">כמות</th>
                        <th style="padding: 10px; text-align: left;">מחיר</th>
                    </tr>
                    {_items_rows(order)}
                </table>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid #7594b1;">
                    {_totals_block(order)}
                </div>
            </div>
            <div style="background: white; padding: 20px; border-radius: 8px;">
                {_delivery_block(order)}
            </div>
    """


def send_order_confirmation_email(order):
    """
    מייל אישור הזמנה ללקוח.
    """
    if not settings.RESEND_API_KEY or not order.guest_email:
        return False

    resend.api_key = settings.RESEND_API_KEY

    closing = (
        'נעדכן אותך כשההזמנה מוכנה לאיסוף!'
        if order.shipping_method == SHIPPING_PICKUP
        else 'נעדכן אותך כשההזמנה תישלח!'
    )

    html_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #7594b1; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Arye Boutique</h1>
        </div>
        <div style="padding: 30px; background-color: #f9f9f9;">
            <h2 style="color: #333;">תודה על ההזמנה! 🎉</h2>
            <p style="color: #555;">שלום {escape(order.guest_name)},</p>
            <p style="color: #555;">ההזמנה שלך התקבלה בהצלחה ואנחנו מתחילים לטפל בה.</p>
            {_order_table(order)}
            {_cancellation_notice()}
            <p style="color: #555; margin-top: 20px;">{closing}</p>
        </div>
        <div style="background-color: #333; padding: 20px; text-align: center;">
            <p style="color: #999; margin: 0; font-size: 12px;">Arye Boutique | בוטיק לתינוקות</p>
        </div>
    </div>
    """

    resend.Emails.send({
        'from': settings.DEFAULT_FROM_EMAIL,
        'to': [order.guest_email],
        'subject': f'אישור הזמנה #{order.id} - Arye Boutique',
        'html': html_content,
    })
    return True


def send_new_order_notification(order):
    """
    התראה לבעל האתר על הזמנה חדשה ששולמה.
    """
    if not settings.RESEND_API_KEY or not settings.CONTACT_EMAIL:
        return False

    resend.api_key = settings.RESEND_API_KEY

    admin_url = f'{settings.SITE_URL}/admin/store/order/{order.id}/change/'
    notes = f'<p><strong>הערות הלקוח:</strong> {escape(order.notes)}</p>' if order.notes else ''

    html_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="padding: 30px; background-color: #f9f9f9;">
            <h2 style="color: #333;">הזמנה חדשה #{order.id} שולמה</h2>
            <p><strong>לקוח:</strong> {escape(order.guest_name)}</p>
            <p><strong>טלפון:</strong> {escape(order.guest_phone)}</p>
            <p><strong>אימייל:</strong> {escape(order.guest_email)}</p>
            <p><strong>שיטת משלוח:</strong> {escape(order.get_shipping_method_display())}</p>
            {notes}
            {_order_table(order)}
            <p style="margin-top: 20px;"><a href="{admin_url}" style="color: #7594b1;">פתיחת ההזמנה בפאנל הניהול</a></p>
        </div>
    </div>
    """

    params = {
        'from': settings.DEFAULT_FROM_EMAIL,
        'to': [settings.CONTACT_EMAIL],
        'subject': f'הזמנה חדשה #{order.id} - {order.total_price} ₪',
        'html': html_content,
    }
    if order.guest_email:
        params['reply_to'] = order.guest_email
    resend.Emails.send(params)
    return True
