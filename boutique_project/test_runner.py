"""
Test runner that guarantees the test suite never sends a real email.

The local .env holds a real Resend key, so without this guard every test that
submits a form (contact, cancellation, newsletter) emails the site owner.
"""
from unittest import mock

from django.conf import settings
from django.test.runner import DiscoverRunner


class NoRealEmailTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._real_resend_api_key = settings.RESEND_API_KEY
        settings.RESEND_API_KEY = ''
        # Tests that patch resend.Emails.send themselves stack on top of this one
        self._resend_send_patch = mock.patch('resend.Emails.send', return_value={'id': 'test'})
        self._resend_send_patch.start()

    def teardown_test_environment(self, **kwargs):
        self._resend_send_patch.stop()
        settings.RESEND_API_KEY = self._real_resend_api_key
        super().teardown_test_environment(**kwargs)
