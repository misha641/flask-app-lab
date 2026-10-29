import json
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, flash, redirect, render_template, request, url_for

from . import app
from .forms import ContactForm


@app.route('/')
def main():
    return render_template('resume.html', title='Резюме')


@app.route('/contact', methods=['GET', 'POST'])
@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    form = ContactForm()
    if form.validate_on_submit():
        entry = {key: getattr(form, key).data for key in ('name', 'email', 'phone', 'subject', 'message')}
        entry['created_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        try:
            path = Path(current_app.config['CONTACT_LOG'])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as log:
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except OSError:
            flash('Не вдалося зберегти звернення. Спробуйте пізніше.', 'danger')
            return render_template('contacts.html', title='Контакти', form=form), 503
        flash('Звернення збережено. Email не надсилався.', 'success')
        return redirect(request.path)
    if request.method == 'POST':
        flash('Перевірте позначені поля форми.', 'danger')
    return render_template('contacts.html', title='Контакти', form=form)


@app.route('/homepage')
def home():
    return render_template(
        'homepage.html', title='Головна', agent=request.user_agent,
    )
