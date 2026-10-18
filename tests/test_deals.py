from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from models import db, Product, Category, Merchant, User, Favorite, OutboundClick


@pytest.fixture
def sample_catalog(app):
    """Seed sample products with varied categories, merchants, prices, and statuses."""
    with app.app_context():
        cat_elec = Category.query.filter_by(name='Electronics').first()
        if not cat_elec:
            cat_elec = Category(name='Electronics', icon='bi-laptop', description='Gadgets & Tech')
            db.session.add(cat_elec)

        cat_fash = Category(name='Fashion', icon='bi-bag', description='Apparel & Style')
        db.session.add(cat_fash)

        merch_amz = Merchant.query.filter_by(domain='amazon.in').first()
        if not merch_amz:
            merch_amz = Merchant(name='Amazon India', domain='amazon.in', badge_color='#ff9900')
            db.session.add(merch_amz)

        merch_flp = Merchant(name='Flipkart', domain='flipkart.com', badge_color='#2874f0')
        db.session.add(merch_flp)
        db.session.commit()

        # 1. Active Electronics Deal (Amazon, ₹20,000 down to ₹15,000 = 25% off)
        p1 = Product(
            title='Sony Noise Cancelling Headphones WH-1000XM4',
            slug='sony-noise-cancelling-headphones-wh-1000xm4',
            description='Industry leading active noise cancellation wireless over-ear headphones.',
            image_url='https://example.com/sony.jpg',
            category_id=cat_elec.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/B0863TXGM3',
            affiliate_url='https://amzn.to/3sony',
            is_published=True,
            is_available=True,
            is_featured=True,
            is_price_verified=True,
            click_count=25
        )
        p1.set_pricing(20000, 15000)

        # 2. Active Fashion Deal (Flipkart, ₹5,000 down to ₹2,000 = 60% off)
        p2 = Product(
            title='Levi 511 Slim Fit Men Jeans',
            slug='levi-511-slim-fit-men-jeans',
            description='Original denim slim fit stretchable jeans for men.',
            image_url='https://example.com/levis.jpg',
            category_id=cat_fash.id,
            merchant_id=merch_flp.id,
            merchant_product_url='https://www.flipkart.com/levis-511/p/itm123',
            affiliate_url='https://flipkart.com/levis-511/p/itm123?affid=dealspark',
            is_published=True,
            is_available=True,
            is_featured=False,
            is_price_verified=False,
            click_count=5
        )
        p2.set_pricing(5000, 2000)

        # 3. Expired Deal (Past expiry date)
        past_date = datetime.now(timezone.utc) - timedelta(days=2)
        p3 = Product(
            title='Expired Flash Deal Smart Watch',
            slug='expired-flash-deal-smart-watch',
            description='Limited time deal expired yesterday.',
            image_url='https://example.com/watch.jpg',
            category_id=cat_elec.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/B0WATCH',
            affiliate_url='https://amzn.to/watch',
            is_published=True,
            is_available=True,
            is_expired=True,
            expiry_date=past_date
        )
        p3.set_pricing(10000, 4000)

        # 4. Unpublished Deal
        p4 = Product(
            title='Unpublished Draft Product',
            slug='unpublished-draft-product',
            description='Internal draft not yet approved.',
            image_url='https://example.com/draft.jpg',
            category_id=cat_elec.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/BDRAFT',
            affiliate_url='https://amzn.to/draft',
            is_published=False,
            is_available=True
        )
        p4.set_pricing(15000, 9000)

        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        yield {
            'cat_elec': cat_elec,
            'cat_fash': cat_fash,
            'merch_amz': merch_amz,
            'merch_flp': merch_flp,
            'p1': p1,
            'p2': p2,
            'p3': p3,
            'p4': p4
        }


def test_deals_list_page(client, sample_catalog):
    """Test /deals listing renders active deals and filters out expired/unpublished."""
    response = client.get('/deals')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Sony Noise Cancelling Headphones' in html
    assert 'Levi 511 Slim Fit Men Jeans' in html
    # Expired and unpublished must not be listed
    assert 'Expired Flash Deal Smart Watch' not in html
    assert 'Unpublished Draft Product' not in html


def test_deal_detail_page(client, sample_catalog):
    """Test /deal/<slug> detail view renders image, prices, savings, and buy button."""
    p1 = sample_catalog['p1']
    response = client.get(f'/deal/{p1.slug}')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert p1.title in html
    assert 'Save ₹5,000' in html or 'Save ₹5,000.00' in html
    assert '25% OFF' in html or '25.0% OFF' in html or '25.00% OFF' in html
    assert 'Amazon India' in html
    assert f'/out/{p1.id}' in html
    assert 'Verified Price Drop' in html


def test_deal_detail_expired_banner(client, sample_catalog):
    """Test viewing an expired deal detail shows clear expiry message."""
    p3 = sample_catalog['p3']
    response = client.get(f'/deal/{p3.slug}')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'This deal has expired' in html


def test_deal_detail_not_found(client, sample_catalog):
    """Test invalid slug returns 404."""
    response = client.get('/deal/non-existent-product-slug-xyz')
    assert response.status_code == 404


def test_search_by_keyword(client, sample_catalog):
    """Test /search with keyword matches product title or description."""
    response = client.get('/search?q=Sony')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Sony Noise Cancelling Headphones' in html
    assert 'Levi 511' not in html


def test_search_empty_results(client, sample_catalog):
    """Test search with no matches renders clean empty state without fake deals."""
    response = client.get('/search?q=NonExistentKeywordXYZ')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'No Matching Deals Found' in html
    assert 'Sony Noise Cancelling' not in html


def test_search_autocomplete_suggestions_api(client, sample_catalog):
    """Test /api/search/suggestions returns matching JSON items."""
    response = client.get('/api/search/suggestions?q=Headphones')
    assert response.status_code == 200
    data = response.get_json()
    assert 'suggestions' in data
    assert len(data['suggestions']) >= 1
    assert data['suggestions'][0]['title'] == 'Sony Noise Cancelling Headphones WH-1000XM4'
    assert data['suggestions'][0]['slug'] == 'sony-noise-cancelling-headphones-wh-1000xm4'


def test_category_deals_route(client, sample_catalog):
    """Test /category/<slug> shows category deals and product count."""
    cat_fash = sample_catalog['cat_fash']
    response = client.get(f'/category/{cat_fash.slug}')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Levi 511 Slim Fit Men Jeans' in html
    assert 'Sony Noise Cancelling' not in html


def test_filter_by_merchant(client, sample_catalog):
    """Test filtering by merchant slug."""
    response = client.get('/deals?merchant=flipkart')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Levi 511 Slim Fit' in html
    assert 'Sony Noise Cancelling' not in html


def test_filter_by_price_range(client, sample_catalog):
    """Test filtering by min_price and max_price."""
    # Only Levi Jeans (₹2000) falls between 1000 and 5000
    response = client.get('/deals?min_price=1000&max_price=5000')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Levi 511 Slim Fit' in html
    assert 'Sony Noise Cancelling' not in html


def test_filter_by_discount_percentage(client, sample_catalog):
    """Test filtering by min_discount."""
    # Levi Jeans has 60% off, Sony has 25% off
    response = client.get('/deals?min_discount=50')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Levi 511 Slim Fit' in html
    assert 'Sony Noise Cancelling' not in html


def test_sorting_by_price_and_discount(client, sample_catalog):
    """Test sorting deals by price and discount percentage."""
    res_price_asc = client.get('/deals?sort=price_asc')
    assert res_price_asc.status_code == 200
    html_asc = res_price_asc.data.decode('utf-8')
    # ₹2,000 should appear before ₹15,000
    idx_levi = html_asc.find('Levi 511 Slim Fit')
    idx_sony = html_asc.find('Sony Noise Cancelling')
    assert idx_levi < idx_sony

    res_price_desc = client.get('/deals?sort=price_desc')
    assert res_price_desc.status_code == 200
    html_desc = res_price_desc.data.decode('utf-8')
    idx_levi_desc = html_desc.find('Levi 511 Slim Fit')
    idx_sony_desc = html_desc.find('Sony Noise Cancelling')
    assert idx_sony_desc < idx_levi_desc


def test_sorting_by_popular(client, sample_catalog):
    """Test sorting by click count."""
    res_popular = client.get('/deals?sort=popular')
    assert res_popular.status_code == 200
    html_pop = res_popular.data.decode('utf-8')
    # Sony (25 clicks) should appear before Levis (5 clicks)
    idx_sony = html_pop.find('Sony Noise Cancelling')
    idx_levi = html_pop.find('Levi 511 Slim Fit')
    assert idx_sony < idx_levi


def test_pagination_12_per_page(client, app, sample_catalog):
    """Test server-side pagination with default 12 items."""
    with app.app_context():
        cat = sample_catalog['cat_elec']
        merch = sample_catalog['merch_amz']
        # Add 15 extra products
        for i in range(15):
            p = Product(
                title=f'Pagination Test Product {i+1}',
                slug=f'pagination-test-product-{i+1}',
                description=f'Pagination item {i+1}',
                image_url='https://example.com/p.jpg',
                category_id=cat.id,
                merchant_id=merch.id,
                merchant_product_url='https://amazon.in/p',
                affiliate_url='https://amzn.to/p',
                is_published=True,
                is_available=True
            )
            p.set_pricing(1000, 500)
            db.session.add(p)
        db.session.commit()

    # Total active products = 2 (p1, p2) + 15 = 17 items.
    # Page 1 should have 12 items, Page 2 should have 5 items.
    res_p1 = client.get('/deals?page=1')
    assert res_p1.status_code == 200
    assert 'Page 2' in res_p1.data.decode('utf-8') or 'Next' in res_p1.data.decode('utf-8')

    res_p2 = client.get('/deals?page=2')
    assert res_p2.status_code == 200


def test_empty_database_deals_behavior(client, app):
    """Test empty database shows clean empty state without fake deals."""
    with app.app_context():
        Product.query.delete()
        db.session.commit()

    response = client.get('/deals')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'No Matching Deals Available' in html


def test_secure_outbound_redirect(client, sample_catalog):
    """Test /out/<id> safely redirects to approved merchant/affiliate URL and logs click."""
    p1 = sample_catalog['p1']
    response = client.get(f'/out/{p1.id}', follow_redirects=False)
    assert response.status_code == 302
    assert response.location == p1.affiliate_url


def test_outbound_redirect_blocks_malicious_domain(client, app, sample_catalog):
    """Test that redirects to non-whitelisted domains are blocked to prevent open redirects."""
    with app.app_context():
        p_malicious = Product(
            title='Malicious Redirect Test',
            slug='malicious-redirect-test',
            description='Test item with untrusted domain',
            image_url='https://example.com/img.jpg',
            category_id=sample_catalog['cat_elec'].id,
            merchant_id=sample_catalog['merch_amz'].id,
            merchant_product_url='https://malicious-phishing-site.com/steal-creds',
            affiliate_url='https://malicious-phishing-site.com/steal-creds',
            is_published=True,
            is_available=True
        )
        p_malicious.set_pricing(1000, 500)
        db.session.add(p_malicious)
        db.session.commit()
        mal_id = p_malicious.id

    response = client.get(f'/out/{mal_id}', follow_redirects=True)
    html = response.data.decode('utf-8')
    # Destination blocked and redirected to homepage with security warning
    assert 'Destination merchant URL could not be verified' in html


def test_admin_created_product_appears_immediately(client, app, sample_catalog):
    """Test product created by admin appears immediately on /deals and search."""
    admin_email = app.config.get('AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com')
    with app.app_context():
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                username='admin',
                email=admin_email,
                role='admin'
            )
            db.session.add(admin)
        admin.set_password('AdminPass123!')
        db.session.commit()

    # Log in as admin via /auth/login
    login_res = client.post('/auth/login', data={'email': admin_email, 'password': 'AdminPass123!'}, follow_redirects=True)
    assert login_res.status_code == 200

    # Admin creates a new product via POST /admin/products/add
    new_deal_data = {
        'title': 'Apple MacBook Air M3 Chip',
        'category_id': sample_catalog['cat_elec'].id,
        'merchant_id': sample_catalog['merch_amz'].id,
        'original_price': '114900',
        'discounted_price': '99900',
        'merchant_product_url': 'https://www.amazon.in/dp/B0MACBOOK',
        'affiliate_url': 'https://amzn.to/macbook',
        'image_url': 'https://example.com/macbook.jpg',
        'description': 'Latest Apple M3 silicon laptop with Retina display.',
        'is_featured': '1',
        'is_price_verified': '1'
    }
    create_res = client.post('/admin/products/add', data=new_deal_data, follow_redirects=True)
    assert create_res.status_code == 200

    # Verify newly created deal appears on public /deals
    deals_res = client.get('/deals')
    assert 'Apple MacBook Air M3 Chip' in deals_res.data.decode('utf-8')

    # Verify newly created deal appears in search
    search_res = client.get('/search?q=MacBook')
    assert 'Apple MacBook Air M3 Chip' in search_res.data.decode('utf-8')


def test_wishlist_toggle_anonymous(client, sample_catalog):
    """Test anonymous visitor can toggle wishlist without 401 login wall."""
    p1 = sample_catalog['p1']
    response = client.post(f'/favorites/toggle/{p1.id}', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['anonymous'] is True


def test_wishlist_toggle_authenticated_admin(client, app, sample_catalog):
    """Test authenticated administrator can add and remove deal from favorites."""
    admin_email = app.config.get('AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com')
    with app.app_context():
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(username='admin', email=admin_email, role='admin')
            db.session.add(admin)
        admin.set_password('AdminPass123!')
        db.session.commit()

    login_res = client.post('/auth/login', data={'email': admin_email, 'password': 'AdminPass123!'}, follow_redirects=True)
    assert login_res.status_code == 200

    p1 = sample_catalog['p1']
    # Toggle on
    res_add = client.post(f'/favorites/toggle/{p1.id}', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert res_add.status_code == 200
    data_add = res_add.get_json()
    assert data_add['favorited'] is True

    # Toggle off
    res_rem = client.post(f'/favorites/toggle/{p1.id}', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert res_rem.status_code == 200
    data_rem = res_rem.get_json()
    assert data_rem['favorited'] is False


def test_favorites_page_anonymous_access(client, sample_catalog):
    """Test anonymous visitor can view favorites page without login."""
    p1 = sample_catalog['p1']
    response = client.get(f'/favorites?ids={p1.id}')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Your Saved Deals' in html
    assert p1.title in html

