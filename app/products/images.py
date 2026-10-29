from pathlib import Path
import re
from uuid import uuid4

from flask import current_app


def save_image(upload):
    directory = Path(current_app.config['PRODUCT_UPLOAD_DIR'])
    directory.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + Path(upload.filename).suffix.lower()
    path = directory / filename
    try:
        upload.save(path)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return 'uploads/' + filename


def remove_image(relative_path):
    # Видаляємо лише власні UUID-файли без виходу за каталог завантажень.
    if not re.fullmatch(r'uploads/[0-9a-f]{32}\.(png|jpg|jpeg)', relative_path or ''):
        return
    directory = Path(current_app.config['PRODUCT_UPLOAD_DIR']).resolve()
    path = (directory / Path(relative_path).name).resolve()
    if path.parent != directory:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.warning('Не вдалося прибрати попереднє зображення товару.')
