import re
import tempfile
import unittest
from pathlib import Path

from flask.testing import FlaskClient

from app import app


class CSRFClient(FlaskClient):
    def post(self, *args, csrf=True, **kwargs):
        # Отримуємо справжній токен через GET, як браузер. Захист не вимикається.
        if csrf:
            page = self.get('/users/login').get_data(as_text=True)
            token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
            data = dict(kwargs.get('data') or {})
            data.setdefault('csrf_token', token)
            kwargs['data'] = data
        response = super().post(*args, **kwargs)
        # Закриваємо також тимчасовий multipart-потік великих завантажень.
        response.get_data()
        response.close()
        response.request.input_stream.close()
        return response


class IsolatedAppTestCase(unittest.TestCase):
    def setUp(self):
        previous_config = app.config.copy()
        previous_client = app.test_client_class
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(app.config.update, previous_config)
        self.addCleanup(setattr, app, 'test_client_class', previous_client)
        self.directory = Path(temporary.name)
        app.config.update(
            TESTING=True, SECRET_KEY='test-only-key-not-for-server',
            PRODUCTS_DB=self.directory / 'data' / 'products.json',
            CONTACT_LOG=self.directory / 'logs' / 'contacts.log',
            PRODUCT_UPLOAD_DIR=self.directory / 'uploads',
        )
        app.test_client_class = CSRFClient
        self.client = app.test_client()
