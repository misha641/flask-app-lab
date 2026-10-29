from flask import Flask, render_template
from flask_wtf.csrf import CSRFError, CSRFProtect

app = Flask(__name__)
app.config.from_pyfile('../config.py')
csrf = CSRFProtect(app)


@app.errorhandler(CSRFError)
def csrf_error(error):
    return render_template('error.html', title='Форму не підтверджено',
                           message='Токен форми відсутній, неправильний або застарів. Оновіть сторінку та повторіть дію.'), 400


@app.errorhandler(413)
def upload_too_large(error):
    return render_template('error.html', title='Завеликий файл',
                           message='Зображення має бути не більше 5 МБ. Поверніться до форми та оберіть менший файл.'), 413

# Маршрути імпортуємо після створення екземпляра app.
from . import views
from .users import users_bp
from .products import products_bp

app.register_blueprint(users_bp)
app.register_blueprint(products_bp)
