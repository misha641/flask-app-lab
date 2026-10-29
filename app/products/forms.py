from decimal import Decimal
from pathlib import Path
import warnings

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from PIL import Image, UnidentifiedImageError
from wtforms import DecimalField, IntegerField, SelectField, SelectChoice, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError

from .storage import CATEGORIES


class ProductForm(FlaskForm):
    name = StringField('Назва', filters=[lambda value: value.strip() if value else value], validators=[
        DataRequired(message='Вкажіть назву.'), Length(min=3, max=120, message='Назва: від 3 до 120 символів.'),
    ])
    content = TextAreaField('Опис', validators=[Optional(), Length(max=5000)], render_kw={'rows': 5, 'cols': 40})
    price = DecimalField('Ціна', places=2, validators=[InputRequired(message='Вкажіть ціну.')])
    category = SelectField('Категорія', choices=[SelectChoice(value, label) for value, label in CATEGORIES])
    quantity = IntegerField('Кількість', validators=[
        InputRequired(message='Вкажіть кількість.'), NumberRange(min=0, message='Кількість не може бути від’ємною.'),
    ])
    image = FileField('Зображення PNG або JPEG (до 5 МБ)', validators=[
        FileAllowed(['png', 'jpg', 'jpeg'], message='Дозволені лише PNG, JPG і JPEG.'),
        FileSize(max_size=5 * 1024 * 1024, message='Зображення має бути не більше 5 МБ.'),
    ])
    submit = SubmitField('Зберегти товар')

    def validate_price(self, field):
        value = field.data
        if value is None or not value.is_finite() or not Decimal('0') < value <= Decimal('999999999.99'):
            raise ValidationError('Ціна має бути додатним числом до 999999999.99.')
        if value.as_tuple().exponent < -2:
            raise ValidationError('Дозволено не більше двох знаків після крапки.')

    def validate_image(self, field):
        if not field.data or field.errors:
            return
        expected = 'PNG' if Path(field.data.filename).suffix.lower() == '.png' else 'JPEG'
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(field.data.stream) as picture:
                    if picture.format != expected:
                        raise ValueError('Image format does not match extension')
                    picture.verify()
                field.data.stream.seek(0)
                with Image.open(field.data.stream) as picture:
                    picture.load()
        except (OSError, ValueError, SyntaxError, UnidentifiedImageError,
                Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ValidationError('Файл не є справним PNG/JPEG відповідного формату.')
        finally:
            field.data.stream.seek(0)
