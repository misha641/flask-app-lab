from flask import abort, current_app, render_template, send_from_directory

from . import products_bp
from .storage import CATEGORIES, get_product, list_products


@products_bp.route('/product')
@products_bp.route('/products/')
def index():
    return render_template('products/products.html', title='Товари',
                           products=list_products(), categories=dict(CATEGORIES))


@products_bp.route('/product/<int:product_id>')
@products_bp.route('/products/<int:product_id>')
def detail(product_id):
    product = get_product(product_id)
    if product is None:
        abort(404)
    return render_template('products/detail_product.html', title=product['name'],
                           product=product, categories=dict(CATEGORIES))


@products_bp.route('/products/static/uploads/<path:filename>')
def uploaded_image(filename):
    # Окремий static-маршрут Blueprint підтримує тимчасову папку у тестах.
    return send_from_directory(current_app.config['PRODUCT_UPLOAD_DIR'], filename)
