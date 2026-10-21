from flask import render_template, request

from . import app


@app.route('/')
def main():
    return render_template('resume.html', title='Резюме')


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    # Заглушка: не читаємо і не зберігаємо дані форми.
    return render_template(
        'contacts.html',
        title='Контакти',
        form_submitted=request.method == 'POST',
    )


@app.route('/homepage')
def home():
    return render_template(
        'homepage.html', title='Головна', agent=request.user_agent,
    )
