"""Перевірки спільного застосунку та збереженої поведінки лабораторної №2."""

import unittest
from html.parser import HTMLParser
from xml.etree import ElementTree

from flask import Flask

from app import app
from support import IsolatedAppTestCase


class PageParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def elements(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


class AppTests(IsolatedAppTestCase):

    def test_pages_and_shared_layout(self):
        for path, title in [('/', 'Резюме'), ('/contacts', 'Контакти'), ('/homepage', 'Головна')]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                page = PageParser(html)
                self.assertIn(f'<title>{title} · Михайло Венгринович</title>', html)
                self.assertIn('lang="uk"', html)
                self.assertEqual(len(page.elements('nav')), 1)
                self.assertEqual(len(page.elements('footer')), 1)
                self.assertEqual(len(page.elements('h1')), 1)

    def test_resume_sections_and_links_from_both_pages(self):
        section_ids = ['about', 'education', 'skills', 'technologies', 'projects']
        resume = PageParser(self.client.get('/').get_data(as_text=True))
        self.assertEqual([section['id'] for section in resume.elements('section')], section_ids)
        for path in ['/', '/contacts']:
            with self.subTest(path=path):
                page = PageParser(self.client.get(path).get_data(as_text=True))
                links = {link.get('href') for link in page.elements('a')}
                self.assertTrue({'/', '/contacts'}.issubset(links))
                self.assertTrue({f'/#{section_id}' for section_id in section_ids}.issubset(links))

    def test_static_resources(self):
        resources = [
            ('/static/css/styles.css', 'text/css'),
            ('/static/images/avatar.svg', 'image/svg+xml'),
            ('/static/images/images.jpg', 'image/jpeg'),
        ]
        for path, mimetype in resources:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, mimetype)
                self.assertTrue(response.data)
                if path.endswith('.svg'):
                    self.assertEqual(ElementTree.fromstring(response.data).tag, '{http://www.w3.org/2000/svg}svg')
                response.close()
        for path in ['/', '/contacts']:
            self.assertIn('/static/css/styles.css', self.client.get(path).get_data(as_text=True))
        self.assertIn('/static/images/avatar.svg', self.client.get('/').get_data(as_text=True))

    def test_contact_form_fields_labels_and_csrf(self):
        page = PageParser(self.client.get('/contacts').get_data(as_text=True))
        form, = page.elements('form')
        self.assertEqual(form['action'], '/contacts')
        self.assertEqual(form['method'], 'post')
        self.assertIn('novalidate', form)
        fields = [field for field in page.elements('input') if field.get('type') not in ('hidden', 'submit')]
        fields += page.elements('textarea') + page.elements('select')
        self.assertEqual({field['id'] for field in fields}, {'name', 'email', 'phone', 'subject', 'message'})
        labels = {label['for'] for label in page.elements('label')}
        self.assertEqual(labels, {field['id'] for field in fields})
        self.assertTrue(all('name' in field for field in fields))
        self.assertTrue(any(field.get('name') == 'csrf_token' for field in page.elements('input')))

    def test_contact_form_rejects_empty_and_invalid_post(self):
        for data in [{}, {'name': 'TEST_FORM_VALUE', 'email': 'test@example.invalid', 'message': 'TEST_MESSAGE_VALUE'}]:
            with self.subTest(data=data):
                response = self.client.post('/contacts', data=data)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn('is-invalid', html)
                self.assertIn('Перевірте позначені поля форми.', html)
                self.assertFalse(app.config['CONTACT_LOG'].exists())
                for value in data.values():
                    self.assertIn(value, html)

    def test_wsgi_app_and_mobile_menu_wiring(self):
        self.assertIsInstance(app, Flask)
        for path in ['/', '/contacts']:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                page = PageParser(html)
                toggle = next(button for button in page.elements('button') if button.get('data-bs-toggle') == 'collapse')
                target = toggle['aria-controls']
                self.assertEqual(toggle['data-bs-target'], f'#{target}')
                self.assertTrue(any(attrs.get('id') == target for _, attrs in page.tags))
                self.assertIn('bootstrap@5.3.8/dist/css/bootstrap.min.css', html)
                self.assertIn('bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js', html)

    def test_homepage_user_agent(self):
        agent = 'Lab3Browser/1.0 <script>alert(1)</script>'
        response = self.client.get('/homepage', headers={'User-Agent': agent})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Lab3Browser/1.0 &lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_navigation_on_all_pages(self):
        paths = ['/', '/contacts', '/homepage', '/users/hi/John?age=30',
                 '/products/', '/products/1', '/products/2', '/products/3']
        expected = {'/', '/contacts', '/homepage', '/users/hi/John?age=30', '/products/'}
        expected.update(f'/#{section}' for section in ['about', 'education', 'skills', 'technologies', 'projects'])
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                links = {link.get('href') for link in PageParser(html).elements('a')}
                self.assertTrue(expected.issubset(links))
                self.assertIn('/static/css/styles.css', html)


if __name__ == '__main__':
    unittest.main()
