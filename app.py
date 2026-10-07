from flask import Flask, render_template, request

app = Flask(__name__)


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


if __name__ == '__main__':
    app.run(debug=True)
