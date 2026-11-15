"""
Email backend ששולח דרך ה-API של Resend.

מאפשר לכל מה שמשתמש ב-django.core.mail (איפוס סיסמה, send_mail) לעבוד
בלי שרת SMTP - באותו ערוץ שבו האתר שולח את שאר המיילים.
"""
import logging

import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'RESEND_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise ValueError('RESEND_API_KEY is not configured')
            return 0

        resend.api_key = api_key
        sent = 0
        for message in email_messages:
            try:
                resend.Emails.send(self._build_params(message))
                sent += 1
            except Exception:
                logger.exception('Resend: failed to send email')
                if not self.fail_silently:
                    raise
        return sent

    @staticmethod
    def _build_params(message):
        params = {
            'from': message.from_email or settings.DEFAULT_FROM_EMAIL,
            'to': list(message.to),
            'subject': message.subject,
        }
        if message.cc:
            params['cc'] = list(message.cc)
        if message.bcc:
            params['bcc'] = list(message.bcc)
        if message.reply_to:
            params['reply_to'] = list(message.reply_to)

        html = None
        for content, mimetype in getattr(message, 'alternatives', None) or []:
            if mimetype == 'text/html':
                html = content
                break

        if message.content_subtype == 'html':
            params['html'] = message.body
        else:
            params['text'] = message.body
            if html:
                params['html'] = html
        return params
