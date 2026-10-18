def test_homepage_status_200(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'DealSpark' in response.data
    assert b'Never Pay Full Price Again' in response.data


def test_homepage_renders_categories(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Electronics' in response.data


def test_homepage_empty_state_without_fake_deals(client):
    response = client.get('/')
    assert response.status_code == 200
    # Checks for clean empty state prompt rather than fabricated deals
    assert b'No Featured Deals Published Yet' in response.data


def test_about_page(client):
    response = client.get('/about')
    assert response.status_code == 200
    assert b'About DealSpark' in response.data


def test_disclaimer_page(client):
    response = client.get('/disclaimer')
    assert response.status_code == 200
    assert b'Affiliate &amp; Pricing Disclaimer' in response.data or b'Affiliate & Pricing Disclaimer' in response.data


def test_search_page(client):
    response = client.get('/search?q=laptop')
    assert response.status_code == 200
    assert b'Search Results' in response.data
