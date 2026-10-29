"""Невелике JSON-сховище TinyDB: файл відкривається на час операції."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from flask import current_app
from tinydb import TinyDB, Query

from .seed import INITIAL_PRODUCTS

CATEGORIES = [('laptops', 'Ноутбуки'), ('phones', 'Телефони'), ('computers', 'Комп’ютери')]
store_lock = RLock()


@contextmanager
def open_database():
    with store_lock:
        path = Path(current_app.config['PRODUCTS_DB'])
        path.parent.mkdir(parents=True, exist_ok=True)
        first_creation = not path.exists()
        with TinyDB(path, encoding='utf-8', ensure_ascii=False, indent=2) as db:
            if first_creation:
                created = datetime.now(timezone.utc).isoformat(timespec='seconds')
                for product, (category, _) in zip(INITIAL_PRODUCTS, CATEGORIES):
                    db.table('products').insert({
                        **product, 'price': f"{product['price']:.2f}", 'category': category,
                        'quantity': 0, 'image': '', 'created_at': created,
                    })
                db.table('metadata').insert({'next_id': 4})
            yield db


def list_products():
    with open_database() as db:
        return db.table('products').all()


def get_product(product_id):
    with open_database() as db:
        return db.table('products').get(Query().id == product_id)


def create_product(values):
    with open_database() as db:
        metadata = db.table('metadata')
        product_id = metadata.get(doc_id=1)['next_id']
        metadata.update({'next_id': product_id + 1}, doc_ids=[1])
        db.table('products').insert({
            **values, 'id': product_id,
            'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        })
        return product_id


def update_product(product_id, values):
    with open_database() as db:
        db.table('products').update(values, Query().id == product_id)


def delete_product(product_id):
    with open_database() as db:
        db.table('products').remove(Query().id == product_id)
