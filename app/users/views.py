from functools import wraps
import re

from flask import current_app, flash, redirect, render_template, request, session, url_for

from . import users_bp

COOKIE_PREFIX = 'lab4_'
THEME_COOKIE = 'lab4_theme'
MAX_COOKIE_AGE = 365 * 24 * 60 * 60


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            flash('Спочатку увійдіть до свого профілю.', 'warning')
            return redirect(url_for('users.login'))
        return view(*args, **kwargs)
    return wrapped


def cookie_name(key):
    """Навчальні cookies мають спільний префікс і безпечну ASCII-назву."""
    if key.startswith(COOKIE_PREFIX):
        key = key[len(COOKIE_PREFIX):]
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', key):
        return None
    return COOKIE_PREFIX + key


@users_bp.route('/hi/<string:name>')
def greetings(name):
    name = name.upper()
    age = request.args.get("age", None, int)
    return render_template('users/hi.html', title='Привітання', name=name, age=age)


@users_bp.route('/admin')
def admin():
    return redirect(url_for('users.greetings', name='administrator', age=45))


@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        # Демонстраційні дані лабораторної, не справжній обліковий запис.
        if username == 'misha' and password == 'lab4pass':
            session.clear()
            session['username'] = username
            flash('Вхід виконано успішно.', 'success')
            return redirect(url_for('users.profile'))
        flash('Неправильне ім’я користувача або пароль.', 'danger')
        return redirect(url_for('users.login'))
    # Після видалення сесії flash створив би нову session-cookie.
    # Тому ці два повідомлення беремо з фіксованого списку, без flash.
    notices = {
        'cookies-cleared': 'Cookies цього застосунку видалено. Вхід завершено; сторонні cookies залишено.',
        'session-cleared': 'Cookie сесії видалено. Вхід завершено.',
    }
    return render_template(
        'users/login.html', title='Вхід', notice=notices.get(request.args.get('notice')),
    )


@users_bp.route('/profile')
@login_required
def profile():
    theme = request.cookies.get(THEME_COOKIE, 'light')
    if theme not in ('light', 'dark'):
        theme = 'light'
    return render_template('users/profile.html', title='Профіль', theme=theme)


@users_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    flash('Ви вийшли з профілю.', 'info')
    return redirect(url_for('users.login'))


@users_bp.route('/cookies/add', methods=['POST'])
@login_required
def add_cookie():
    key = request.form.get('key', '')
    name = cookie_name(key)
    value = request.form.get('value', '')
    max_age = request.form.get('max_age', type=int)
    if current_app.config['SESSION_COOKIE_NAME'] in (key, name) or name == THEME_COOKIE:
        flash('Службову cookie сесії або теми не можна перезаписати цією формою.', 'danger')
    elif name is None:
        flash('Ключ має містити 1–40 латинських літер, цифр, дефісів або підкреслень.', 'danger')
    elif max_age is None or not 1 <= max_age <= MAX_COOKIE_AGE:
        flash('Термін дії має бути цілим числом від 1 до 31536000 секунд.', 'danger')
    elif len(value.encode('utf-8')) > 512 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        flash('Значення має містити до 512 байтів UTF-8 без керівних символів.', 'danger')
    else:
        flash(f'Cookie {name} додано на {max_age} секунд.', 'success')
        response = redirect(url_for('users.profile'))
        response.set_cookie(name, value, max_age=max_age, path='/', httponly=True, samesite='Lax')
        return response
    return redirect(url_for('users.profile'))


@users_bp.route('/cookies/delete', methods=['POST'])
@login_required
def delete_cookie():
    key = request.form.get('key', '')
    session_name = current_app.config['SESSION_COOKIE_NAME']
    if key == session_name:
        session.clear()
        response = redirect(url_for('users.login', notice='session-cleared'))
        response.delete_cookie(session_name, path='/')
        return response
    name = cookie_name(key)
    if name is None:
        flash('Вкажіть коректний ключ cookie: латинські літери, цифри, дефіс або підкреслення; до 40 символів.', 'danger')
    elif name not in request.cookies:
        flash('Такої cookie застосунку немає.', 'warning')
    else:
        flash(f'Cookie {name} видалено.', 'success')
        response = redirect(url_for('users.profile'))
        response.delete_cookie(name, path='/')
        return response
    return redirect(url_for('users.profile'))


@users_bp.route('/cookies/delete-all', methods=['POST'])
@login_required
def delete_all_cookies():
    session.clear()
    response = redirect(url_for('users.login', notice='cookies-cleared'))
    session_name = current_app.config['SESSION_COOKIE_NAME']
    for name in request.cookies:
        if name.startswith(COOKIE_PREFIX) or name == session_name:
            response.delete_cookie(name, path='/')
    return response


@users_bp.route('/theme', methods=['POST'])
@login_required
def change_theme():
    theme = request.form.get('theme')
    response = redirect(url_for('users.profile'))
    if theme not in ('light', 'dark'):
        flash('Оберіть світлу або темну тему.', 'danger')
    else:
        response.set_cookie(THEME_COOKIE, theme, max_age=MAX_COOKIE_AGE, path='/', httponly=True, samesite='Lax')
        flash('Тему профілю збережено.', 'success')
    return response
