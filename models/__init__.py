from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# Setup login manager configurations
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Import models so they are registered with SQLAlchemy
from models.user import User  # noqa: E402
from models.category import Category  # noqa: E402
from models.merchant import Merchant  # noqa: E402
from models.product import Product  # noqa: E402
from models.price_history import ProductPriceHistory  # noqa: E402
from models.click import OutboundClick  # noqa: E402
from models.favorite import Favorite  # noqa: E402

__all__ = [
    'db',
    'login_manager',
    'User',
    'Category',
    'Merchant',
    'Product',
    'ProductPriceHistory',
    'OutboundClick',
    'Favorite'
]
