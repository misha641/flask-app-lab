import unittest
from html import unescape
from html.parser import HTMLParser

from app import app
from support import IsolatedAppTestCase


class ProductParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.articles = []
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article':
            self.articles.append(attrs)
        if tag == 'a':
            self.links.append(attrs.get('href'))


class ProductBlueprintTests(IsolatedAppTestCase):

    def test_product_list(self):
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        page = ProductParser(html)
        self.assertEqual(len(page.articles), 3)
        for product_id, name, price in [(1, 'Laptop', 1200), (2, 'Phone', 800), (3, 'PC', 1800)]:
            with self.subTest(product_id=product_id):
                self.assertIn(name, html)
                self.assertIn(f'Ціна: {price}', html)
                self.assertIn(f'/products/{product_id}', page.links)

    def test_product_details(self):
        expected = [
            (1, 'Laptop', 1200, 'Потужний ноутбук з процесором Intel Core i7, 16 ГБ оперативної пам’яті та SSD на 512 ГБ.'),
            (2, 'Phone', 800, 'Смартфон із 6.5-дюймовим OLED-дисплеєм, подвійною камерою та акумулятором на 5000 мА·год.'),
            (3, 'PC', 1800, 'Настільний комп’ютер для ігор або роботи з графікою: RTX 4070, 32 ГБ RAM, 1 ТБ SSD.'),
        ]
        for product_id, name, price, content in expected:
            with self.subTest(product_id=product_id):
                response = self.client.get(f'/products/{product_id}')
                self.assertEqual(response.status_code, 200)
                html = unescape(response.get_data(as_text=True))
                self.assertIn(f'<h1>{name}</h1>', html)
                self.assertIn(f'Товар №{product_id}', html)
                self.assertIn(f'Ціна: {price}', html)
                self.assertIn(content, html)
                for other_id, other_name, _, _ in expected:
                    if other_id != product_id:
                        self.assertNotIn(other_name, html)
                self.assertIn('/products/', ProductParser(html).links)

    def test_unknown_product(self):
        for product_id in [0, 4, 999, -1, 'invalid']:
            with self.subTest(product_id=product_id):
                self.assertEqual(self.client.get(f'/products/{product_id}').status_code, 404)


if __name__ == '__main__':
    unittest.main()
