from flask import abort, render_template

from . import products_bp

products = [
    {
        "id": 1,
        "name": "Laptop",
        "price": 1200,
        "content": "Потужний ноутбук з процесором Intel Core i7, 16 ГБ оперативної пам’яті та SSD на 512 ГБ.",
    },
    {
        "id": 2,
        "name": "Phone",
        "price": 800,
        "content": "Смартфон із 6.5-дюймовим OLED-дисплеєм, подвійною камерою та акумулятором на 5000 мА·год.",
    },
    {
        "id": 3,
        "name": "PC",
        "price": 1800,
        "content": "Настільний комп’ютер для ігор або роботи з графікою: RTX 4070, 32 ГБ RAM, 1 ТБ SSD.",
    },
]


@products_bp.route('/')
def index():
    return render_template('products/products.html', title='Товари', products=products)


@products_bp.route('/<int:product_id>')
def detail(product_id):
    for product in products:
        if product['id'] == product_id:
            return render_template(
                'products/detail_product.html', title=product['name'], product=product,
            )
    abort(404)
