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
