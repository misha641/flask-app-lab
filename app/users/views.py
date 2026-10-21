from flask import redirect, render_template, request, url_for

from . import users_bp


@users_bp.route('/hi/<string:name>')
def greetings(name):
    name = name.upper()
    age = request.args.get("age", None, int)
    return render_template('users/hi.html', title='Привітання', name=name, age=age)


@users_bp.route('/admin')
def admin():
    return redirect(url_for('users.greetings', name='administrator', age=45))
