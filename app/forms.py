from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SelectChoice, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp


class ContactForm(FlaskForm):
    name = StringField('Ім’я', validators=[
        DataRequired(message='Вкажіть ім’я.'),
        Length(min=4, max=10, message='Ім’я має містити від 4 до 10 символів.'),
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Вкажіть email.'), Email(message='Вкажіть коректну адресу email.'),
    ])
    phone = StringField('Телефон (необов’язково)', validators=[
        Optional(), Regexp(r'\A\+380[0-9]{9}\Z', message='Формат телефону: +380 і дев’ять цифр.'),
    ])
    subject = SelectField('Тема', choices=[
        SelectChoice('question', 'Запитання'), SelectChoice('cooperation', 'Співпраця'), SelectChoice('feedback', 'Відгук'),
    ])
    message = TextAreaField('Повідомлення', validators=[
        DataRequired(message='Напишіть повідомлення.'),
        Length(max=500, message='Повідомлення має містити не більше 500 символів.'),
    ])
    submit = SubmitField('Зберегти звернення')
