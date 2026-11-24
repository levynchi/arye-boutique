import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class LoginTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dana', email='dana@example.com', password='a-Strong-pass-123', first_name='דנה',
        )

    def login(self, username, next_url=None):
        url = reverse('users:login')
        if next_url is not None:
            url += f'?next={next_url}'
        return self.client.post(url, {'username': username, 'password': 'a-Strong-pass-123'})

    def test_login_with_username(self):
        response = self.login('dana')
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_login_with_email(self):
        response = self.login('Dana@Example.com')
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(reverse('users:login'), {'username': 'dana@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_next_inside_the_site_is_followed(self):
        response = self.login('dana', next_url='/cart/')
        self.assertRedirects(response, '/cart/', fetch_redirect_response=False)

    def test_next_to_another_site_is_ignored(self):
        for target in ('https://evil.example.com/', '//evil.example.com/', 'javascript:alert(1)'):
            with self.subTest(target=target):
                self.client.logout()
                response = self.login('dana', next_url=target)
                self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)


class LogoutTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dana', email='dana@example.com', password='a-Strong-pass-123', first_name='דנה',
        )

    def test_profile_redirects_to_the_site_login_page(self):
        response = self.client.get(reverse('users:profile'))
        self.assertRedirects(
            response,
            f"{reverse('users:login')}?next={reverse('users:profile')}",
            fetch_redirect_response=False,
        )

    def test_profile_shows_a_logout_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:profile'))
        self.assertContains(response, 'התנתק')
        self.assertContains(response, reverse('users:logout'))

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('users:logout'))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

        self.client.force_login(self.user)
        response = self.client.get(reverse('users:logout'))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dana', email='dana@example.com', password='a-Strong-pass-123',
        )

    def request_reset(self, email):
        return self.client.post(reverse('users:password_reset'), {'email': email})

    def test_reset_email_is_sent_with_a_working_link(self):
        response = self.request_reset('dana@example.com')
        self.assertRedirects(response, reverse('users:password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['dana@example.com'])

        link = re.search(r'https?://\S+', message.body).group(0)
        path = '/' + link.split('/', 3)[3]
        response = self.client.get(path, follow=True)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(response.request['PATH_INFO'], {
            'new_password1': 'another-Strong-pass-456',
            'new_password2': 'another-Strong-pass-456',
        })
        self.assertRedirects(response, reverse('users:password_reset_complete'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('another-Strong-pass-456'))

    def test_unknown_email_gets_the_same_response_without_sending(self):
        response = self.request_reset('nobody@example.com')
        self.assertRedirects(response, reverse('users:password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_does_not_crash_the_page(self):
        with mock.patch('django.core.mail.message.EmailMessage.send', side_effect=RuntimeError('mail server down')):
            response = self.request_reset('dana@example.com')
        self.assertRedirects(response, reverse('users:password_reset_done'), fetch_redirect_response=False)


class LoginRateLimitTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='dana', email='dana@example.com', password='a-long-test-password-1!',
        )

    def test_password_guessing_is_blocked_per_account(self):
        url = reverse('users:login')
        for i in range(10):
            response = self.client.post(url, {'username': 'dana', 'password': 'wrong'}, REMOTE_ADDR=f'10.0.0.{i}')
            self.assertEqual(response.status_code, 200)
        # גם הסיסמה הנכונה נחסמת אחרי יותר מדי ניסיונות, ומכתובת אחרת
        response = self.client.post(
            url, {'username': 'dana', 'password': 'a-long-test-password-1!'}, REMOTE_ADDR='10.0.1.1',
        )
        self.assertEqual(response.status_code, 429)

    def test_normal_login_still_works(self):
        response = self.client.post(
            reverse('users:login'), {'username': 'dana', 'password': 'a-long-test-password-1!'},
        )
        self.assertEqual(response.status_code, 302)

    def test_password_reset_requests_are_limited(self):
        url = reverse('users:password_reset')
        for _ in range(5):
            self.assertEqual(self.client.post(url, {'email': 'nobody@example.com'}).status_code, 302)
        self.assertEqual(self.client.post(url, {'email': 'nobody@example.com'}).status_code, 429)
