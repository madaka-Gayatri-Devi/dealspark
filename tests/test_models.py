from decimal import Decimal
from models import Product, User, Category, Merchant


def test_pricing_calculation_standard():
    orig, disc, savings, discount_pct = Product.calculate_pricing(1000, 400)
    assert orig == Decimal('1000.00')
    assert disc == Decimal('400.00')
    assert savings == Decimal('600.00')
    assert discount_pct == Decimal('60.0')


def test_pricing_calculation_zero_savings():
    orig, disc, savings, discount_pct = Product.calculate_pricing(500, 500)
    assert savings == Decimal('0.00')
    assert discount_pct == Decimal('0.0')


def test_pricing_calculation_prevent_negative():
    # If discounted price is entered higher than original
    orig, disc, savings, discount_pct = Product.calculate_pricing(200, 300)
    assert disc == Decimal('200.00')
    assert savings == Decimal('0.00')
    assert discount_pct == Decimal('0.0')


def test_pricing_calculation_division_by_zero():
    orig, disc, savings, discount_pct = Product.calculate_pricing(0, 0)
    assert orig == Decimal('0.00')
    assert savings == Decimal('0.00')
    assert discount_pct == Decimal('0.0')


def test_user_password_and_roles(app):
    with app.app_context():
        user = User(username='testshopper', email='test@example.com', role='user')
        user.set_password('mysecretpass123')
        assert user.check_password('mysecretpass123') is True
        assert user.check_password('wrongpass') is False
        assert user.is_admin is False

        # Authorized administrator email
        admin = User(username='headadmin', email='nagarajuchaintala2002@gmail.com', role='admin')
        assert admin.is_admin is True

        # Unauthorized email attempting to hold role='admin'
        fake_admin = User(username='fakeadmin', email='imposter@example.com', role='admin')
        assert fake_admin.is_admin is False


def test_category_and_merchant_slugs(app):
    with app.app_context():
        cat = Category(name='Home & Kitchen Essentials')
        assert cat.slug == 'home-kitchen-essentials'

        merch = Merchant(name='Amazon India Prime', domain='amazon.in')
        assert merch.slug == 'amazon-india-prime'
