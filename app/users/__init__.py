from flask import Blueprint

users_bp = Blueprint('users', __name__, template_folder='templates', url_prefix='/users')

from . import views
