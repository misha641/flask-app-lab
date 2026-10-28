from flask import flash, redirect, render_template, request, session, url_for

from . import users_bp


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
    return render_template('users/login.html', title='Вхід')


@users_bp.route('/profile')
def profile():
    if 'username' not in session:
        flash('Спочатку увійдіть до свого профілю.', 'warning')
        return redirect(url_for('users.login'))
    return render_template('users/profile.html', title='Профіль')


@users_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Ви вийшли з профілю.', 'info')
    return redirect(url_for('users.login'))
