"""Загальні налаштування застосунку без секретів."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

DEBUG = False
TESTING = False

PROJECT_ROOT = Path(__file__).resolve().parent
CONTACT_LOG = PROJECT_ROOT / 'logs' / 'contacts.log'
PRODUCTS_DB = PROJECT_ROOT / 'data' / 'products.json'
PRODUCT_UPLOAD_DIR = PROJECT_ROOT / 'app' / 'products' / 'static' / 'uploads'
MAX_CONTENT_LENGTH = 6 * 1024 * 1024
