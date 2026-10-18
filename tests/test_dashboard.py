import io
from datetime import datetime, timezone, timedelta
from flask import url_for
from models import db, User, Product, Category, Merchant, OutboundClick, Favorite
from services.product_service import ProductService
from services.product_import_service import ProductImportService


def create_test_admin(app):
    """Helper to initialize the authorized administrator in the test DB."""
    admin = User(
        full_name='Authorized Admin',
        username='admin',
        email='nagarajuchaintala2002@gmail.com',
        role='admin'
    )
    admin.set_password('AdminSecure123!')
    db.session.add(admin)
    db.session.commit()
    return admin


def login_admin(client):
    """Helper to authenticate as the authorized administrator."""
    return client.post('/auth/login', data={
        'email': 'nagarajuchaintala2002@gmail.com',
        'password': 'AdminSecure123!'
    }, follow_redirects=True)


def create_test_user(app):
    """Helper to create a regular user."""
    user = User(
        full_name='Regular Shopper',
        username='shopper',
        email='shopper@dealspark.test',
        role='user'
    )
    user.set_password('Shopper123!')
    db.session.add(user)
    db.session.commit()
    return user


def login_user(client):
    """Helper to authenticate as a regular user."""
    return client.post('/auth/login', data={
        'email': 'shopper@dealspark.test',
        'password': 'Shopper123!'
    }, follow_redirects=True)


def test_admin_dashboard_stats_calculation(app):
    """Test get_admin_dashboard_stats accurately reflects database metrics."""
    with app.app_context():
        cat = Category.query.first()
        merch = Merchant.query.first()

        now = datetime.now(timezone.utc)
        future = now + timedelta(days=5)
        past = now - timedelta(days=2)

        # 1. Published active product
        p1 = Product(
            title='Live Deal',
            slug='live-deal',
            image_url='https://example.com/p1.jpg',
            category_id=cat.id,
            merchant_id=merch.id,
            merchant_product_url='https://amazon.in/dp/B001',
            is_published=True,
            is_available=True,
            expiry_date=future,
            click_count=5
        )
        p1.set_pricing(1000, 600)

        # 2. Unpublished product
        p2 = Product(
            title='Draft Deal',
            slug='draft-deal',
            image_url='https://example.com/p2.jpg',
            category_id=cat.id,
            merchant_id=merch.id,
            merchant_product_url='https://amazon.in/dp/B002',
            is_published=False,
            is_available=True,
            click_count=0
        )
        p2.set_pricing(2000, 1500)

        # 3. Expired product
        p3 = Product(
            title='Expired Deal',
            slug='expired-deal',
            image_url='https://example.com/p3.jpg',
            category_id=cat.id,
            merchant_id=merch.id,
            merchant_product_url='https://amazon.in/dp/B003',
            is_published=True,
            is_available=True,
            expiry_date=past,
            click_count=3
        )
        p3.set_pricing(500, 400)

        db.session.add_all([p1, p2, p3])
        db.session.commit()

        stats = ProductService.get_admin_dashboard_stats()
        assert stats['total_products'] == 3
        assert stats['published_products'] == 2  # p1 and p3 are published
        assert stats['unpublished_products'] == 1  # p2
        assert stats['expired_deals'] == 1  # p3
        assert stats['total_categories'] >= 1
        assert stats['total_merchants'] >= 1
        assert stats['total_clicks'] == 8  # 5 + 0 + 3


def test_admin_dashboard_views_authorized(client, app):
    """Test authorized administrator can view all admin dashboard views."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    # 1. Overview
    res_dash = client.get('/admin/dashboard')
    assert res_dash.status_code == 200
    assert b'Welcome back' in res_dash.data
    assert b'Total Products' in res_dash.data

    # 2. Products
    res_prod = client.get('/admin/products')
    assert res_prod.status_code == 200
    assert b'All Products Catalog' in res_prod.data

    # 3. Deals
    res_deals = client.get('/admin/deals')
    assert res_deals.status_code == 200
    assert b'Published Active Deals' in res_deals.data

    # 4. Categories
    res_cat = client.get('/admin/categories')
    assert res_cat.status_code == 200
    assert b'Taxonomy &amp; Product Categories' in res_cat.data or b'Taxonomy & Product Categories' in res_cat.data

    # 5. Merchants
    res_merch = client.get('/admin/merchants')
    assert res_merch.status_code == 200
    assert b'Partner Merchants' in res_merch.data

    # 6. Analytics
    res_ana = client.get('/admin/analytics')
    assert res_ana.status_code == 200
    assert b'Outbound Clicks' in res_ana.data


def test_unauthorized_user_blocked_from_admin_and_api(client, app):
    """Test unauthenticated visitors and non-admin users are blocked from admin routes and APIs."""
    # 1. Anonymous visitor accessing admin dashboard is redirected to admin login
    res = client.get('/admin/dashboard')
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']

    # 2. Direct admin login URL redirects to auth login
    res_login = client.get('/admin/login')
    assert res_login.status_code == 302
    assert '/auth/login' in res_login.headers['Location']

    # 3. Non-admin user credentials submitted to login portal are strictly rejected with 401
    with app.app_context():
        user = create_test_user(app)

    login_attempt = client.post('/auth/login', data={
        'email': 'shopper@dealspark.test',
        'password': 'Shopper123!'
    })
    assert login_attempt.status_code == 401
    assert b'Invalid administrator credentials' in login_attempt.data

    # 4. APIs are protected against unauthorized access
    res_api = client.post('/admin/api/products/import-url', json={'url': 'https://amazon.in/dp/test'})
    assert res_api.status_code in (302, 401, 403)

    res_up = client.post('/admin/api/products/upload-image', data={'image': (io.BytesIO(b'dummy'), 'test.png')})
    assert res_up.status_code in (302, 401, 403)


def test_visitor_redirected_from_profile_and_admin_profile_access(client, app):
    """Test visitors are redirected from /auth/profile to homepage, while admin can access profile."""
    # 1. Anonymous visitor is redirected to login
    res_anon = client.get('/auth/profile')
    assert res_anon.status_code == 302
    assert '/auth/login' in res_anon.headers['Location']

    # 2. Administrator accesses profile
    with app.app_context():
        create_test_admin(app)

    login_admin(client)
    res_admin = client.get('/auth/profile?tab=profile')
    assert res_admin.status_code == 200
    assert b'Administrator Profile' in res_admin.data


def test_api_import_product_url(client, app):
    """Test /admin/api/products/import-url with shopping URLs."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    # 1. Missing URL
    res_empty = client.post('/admin/api/products/import-url', json={'url': ''})
    assert res_empty.status_code == 400
    assert res_empty.json['success'] is False

    # 2. Amazon URL parsing
    test_url = 'https://www.amazon.in/Sony-WH-1000XM5-Wireless-Cancelling-Headphones/dp/B09XS7JWHH'
    res_import = client.post('/admin/api/products/import-url', json={'url': test_url})
    assert res_import.status_code == 200
    data = res_import.json
    assert data['success'] is True
    assert 'merchant_name' in data['data']
    assert data['data']['merchant_name'] == 'Amazon India'
    assert 'Sony' in data['data']['title']


def test_api_upload_product_image(client, app):
    """Test /admin/api/products/upload-image validates file types and returns uploaded path."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    # 1. Disallowed extension
    data_bad = {
        'image': (io.BytesIO(b'malicious script'), 'bad_file.sh')
    }
    res_bad = client.post('/admin/api/products/upload-image', data=data_bad, content_type='multipart/form-data')
    assert res_bad.status_code == 400
    assert res_bad.json['success'] is False

    # 2. Valid image upload
    fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
    data_good = {
        'image': (io.BytesIO(fake_png), 'test_product.png')
    }
    res_good = client.post('/admin/api/products/upload-image', data=data_good, content_type='multipart/form-data')
    assert res_good.status_code == 200
    assert res_good.json['success'] is True
    assert '/static/uploads/products/' in res_good.json['image_url']


def test_admin_add_product_with_image_upload_and_auto_discount(client, app):
    """Test adding a product with an uploaded image file and automatic discount calculation."""
    with app.app_context():
        create_test_admin(app)
        cat = Category.query.first()
        merch = Merchant.query.first()
        cat_id = cat.id
        merch_id = merch.id

    login_admin(client)

    fake_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'
    form_data = {
        'title': 'Apple MacBook Pro M3',
        'category_id': str(cat_id),
        'merchant_id': str(merch_id),
        'original_price': '199900',
        'discounted_price': '169900',
        'image_url': 'https://example.com/fallback.jpg',
        'merchant_product_url': 'https://amazon.in/dp/B0CX234',
        'affiliate_url': 'https://amzn.to/m3pro',
        'is_featured': 'y',
        'is_price_verified': 'y',
        'description': 'Latest M3 chip laptop.',
        'image_file': (io.BytesIO(fake_jpg), 'macbook.jpg')
    }

    res = client.post('/admin/products/add', data=form_data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b'Apple MacBook Pro M3' in res.data

    with app.app_context():
        product = Product.query.filter_by(title='Apple MacBook Pro M3').first()
        assert product is not None
        assert product.discount_percentage == 15  # (199900-169900)/199900 = 15.01% -> 15%
        assert product.savings == 30000.0
        assert '/static/uploads/products/' in product.image_url
        assert product.is_featured is True
        assert product.is_price_verified is True


def test_api_import_flipkart_url(client, app):
    """Test importing product metadata from supported Flipkart URLs."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    flipkart_url = 'https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W'
    res = client.post('/admin/api/products/import-url', json={'url': flipkart_url})
    assert res.status_code == 200
    data = res.json
    assert data['success'] is True
    assert data['data']['merchant_name'] == 'Flipkart'
    assert data['data']['product_id'] == 'MOBGTAGPTB3VS24W'
    assert 'Apple' in data['data']['title'] or 'Iphone' in data['data']['title']


def test_api_import_unsupported_domain_rejected(client, app):
    """Test unsupported merchant shopping domains are securely rejected with 400."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    res = client.post('/admin/api/products/import-url', json={'url': 'https://random-store.com/deal-item'})
    assert res.status_code == 400
    assert res.json['success'] is False
    assert 'Unsupported merchant domain' in res.json['error']


def test_api_import_ssrf_ip_blocked(client, app):
    """Test SSRF attack vectors (localhost, internal IP ranges) are blocked."""
    with app.app_context():
        create_test_admin(app)

    login_admin(client)

    for evil_url in [
        'http://127.0.0.1:5000/secret',
        'http://localhost/admin',
        'http://169.254.169.254/latest/meta-data',
        'http://10.0.0.1/internal'
    ]:
        res = client.post('/admin/api/products/import-url', json={'url': evil_url})
        assert res.status_code == 400
        assert res.json['success'] is False


def test_api_import_amazon_with_official_paapi_mock(client, app, monkeypatch):
    """Test full automatic import parsing when Amazon PA-API 5.0 returns official JSON data."""
    from services.product_import_service import AmazonIndiaProvider

    mock_paapi_response = {
        "ItemsResult": {
            "Items": [{
                "ASIN": "B09XS7JWHH",
                "ItemInfo": {
                    "Title": {"DisplayValue": "Sony WH-1000XM5 Wireless Industry Leading Noise Cancelling Headphones"},
                    "Features": {"DisplayValues": ["Auto NC Optimizer", "Up to 30-hour battery life", "Ultra-comfortable lightweight design"]},
                    "Classifications": {"ProductGroup": {"DisplayValue": "Electronics"}}
                },
                "Images": {
                    "Primary": {
                        "Large": {"URL": "https://m.media-amazon.com/images/I/61+ElTDEWLL._SL1500_.jpg"}
                    }
                },
                "Offers": {
                    "Listings": [{
                        "Price": {"Amount": 26990.0, "DisplayAmount": "₹26,990.00"},
                        "SavingBasis": {"Amount": 34990.0, "DisplayAmount": "₹34,990.00"}
                    }]
                }
            }]
        }
    }

    monkeypatch.setattr(AmazonIndiaProvider, "_aws_sigv4_request", lambda *args, **kwargs: mock_paapi_response)

    with app.app_context():
        create_test_admin(app)
        app.config['AMAZON_PAAPI_ACCESS_KEY'] = 'TEST_KEY'
        app.config['AMAZON_PAAPI_SECRET_KEY'] = 'TEST_SECRET'
        app.config['AMAZON_ASSOCIATE_TAG'] = 'dealspark0e-21'

    login_admin(client)

    test_url = 'https://www.amazon.in/dp/B09XS7JWHH'
    res = client.post('/admin/api/products/import-url', json={'url': test_url})
    assert res.status_code == 200
    data = res.json
    assert data['success'] is True
    d = data['data']
    assert d['is_api_verified'] is True
    assert 'Sony WH-1000XM5' in d['title']
    assert d['original_price'] == '34990.00'
    assert d['discounted_price'] == '26990.00'
    assert d['savings_amount'] == '8000.00'
    assert d['discount_percentage'] == 23
    assert 'https://m.media-amazon.com/' in d['image_url']
    assert 'tag=dealspark0e-21' in d['affiliate_url']
    assert 'Auto NC Optimizer' in d['description']

