from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from models import db, Product, Category, Merchant, User
from services.product_service import ProductService


@pytest.fixture
def phase5_catalog(app):
    """Seed test data for Phase 5 tests."""
    with app.app_context():
        # Categories
        cat_audio = Category.query.filter_by(name='Audio & Headphones').first()
        if not cat_audio:
            cat_audio = Category(name='Audio & Headphones', slug='audio-headphones', icon='bi-headphones', description='Audio Gear')
            db.session.add(cat_audio)

        cat_fashion = Category.query.filter_by(name='Ethnic Wear').first()
        if not cat_fashion:
            cat_fashion = Category(name='Ethnic Wear', slug='ethnic-wear', icon='bi-bag-heart', description='Traditional clothing')
            db.session.add(cat_fashion)

        merch_amz = Merchant.query.filter_by(domain='amazon.in').first()
        if not merch_amz:
            merch_amz = Merchant(name='Amazon India', domain='amazon.in', badge_color='#ff9900')
            db.session.add(merch_amz)

        merch_myntra = Merchant.query.filter_by(domain='myntra.com').first()
        if not merch_myntra:
            merch_myntra = Merchant(name='Myntra', domain='myntra.com', badge_color='#ff3f6c')
            db.session.add(merch_myntra)

        db.session.commit()

        # Product 1: Sony WH-1000XM5 Headphones
        p1 = Product(
            title='Sony WH-1000XM5 Noise Cancelling Headphones',
            slug='sony-wh-1000xm5-noise-cancelling-headphones',
            description='Flagship wireless ANC headphones with 30-hour battery life.',
            image_url='https://example.com/sony5.jpg',
            category_id=cat_audio.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/B09XS7JWHH',
            affiliate_url='https://amzn.to/3sony5',
            is_published=True,
            is_available=True,
            is_featured=True,
            is_price_verified=True,
            click_count=50
        )
        p1.set_pricing(29990, 24990)

        # Product 2: Bose QuietComfort Headphones (Related to p1 in audio)
        p2 = Product(
            title='Bose QuietComfort Wireless Headphones',
            slug='bose-quietcomfort-wireless-headphones',
            description='Legendary noise cancellation and all-day comfort.',
            image_url='https://example.com/bose.jpg',
            category_id=cat_audio.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/B0BOSENCR',
            affiliate_url='https://amzn.to/boseqc',
            is_published=True,
            is_available=True,
            is_featured=False,
            is_price_verified=True,
            click_count=30
        )
        p2.set_pricing(32900, 22900)

        # Product 3: Anouk Women Printed Cotton Kurti
        p3 = Product(
            title='Anouk Women Floral Printed Straight Cotton Kurti',
            slug='anouk-women-floral-printed-straight-cotton-kurti',
            description='Beautiful floral print cotton straight kurti for everyday styling.',
            image_url='https://example.com/kurti.jpg',
            category_id=cat_fashion.id,
            merchant_id=merch_myntra.id,
            merchant_product_url='https://www.myntra.com/kurtis/anouk/1234',
            affiliate_url='https://myntra.com/kurtis/anouk/1234?affid=dealspark',
            is_published=True,
            is_available=True,
            is_featured=True,
            is_price_verified=False,
            click_count=15
        )
        p3.set_pricing(1999, 699)

        # Product 4: Expired Audio Product (should never appear in related deals)
        p4 = Product(
            title='Expired Audio Headset Deal',
            slug='expired-audio-headset-deal',
            description='Old flash discount on headset.',
            image_url='https://example.com/expired.jpg',
            category_id=cat_audio.id,
            merchant_id=merch_amz.id,
            merchant_product_url='https://www.amazon.in/dp/B0EXPIRED',
            is_published=True,
            is_available=True,
            is_expired=True,
            expiry_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        p4.set_pricing(4999, 1999)

        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        yield {
            'cat_audio': cat_audio,
            'cat_fashion': cat_fashion,
            'p1': p1,
            'p2': p2,
            'p3': p3,
            'p4': p4
        }


def test_detail_page_suppresses_footer_and_shows_related(client, phase5_catalog):
    """
    CRITICAL REQUIREMENT TEST:
    Verifies that the large public footer (<footer class="ds-footer">) is completely
    suppressed on the product detail page, while the rich related products section is rendered.
    """
    p1 = phase5_catalog['p1']
    response = client.get(f'/deal/{p1.slug}')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    # Footer must NOT be present on the detail page
    assert '<footer class="ds-footer">' not in html
    assert 'DealSpark is India\'s premier deals discovery portal' not in html

    # Related deals section must be present
    assert 'id="related-deals-section"' in html or 'Related Deals' in html
    # Bose headphones should appear as related deal to Sony headphones
    assert 'Bose QuietComfort Wireless Headphones' in html


def test_homepage_renders_footer_and_hero(client, phase5_catalog):
    """Verifies that the homepage still renders the public footer, hero search, and category cards."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    # Footer MUST be present on homepage
    assert '<footer class="ds-footer">' in html
    assert 'DealSpark is India\'s premier deals discovery portal' in html

    # Hero section with prominent search must be present
    assert 'id="heroSearchInput"' in html
    assert 'id="heroSuggestionsBox"' in html
    assert 'Never Pay Full Price Again with' in html

    # Shop by category section must be present
    assert 'Shop by Category' in html
    assert 'Audio &amp; Headphones' in html or 'Audio & Headphones' in html


def test_search_autocomplete_includes_categories_and_deals(client, phase5_catalog):
    """Verifies /api/search/suggestions returns matching categories alongside products."""
    response = client.get('/api/search/suggestions?q=Audio')
    assert response.status_code == 200
    data = response.get_json()

    assert 'suggestions' in data
    assert 'categories' in data

    # Matching category
    cat_matches = [c for c in data['categories'] if c['name'] == 'Audio & Headphones']
    assert len(cat_matches) == 1
    assert cat_matches[0]['slug'] == 'audio-headphones'
    assert 'deals_count' in cat_matches[0]


def test_related_deals_relevance_algorithm(client, phase5_catalog, app):
    """Verifies relevance scoring: category match, keyword matching, and exclusion of self/expired."""
    with app.app_context():
        p1 = phase5_catalog['p1']
        related = ProductService.get_related_deals(p1, limit=4)

        # 1. Product itself must never be in related
        related_ids = [r.id for r in related]
        assert p1.id not in related_ids

        # 2. Expired deal (p4) must never be in related
        p4 = phase5_catalog['p4']
        assert p4.id not in related_ids

        # 3. Bose headphones (same category + title keyword "Headphones") must be included
        p2 = phase5_catalog['p2']
        assert p2.id in related_ids


def test_related_deals_dynamic_headings(phase5_catalog, app):
    """Verifies contextual dynamic headings based on product type / category."""
    with app.app_context():
        p1 = phase5_catalog['p1']
        heading1 = ProductService.get_related_deals_heading(p1)
        assert 'Headphones' in heading1 or 'Audio' in heading1

        p3 = phase5_catalog['p3']
        heading3 = ProductService.get_related_deals_heading(p3)
        assert 'Kurtis' in heading3 or 'Ethnic Wear' in heading3
