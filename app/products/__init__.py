from flask import Blueprint

products_bp = Blueprint('products', __name__, template_folder='templates',
                        static_folder='static', static_url_path='/products/static')

from . import views
