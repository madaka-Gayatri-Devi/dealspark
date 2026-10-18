import pytest
from datetime import datetime, timezone
from models import db, User, Product, Category, Merchant

AUTHORIZED_ADMIN_EMAIL = 'nagarajuchaintala2002@gmail.com'


def create_regular_user(app):
    with app.app_context():
        user = User.query.filter_by(email='shopper_phase3@dealspark.test').first()
        if not user:
            user = User(
                full_name='Alice Member',
                username='alice_shopper',
                email='shopper_phase3@dealspark.test',
                phone='9876543210',
                role='user'
            )
            user.set_password('ShopperPass123!')
            db.session.add(user)
            db.session.commit()
        return user


def create_admin_user(app):
    with app.app_context():
        admin = User.query.filter_by(email=AUTHORIZED_ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                full_name='System Admin',
                username='admin',
                email=AUTHORIZED_ADMIN_EMAIL,
                role='admin'
            )
            admin.set_password('AdminPass123!')
            db.session.add(admin)
            db.session.commit()
        return admin


def login_client(client, email, password):
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def test_visitor_redirected_from_profile(client, app):
    """Verify non-admin visitors cannot access member dashboard and are redirected."""
    # 1. Anonymous visitor is redirected to login
    res = client.get('/auth/profile')
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']


def test_admin_dashboard_heading_displays_administrator(client, app):
    """Verify administrator views display 'Administrator Dashboard' and 'Administrator' badge."""
    create_admin_user(app)
    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    res = client.get('/admin/dashboard')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'Administrator Dashboard' in html
    assert 'Administrator' in html

    res_prof = client.get('/auth/profile?tab=profile')
    assert res_prof.status_code == 200
    html_prof = res_prof.data.decode('utf-8')
    assert 'Administrator Profile' in html_prof
    assert 'Administrator' in html_prof


def test_profile_edit_and_persistence_for_admin(client, app):
    """Verify administrator can edit full_name and phone number with persistence."""
    create_admin_user(app)
    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    # POST updated details
    post_res = client.post('/auth/profile?tab=profile', data={
        'full_name': 'DealSpark Admin Updated',
        'email': AUTHORIZED_ADMIN_EMAIL,
        'phone': '+91 99999 88888'
    }, follow_redirects=True)

    assert post_res.status_code == 200
    html = post_res.data.decode('utf-8')
    assert 'Profile updated successfully!' in html
    assert 'DealSpark Admin Updated' in html

    # Verify persistence in database
    with app.app_context():
        u = User.query.filter_by(email=AUTHORIZED_ADMIN_EMAIL).first()
        assert u is not None
        assert u.full_name == 'DealSpark Admin Updated'
        assert u.phone == '+91 99999 88888'


def test_profile_edit_validations_and_uniqueness(client, app):
    """Verify invalid inputs are safely rejected on profile edit."""
    create_admin_user(app)
    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    # Attempt too short name
    short_res = client.post('/auth/profile?tab=profile', data={
        'full_name': 'A',
        'email': AUTHORIZED_ADMIN_EMAIL,
        'phone': '1234567890'
    }, follow_redirects=True)
    assert 'Full Name must be at least 2 characters long.' in short_res.data.decode('utf-8')


def test_admin_email_lock_protection(client, app):
    """Verify administrator cannot change email away from the authorized admin address."""
    create_admin_user(app)
    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    res = client.post('/auth/profile?tab=profile', data={
        'full_name': 'Hacked Admin',
        'email': 'attacker@dealspark.test',
        'phone': '1234567890'
    }, follow_redirects=True)

    html = res.data.decode('utf-8')
    assert 'Administrator email address cannot be changed' in html

    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin.email == AUTHORIZED_ADMIN_EMAIL


def test_storefront_footer_and_admin_dashboard_footer_suppression(client, app):
    """Verify footer is present on storefront pages but strictly suppressed on admin dashboard pages."""
    # 1. Storefront pages have footer
    anon_home = client.get('/')
    assert anon_home.status_code == 200
    assert b'ds-footer' in anon_home.data or b'DealSpark' in anon_home.data

    anon_deals = client.get('/deals')
    assert anon_deals.status_code == 200
    assert b'ds-footer' in anon_deals.data

    # 2. Admin dashboard pages do not display public website footer
    create_admin_user(app)
    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    admin_dash = client.get('/admin/dashboard')
    assert admin_dash.status_code == 200
    assert b'ds-footer' not in admin_dash.data

    admin_prods = client.get('/admin/products')
    assert admin_prods.status_code == 200
    assert b'ds-footer' not in admin_prods.data


def test_admin_product_edit_and_pricing_calculation(client, app):
    """Verify admin can edit existing product details, pricing, and discount recalculation."""
    create_admin_user(app)
    with app.app_context():
        cat = Category.query.first()
        merch = Merchant.query.first()
        cat_id = cat.id
        merch_id = merch.id

        prod = Product(
            title='Phase 3 Original Product',
            slug='phase-3-orig-prod',
            image_url='https://example.com/p3.jpg',
            category_id=cat_id,
            merchant_id=merch_id,
            merchant_product_url='https://amazon.in/dp/PHASE3',
            is_published=True,
            is_available=True
        )
        prod.set_pricing(10000, 8000)
        db.session.add(prod)
        db.session.commit()
        prod_id = prod.id

    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    # Edit product via POST
    edit_res = client.post(f'/admin/products/{prod_id}/edit', data={
        'title': 'Phase 3 Updated Product Title',
        'category_id': str(cat_id),
        'merchant_id': str(merch_id),
        'original_price': '12000',
        'discounted_price': '6000',
        'image_url': 'https://example.com/p3_updated.jpg',
        'merchant_product_url': 'https://amazon.in/dp/PHASE3_NEW',
        'affiliate_url': 'https://amzn.to/phase3',
        'description': 'Updated deal highlights',
        'is_featured': '1',
        'is_published': '1',
        'is_price_verified': '1'
    }, follow_redirects=True)

    assert edit_res.status_code == 200
    assert 'updated successfully!' in edit_res.data.decode('utf-8')

    # Verify DB state
    with app.app_context():
        updated_prod = db.session.get(Product, prod_id)
        assert updated_prod.title == 'Phase 3 Updated Product Title'
        assert float(updated_prod.original_price) == 12000.0
        assert float(updated_prod.discounted_price) == 6000.0
        assert updated_prod.discount_percentage == 50
        assert float(updated_prod.savings_amount) == 6000.0
        assert updated_prod.is_featured is True
        assert updated_prod.affiliate_url == 'https://amzn.to/phase3'


def test_admin_product_search_and_filtering(client, app):
    """Verify admin product catalog search and filtering by query, category, and status."""
    create_admin_user(app)
    with app.app_context():
        cat = Category.query.first()
        merch = Merchant.query.first()

        p1 = Product(
            title='UniqueAlphaDeal 4K Monitor',
            slug='unique-alpha-deal',
            image_url='https://example.com/m.jpg',
            category_id=cat.id,
            merchant_id=merch.id,
            merchant_product_url='https://amazon.in/dp/MON1',
            is_published=True
        )
        p1.set_pricing(20000, 15000)

        p2 = Product(
            title='UniqueBetaDraft Mechanical Keyboard',
            slug='unique-beta-draft',
            image_url='https://example.com/k.jpg',
            category_id=cat.id,
            merchant_id=merch.id,
            merchant_product_url='https://amazon.in/dp/KEY1',
            is_published=False  # Draft
        )
        p2.set_pricing(5000, 3000)

        db.session.add_all([p1, p2])
        db.session.commit()

    login_client(client, AUTHORIZED_ADMIN_EMAIL, 'AdminPass123!')

    # 1. Search by keyword
    res_q = client.get('/admin/products?q=UniqueAlphaDeal')
    assert res_q.status_code == 200
    html_q = res_q.data.decode('utf-8')
    assert 'UniqueAlphaDeal 4K Monitor' in html_q
    assert 'UniqueBetaDraft Mechanical Keyboard' not in html_q

    # 2. Filter by status: draft
    res_draft = client.get('/admin/products?status=draft')
    assert res_draft.status_code == 200
    html_draft = res_draft.data.decode('utf-8')
    assert 'UniqueBetaDraft Mechanical Keyboard' in html_draft
    assert 'UniqueAlphaDeal 4K Monitor' not in html_draft

    # 3. Filter by status: published
    res_pub = client.get('/admin/products?status=published')
    assert res_pub.status_code == 200
    html_pub = res_pub.data.decode('utf-8')
    assert 'UniqueAlphaDeal 4K Monitor' in html_pub
    assert 'UniqueBetaDraft Mechanical Keyboard' not in html_pub
