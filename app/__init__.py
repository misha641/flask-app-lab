from flask import Flask

app = Flask(__name__)
app.config.from_pyfile('../config.py')

# Маршрути імпортуємо після створення екземпляра app.
from . import views
from .users import users_bp

app.register_blueprint(users_bp)
