"""Лабораторна №4: сесія, flash, керування cookies та тема профілю."""

import unittest
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie

from app import app


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        previous = {key: app.config[key] for key in ('TESTING', 'SECRET_KEY', 'SESSION_COOKIE_NAME')}
        app.config.update(TESTING=True, SECRET_KEY='test-only-key-not-for-server')
        self.addCleanup(app.config.update, previous)
        self.client = app.test_client()

    def login(self, **kwargs):
        return self.client.post('/users/login', data={'username': 'misha', 'password': 'lab4pass'}, **kwargs)

    def add_cookie(self, key='note', value='hello', max_age='60', **kwargs):
        return self.client.post('/users/cookies/add', data={
            'key': key, 'value': value, 'max_age': max_age,
        }, **kwargs)


class AuthTests(ClientTestCase):
    def test_login_form_and_navigation(self):
        response = self.client.get('/users/login')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('name="username"', html)
        self.assertIn('name="password" type="password"', html)
        self.assertIn('method="post"', html)
        for path in ['/homepage', '/', '/contacts', '/products/', '/users/login', '/users/profile']:
            self.assertIn(f'href="{path}"', html)

    def test_guest_profile_redirect_and_flash(self):
        response = self.client.get('/users/profile')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/users/login')
        html = self.client.get(response.location).get_data(as_text=True)
        self.assertIn('alert-warning', html)
        self.assertIn('Спочатку увійдіть', html)

    def test_correct_login_stores_only_username_and_redirects(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/users/profile')
        with self.client.session_transaction() as session:
            self.assertEqual(session['username'], 'misha')
            self.assertNotIn('password', session)
            self.assertIn(('success', 'Вхід виконано успішно.'), session['_flashes'])

    def test_wrong_and_missing_credentials(self):
        for data in [{}, {'username': 'misha'}, {'password': 'lab4pass'},
                     {'username': 'misha', 'password': 'wrong'},
                     {'username': 'other', 'password': 'lab4pass'}]:
            with self.subTest(data=data):
                response = self.client.post('/users/login', data=data)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/users/login')
                html = self.client.get(response.location).get_data(as_text=True)
                self.assertIn('alert-danger', html)
                self.assertIn('Неправильне ім’я користувача або пароль.', html)
                with self.client.session_transaction() as session:
                    self.assertNotIn('username', session)

    def test_profile_name_and_flash_consumed_once(self):
        response = self.login(follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<strong>misha</strong>', response.get_data(as_text=True))
        self.assertIn('alert-success', response.get_data(as_text=True))
        self.assertNotIn('Вхід виконано успішно.', self.client.get('/users/profile').get_data(as_text=True))

    def test_profile_uses_and_escapes_session_name(self):
        with self.client.session_transaction() as session:
            session['username'] = '<b>Student</b>'
        html = self.client.get('/users/profile').get_data(as_text=True)
        self.assertIn('&lt;b&gt;Student&lt;/b&gt;', html)
        self.assertNotIn('<b>Student</b>', html)

    def test_logout_removes_login_and_preserves_theme(self):
        self.login()
        self.client.post('/users/theme', data={'theme': 'dark'})
        response = self.client.post('/users/logout')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/users/login')
        with self.client.session_transaction() as session:
            self.assertNotIn('username', session)
        html = self.client.get('/users/login').get_data(as_text=True)
        self.assertIn('Ви вийшли з профілю.', html)
        self.assertIn('alert-info', html)
        self.assertEqual(self.client.get_cookie('lab4_theme').value, 'dark')
        self.assertEqual(self.client.get('/users/profile').location, '/users/login')

    def test_all_mutations_require_post(self):
        self.login()
        for path in ['/users/logout', '/users/cookies/add', '/users/cookies/delete',
                     '/users/cookies/delete-all', '/users/theme']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)

    def test_guest_cannot_mutate_cookies_or_theme(self):
        self.client.set_cookie('lab4_note', 'keep')
        for path in ['/users/cookies/add', '/users/cookies/delete', '/users/cookies/delete-all', '/users/theme']:
            with self.subTest(path=path):
                response = self.client.post(path, data={'key': 'note', 'value': 'changed', 'max_age': '60', 'theme': 'dark'})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/users/login')
                self.assertEqual(self.client.get_cookie('lab4_note').value, 'keep')
                self.assertIsNone(self.client.get_cookie('lab4_theme'))


class CookieTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.login(follow_redirects=True)

    def test_add_cookie_redirect_table_and_expiry(self):
        before = datetime.now(timezone.utc)
        response = self.add_cookie()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/users/profile')
        header = next(h for h in response.headers.getlist('Set-Cookie') if h.startswith('lab4_note='))
        cookie = SimpleCookie(header)['lab4_note']
        self.assertEqual(cookie.value, 'hello')
        self.assertEqual(cookie['max-age'], '60')
        self.assertEqual(cookie['path'], '/')
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertTrue(cookie['httponly'])
        self.assertAlmostEqual((parsedate_to_datetime(cookie['expires']) - before).total_seconds(), 60, delta=3)
        html = self.client.get('/users/profile').get_data(as_text=True)
        self.assertIn('<th scope="row">lab4_note</th><td>hello</td>', html)
        self.assertIn('Cookie lab4_note додано на 60 секунд.', html)

    def test_prefixed_key_unicode_value_and_html_escaping(self):
        response = self.add_cookie(key='lab4_note', value='<b>Привіт</b>', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get_cookie('lab4_note').decoded_value, '<b>Привіт</b>')
        self.assertIsNone(self.client.get_cookie('lab4_lab4_note'))
        self.assertIn('&lt;b&gt;Привіт&lt;/b&gt;', response.get_data(as_text=True))

    def test_invalid_cookie_keys(self):
        for key in ['', 'bad key', 'bad;name', 'bad=name', 'назва', 'a' * 41, 'lab4_', 'bad\r\nname']:
            with self.subTest(key=key):
                response = self.add_cookie(key=key, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('alert-danger', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/users/profile').status_code, 200)

    def test_invalid_cookie_lifetimes(self):
        for age in ['', 'bad', '-1', '0', '1.5', '31536001', '9' * 5000]:
            with self.subTest(age=age[:20]):
                response = self.add_cookie(max_age=age, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('Термін дії має бути цілим числом', response.get_data(as_text=True))
                self.assertIsNone(self.client.get_cookie('lab4_note'))

    def test_missing_fields_and_invalid_values(self):
        response = self.client.post('/users/cookies/add', data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('alert-danger', response.get_data(as_text=True))
        for value in ['x' * 513, 'я' * 257, 'line\nbreak', '\x00', '\x7f']:
            with self.subTest(value_length=len(value)):
                response = self.add_cookie(value=value, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('alert-danger', response.get_data(as_text=True))
                self.assertIsNone(self.client.get_cookie('lab4_note'))

    def test_session_and_theme_are_reserved(self):
        for key in ['session', 'theme', 'lab4_theme']:
            with self.subTest(key=key):
                response = self.add_cookie(key=key, follow_redirects=True)
                self.assertIn('Службову cookie', response.get_data(as_text=True))
                with self.client.session_transaction() as session:
                    self.assertEqual(session['username'], 'misha')
        self.assertIsNone(self.client.get_cookie('lab4_theme'))

    def test_configured_session_name_is_reserved(self):
        app.config['SESSION_COOKIE_NAME'] = 'lab4_auth'
        self.client = app.test_client()
        self.login()
        for key in ['lab4_auth', 'auth']:
            response = self.add_cookie(key=key, follow_redirects=True)
            self.assertIn('Службову cookie', response.get_data(as_text=True))
            with self.client.session_transaction() as session:
                self.assertEqual(session['username'], 'misha')

    def test_delete_cookie_by_full_key(self):
        self.add_cookie()
        response = self.client.post('/users/cookies/delete', data={'key': 'lab4_note'})
        self.assertEqual(response.location, '/users/profile')
        self.assertTrue(any('lab4_note=;' in h and 'Max-Age=0' in h for h in response.headers.getlist('Set-Cookie')))
        self.assertIsNone(self.client.get_cookie('lab4_note'))
        html = self.client.get('/users/profile').get_data(as_text=True)
        self.assertIn('Cookie lab4_note видалено.', html)
        self.assertNotIn('<th scope="row">lab4_note</th>', html)

    def test_delete_longest_key_and_empty_value(self):
        key = 'a' * 40
        self.add_cookie(key=key, value='')
        self.assertEqual(self.client.get_cookie('lab4_' + key).value, '')
        self.client.post('/users/cookies/delete', data={'key': 'lab4_' + key})
        self.assertIsNone(self.client.get_cookie('lab4_' + key))

    def test_invalid_or_unknown_delete_key(self):
        for key, message in [('', 'коректний ключ'), ('bad;key', 'коректний ключ'), ('missing', 'Такої cookie')]:
            with self.subTest(key=key):
                response = self.client.post('/users/cookies/delete', data={'key': key}, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn(message, response.get_data(as_text=True))

    def test_delete_session_logs_out_without_new_session_cookie(self):
        self.add_cookie()
        response = self.client.post('/users/cookies/delete', data={'key': 'session'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.path, '/users/login')
        self.assertIn('Cookie сесії видалено.', response.get_data(as_text=True))
        self.assertIsNone(self.client.get_cookie('session'))
        self.assertIsNotNone(self.client.get_cookie('lab4_note'))
        self.assertEqual(self.client.get('/users/profile').location, '/users/login')

    def test_delete_all_removes_app_cookies_and_preserves_foreign(self):
        self.add_cookie()
        self.client.post('/users/theme', data={'theme': 'dark'})
        self.client.set_cookie('other_app', 'keep')
        response = self.client.post('/users/cookies/delete-all', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.path, '/users/login')
        self.assertIn('сторонні cookies залишено', response.get_data(as_text=True))
        for key in ['session', 'lab4_note', 'lab4_theme']:
            self.assertIsNone(self.client.get_cookie(key))
        self.assertEqual(self.client.get_cookie('other_app').value, 'keep')
        self.assertEqual(self.client.get('/users/profile').location, '/users/login')

    def test_theme_cookie_persists_and_profile_uses_it(self):
        for theme in ['dark', 'light']:
            with self.subTest(theme=theme):
                response = self.client.post('/users/theme', data={'theme': theme})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/users/profile')
                cookie = self.client.get_cookie('lab4_theme')
                self.assertEqual(cookie.value, theme)
                self.assertEqual(cookie.max_age, 31536000)
                self.assertIsNotNone(cookie.expires)
                for _ in range(2):
                    html = self.client.get('/users/profile').get_data(as_text=True)
                    self.assertIn(f'data-bs-theme="{theme}"', html)
                # Новий клієнт із лише збереженою cookie теми, після нового входу.
                new_client = app.test_client()
                new_client.set_cookie('lab4_theme', cookie.value)
                new_client.post('/users/login', data={'username': 'misha', 'password': 'lab4pass'})
                self.assertIn(f'data-bs-theme="{theme}"', new_client.get('/users/profile').get_data(as_text=True))

    def test_invalid_theme_does_not_replace_saved_theme(self):
        self.client.post('/users/theme', data={'theme': 'dark'})
        for theme in ['', 'blue', '<script>']:
            response = self.client.post('/users/theme', data={'theme': theme}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Оберіть світлу або темну тему.', response.get_data(as_text=True))
            self.assertEqual(self.client.get_cookie('lab4_theme').value, 'dark')

    def test_invalid_or_missing_theme_cookie_falls_back_to_light(self):
        for theme in [None, 'unexpected']:
            if theme is not None:
                self.client.set_cookie('lab4_theme', theme)
            self.assertIn('data-bs-theme="light"', self.client.get('/users/profile').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
