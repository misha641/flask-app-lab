import io
import json
from pathlib import Path
import re
from unittest.mock import patch

from PIL import Image
from tinydb import TinyDB

from app import app
from app.products.images import remove_image
from app.products.storage import get_product, list_products, open_database
from support import IsolatedAppTestCase


class ContactFormTests(IsolatedAppTestCase):
    def valid_data(self, **changes):
        return dict(name='Михайло', email='misha@example.com', phone='+380123456789',
                    subject='question', message='Тестове звернення', **changes)

    def test_both_aliases_save_utf8_and_use_prg(self):
        for path in ['/contact', '/contacts']:
            response = self.client.post(path, data=self.valid_data())
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, path)
            page = self.client.get(path)
            self.assertIn('Звернення збережено. Email не надсилався.', page.text)
            self.client.get(path)
        entries = [json.loads(line) for line in app.config['CONTACT_LOG'].read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['name'], 'Михайло')
        self.assertEqual(entries[0]['message'], 'Тестове звернення')
        self.assertNotIn('csrf_token', entries[0])

    def test_invalid_fields_do_not_write_and_preserve_input(self):
        invalid = [('name', ''), ('name', 'abc'), ('name', 'a'*11), ('email', ''),
                   ('email', 'bad'), ('phone', '380123456789'), ('phone', '+380123'),
                   ('phone', '+3801234567890'), ('subject', 'unknown'),
                   ('message', ''), ('message', 'x'*501)]
        for field, value in invalid:
            with self.subTest(field=field, value=value[:20]):
                data = {**self.valid_data(), field: value}
                response = self.client.post('/contact', data=data)
                self.assertEqual(response.status_code, 200)
                self.assertIn('is-invalid', response.text)
                self.assertFalse(app.config['CONTACT_LOG'].exists())
                if field != 'name':
                    self.assertIn('Михайло', response.text)

    def test_optional_phone_and_length_boundaries(self):
        for name in ['abcd', 'abcdefghij']:
            response = self.client.post('/contact', data={**self.valid_data(), 'name': name, 'phone': '', 'message': 'x'*500})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(app.config['CONTACT_LOG'].read_text(encoding='utf-8').splitlines()), 2)

    def test_log_failure_has_no_success_flash(self):
        with patch('app.views.Path.open', side_effect=OSError('disk unavailable')):
            response = self.client.post('/contacts', data=self.valid_data())
        self.assertEqual(response.status_code, 503)
        self.assertIn('Не вдалося зберегти', response.text)
        self.assertNotIn('Звернення збережено.', response.text)
        self.assertIn('Тестове звернення', response.text)

    def test_log_escapes_newlines_as_one_json_record(self):
        self.client.post('/contact', data={**self.valid_data(), 'message': 'Рядок 1\nРядок 2'})
        lines = app.config['CONTACT_LOG'].read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])['message'], 'Рядок 1\nРядок 2')


class ProductCrudTests(IsolatedAppTestCase):
    def values(self, **changes):
        return dict({'name': 'Test product', 'content': 'Опис товару', 'price': '12.30',
                     'category': 'laptops', 'quantity': '0'}, **changes)

    def products(self):
        with app.app_context():
            return list_products()

    def product(self, product_id):
        with app.app_context():
            return get_product(product_id)

    def image(self, format='PNG', filename=None):
        stream = io.BytesIO()
        Image.new('RGB', (24, 24), 'green').save(stream, format=format)
        stream.seek(0)
        return stream, filename or ('test.png' if format == 'PNG' else 'test.jpg')

    def create(self, **changes):
        response = self.client.post('/product/add', data=self.values(**changes))
        self.assertEqual(response.status_code, 302, response.text)
        return int(response.location.rsplit('/', 1)[1])

    def test_aliases_share_products_and_unknown_ids(self):
        for path in ['/product', '/products/']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for prefix in ['/product', '/products']:
            self.assertIn('Laptop', self.client.get(prefix+'/1').text)
            self.assertEqual(self.client.get(prefix+'/999').status_code, 404)
        self.assertEqual(self.client.get('/product/999/edit').status_code, 404)
        self.assertEqual(self.client.post('/product/999/delete', data={'confirm': 'yes'}).status_code, 404)

    def test_create_zero_quantity_and_serializable_price(self):
        product_id = self.create()
        product = self.product(product_id)
        self.assertEqual(product['quantity'], 0)
        self.assertEqual(product['price'], '12.30')
        self.assertTrue(product['created_at'])
        self.assertEqual(product['image'], '')
        self.assertEqual(set(product), {'id', 'name', 'content', 'price', 'category', 'quantity', 'image', 'created_at'})
        self.assertIn('Товар додано.', self.client.get(f'/product/{product_id}').text)
        self.client.get(f'/product/{product_id}')
        self.assertEqual(len(self.products()), 4)
        json.loads(app.config['PRODUCTS_DB'].read_text(encoding='utf-8'))

    def test_edit_prefills_and_preserves_identity(self):
        product_id = self.create()
        original = self.product(product_id)
        page = self.client.get(f'/product/{product_id}/edit').text
        self.assertIn('value="Test product"', page)
        self.assertIn('value="12.30"', page)
        self.assertIn('cols="40"', page)
        self.assertIn('rows="5"', page)
        self.assertIn('multipart/form-data', page)
        response = self.client.post(f'/product/{product_id}/edit', data=self.values(name='Updated', price='0.01', category='phones'))
        self.assertEqual(response.status_code, 302)
        updated = self.product(product_id)
        self.assertEqual(updated['id'], original['id'])
        self.assertEqual(updated['created_at'], original['created_at'])
        self.assertEqual(updated['name'], 'Updated')
        self.assertEqual(updated['price'], '0.01')

    def test_invalid_product_data_never_changes_database(self):
        product_id = self.create()
        before = self.products()
        invalid = [('name', 'ab'), ('name', '   '), ('price', '0'), ('price', '-1'),
                   ('price', '1.234'), ('price', 'NaN'), ('price', 'Infinity'),
                   ('price', 'bad'), ('price', '1e100000'), ('category', 'invalid'),
                   ('quantity', '-1'), ('quantity', '1.5'), ('quantity', ''), ('content', 'x'*5001)]
        for field, value in invalid:
            for path in ['/product/add', f'/product/{product_id}/edit']:
                with self.subTest(path=path, field=field, value=value[:20]):
                    response = self.client.post(path, data=self.values(**{field: value}))
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('is-invalid', response.text)
                    self.assertEqual(self.products(), before)

    def test_delete_requires_post_and_confirmation(self):
        product_id = self.create()
        path = f'/product/{product_id}/delete'
        self.assertEqual(self.client.get(path).status_code, 405)
        self.client.post(path)
        self.assertIsNotNone(self.product(product_id))
        response = self.client.post(path, data={'confirm': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.product(product_id))
        self.assertEqual(self.client.get(f'/product/{product_id}').status_code, 404)

    def test_reopen_persists_and_ids_are_not_reused(self):
        product_id = self.create()
        with TinyDB(app.config['PRODUCTS_DB'], encoding='utf-8') as db:
            stored = next(p for p in db.table('products').all() if p['id'] == product_id)
        self.assertEqual(stored, self.product(product_id))
        self.client.post(f'/product/{product_id}/delete', data={'confirm': 'yes'})
        self.assertGreater(self.create(), product_id)

    def test_seed_once_and_empty_database_stays_empty(self):
        self.assertEqual(len(self.products()), 3)
        self.assertEqual(len(self.products()), 3)
        with app.app_context(), open_database() as db:
            db.table('products').truncate()
        self.assertEqual(self.products(), [])
        self.assertEqual(self.products(), [])
        self.assertIn('Товарів поки немає.', self.client.get('/product').text)

    def test_png_jpeg_upload_uuid_path_and_serving(self):
        for format, filename in [('PNG', '../../outside.png'), ('JPEG', 'photo.JPG'), ('JPEG', 'photo.jpeg')]:
            with self.subTest(filename=filename):
                product_id = self.create(image=self.image(format, filename))
                image_path = self.product(product_id)['image']
                self.assertRegex(image_path, r'^uploads/[a-f0-9]{32}\.(png|jpg|jpeg)$')
                path = app.config['PRODUCT_UPLOAD_DIR'] / Path(image_path).name
                self.assertTrue(path.is_file())
                response = self.client.get('/products/static/' + image_path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, path.read_bytes())
                response.close()
                self.assertIn(image_path, self.client.get(f'/product/{product_id}').text)

    def test_edit_without_image_keeps_old_and_replacement_removes_it(self):
        product_id = self.create(image=self.image())
        original = self.product(product_id)
        old_path = app.config['PRODUCT_UPLOAD_DIR'] / Path(original['image']).name
        self.client.post(f'/product/{product_id}/edit', data=self.values(name='Keep image'))
        self.assertEqual(self.product(product_id)['image'], original['image'])
        self.assertTrue(old_path.exists())
        self.client.post(f'/product/{product_id}/edit', data=self.values(image=self.image('JPEG')))
        updated = self.product(product_id)
        self.assertNotEqual(updated['image'], original['image'])
        self.assertEqual(updated['created_at'], original['created_at'])
        self.assertFalse(old_path.exists())
        new_path = app.config['PRODUCT_UPLOAD_DIR'] / Path(updated['image']).name
        self.assertTrue(new_path.exists())
        self.client.post(f'/product/{product_id}/delete', data={'confirm': 'yes'})
        self.assertFalse(new_path.exists())

    def test_invalid_images_do_not_change_data_or_save_files(self):
        before = self.products()
        files = [(b'not an image', 'fake.png'), (b'<svg/>', 'picture.svg'),
                 (b'x' * (5*1024*1024+1), 'large.jpg')]
        for content, filename in files:
            response = self.client.post('/product/add', data=self.values(image=(io.BytesIO(content), filename)))
            self.assertEqual(response.status_code, 200)
            self.assertIn('is-invalid', response.text)
            self.assertEqual(self.products(), before)
        response = self.client.post('/product/add', data=self.values(image=self.image('JPEG', 'wrong.png')))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.products(), before)
        self.assertFalse(app.config['PRODUCT_UPLOAD_DIR'].exists())

    def test_total_request_limit_returns_friendly_413(self):
        response = self.client.post('/product/add', data=self.values(image=(io.BytesIO(b'x'*(6*1024*1024+1)), 'big.png')))
        self.assertEqual(response.status_code, 413)
        self.assertIn('не більше 5 МБ', response.text)

    def test_failed_database_update_preserves_old_image_and_removes_new(self):
        product_id = self.create(image=self.image())
        before = self.product(product_id)
        old_files = set(app.config['PRODUCT_UPLOAD_DIR'].iterdir())
        with patch('app.products.views.update_product', side_effect=OSError('write failed')):
            response = self.client.post(f'/product/{product_id}/edit', data=self.values(image=self.image('JPEG')))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('Товар оновлено.', response.text)
        self.assertEqual(self.product(product_id), before)
        self.assertEqual(set(app.config['PRODUCT_UPLOAD_DIR'].iterdir()), old_files)

    def test_failed_image_save_does_not_create_product(self):
        before = self.products()
        with patch('app.products.views.save_image', side_effect=OSError('write failed')):
            response = self.client.post('/product/add', data=self.values(image=self.image()))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.products(), before)

    def test_cleanup_does_not_touch_foreign_files(self):
        directory = app.config['PRODUCT_UPLOAD_DIR']
        directory.mkdir()
        foreign = directory / 'user-photo.png'
        foreign.write_bytes(b'keep')
        outside = self.directory / 'outside.png'
        outside.write_bytes(b'keep')
        with app.app_context():
            remove_image('uploads/user-photo.png')
            remove_image('../outside.png')
            remove_image('uploads/../../outside.png')
        self.assertEqual(foreign.read_bytes(), b'keep')
        self.assertEqual(outside.read_bytes(), b'keep')

    def test_placeholder_and_upload_path_traversal(self):
        self.assertIn('product-placeholder.svg', self.client.get('/product/1').text)
        response = self.client.get('/products/static/product-placeholder.svg')
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.get('/products/static/uploads/../forms.py').status_code, 404)


class CSRFTests(IsolatedAppTestCase):
    def test_missing_and_wrong_tokens_rejected_on_all_post_routes(self):
        paths = ['/contact', '/contacts', '/users/login', '/users/logout', '/users/theme',
                 '/users/cookies/add', '/users/cookies/delete', '/users/cookies/delete-all',
                 '/product/add', '/product/1/edit', '/product/1/delete']
        for path in paths:
            for data in [{}, {'csrf_token': 'invalid'}]:
                with self.subTest(path=path, data=data):
                    self.assertEqual(self.client.post(path, data=data, csrf=False).status_code, 400)
        self.assertFalse(app.config['CONTACT_LOG'].exists())
        self.assertFalse(app.config['PRODUCTS_DB'].exists())

    def test_token_from_another_client_is_rejected(self):
        other = app.test_client()
        page = other.get('/contact').text
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
        self.client.get('/contact')
        response = self.client.post('/contact', csrf=False, data={'csrf_token': token})
        self.assertEqual(response.status_code, 400)

    def test_profile_forms_contain_csrf_and_work_after_login(self):
        self.client.post('/users/login', data={'username': 'misha', 'password': 'lab4pass'})
        page = self.client.get('/users/profile').text
        self.assertEqual(page.count('<form'), page.count('name="csrf_token"'))
        response = self.client.post('/users/theme', data={'theme': 'dark'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-bs-theme="dark"', response.text)
