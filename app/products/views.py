from decimal import Decimal

from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for

from . import products_bp
from .forms import ProductForm
from .images import remove_image, save_image
from .storage import CATEGORIES, create_product, delete_product, get_product, list_products, update_product


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


def product_form(product=None):
    initial = dict(product) if product else {'quantity': 0}
    if product:
        initial['price'] = Decimal(product['price'])
        initial.pop('image', None)
    form = ProductForm(data=initial)
    title = 'Редагувати товар' if product else 'Додати товар'
    if form.validate_on_submit():
        image_path = product['image'] if product else ''
        new_image = ''
        try:
            if form.image.data:
                new_image = save_image(form.image.data)
                image_path = new_image
            values = {field: getattr(form, field).data for field in ('name', 'content', 'category', 'quantity')}
            values.update(price=format(form.price.data, '.2f'), image=image_path)
            if product:
                update_product(product['id'], values)
                product_id = product['id']
            else:
                product_id = create_product(values)
        except OSError:
            remove_image(new_image)
            flash('Не вдалося зберегти товар. Спробуйте пізніше.', 'danger')
            return render_template('products/form.html', title=title, form=form, product=product), 503
        if product and new_image:
            remove_image(product['image'])
        flash('Товар оновлено.' if product else 'Товар додано.', 'success')
        return redirect(url_for('products.detail', product_id=product_id))
    if request.method == 'POST':
        flash('Перевірте позначені поля форми.', 'danger')
    return render_template('products/form.html', title=title, form=form, product=product)


@products_bp.route('/product/add', methods=['GET', 'POST'])
def add():
    return product_form()


@products_bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
def edit(product_id):
    product = get_product(product_id)
    if product is None:
        abort(404)
    return product_form(product)


@products_bp.route('/product/<int:product_id>/delete', methods=['POST'])
def delete(product_id):
    product = get_product(product_id)
    if product is None:
        abort(404)
    if request.form.get('confirm') != 'yes':
        flash('Підтвердьте видалення товару.', 'warning')
        return redirect(url_for('products.detail', product_id=product_id))
    try:
        delete_product(product_id)
    except OSError:
        flash('Не вдалося видалити товар.', 'danger')
        return redirect(url_for('products.detail', product_id=product_id))
    remove_image(product['image'])
    flash('Товар видалено.', 'success')
    return redirect(url_for('products.index'))
