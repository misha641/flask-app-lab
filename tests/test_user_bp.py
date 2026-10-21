import unittest

from app import app


class UserBlueprintTests(unittest.TestCase):
    def setUp(self):
        previous_testing = app.config['TESTING']
        app.config['TESTING'] = True
        self.addCleanup(app.config.update, TESTING=previous_testing)
        self.client = app.test_client()

    def test_greetings_page(self):
        response = self.client.get('/users/hi/John?age=30')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'JOHN', response.data)
        self.assertIn('Вік: 30', response.get_data(as_text=True))

    def test_admin_redirect(self):
        response = self.client.get('/users/admin')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/users/hi/administrator?age=45')

    def test_admin_follow_redirects(self):
        response = self.client.get('/users/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ADMINISTRATOR', response.data)
        self.assertIn('Вік: 45', response.get_data(as_text=True))

    def test_zero_age(self):
        response = self.client.get('/users/hi/John?age=0')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Вік: 0', html)
        self.assertNotIn('Вік не вказано.', html)

    def test_missing_and_invalid_age(self):
        for query in ['', '?age=bad', '?age=', '?age=1.5']:
            with self.subTest(query=query):
                response = self.client.get('/users/hi/John' + query)
                self.assertEqual(response.status_code, 200)
                self.assertIn('Вік не вказано.', response.get_data(as_text=True))

    def test_menu_only_on_greetings(self):
        html = self.client.get('/users/hi/John').get_data(as_text=True)
        self.assertIn('class="greeting-menu"', html)
        self.assertIn('href="/users/hi/John?age=30"', html)
        self.assertIn('href="/users/admin"', html)
        for path in ['/', '/contacts', '/homepage', '/products/', '/products/1']:
            with self.subTest(path=path):
                self.assertNotIn('class="greeting-menu"', self.client.get(path).get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
