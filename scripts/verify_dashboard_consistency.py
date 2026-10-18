"""
Script to verify complete UI/UX consistency across DealSpark authenticated pages.
Verifies:
1. No public footer on any authenticated page (User Dashboard, Admin Dashboard,
   Favorites, Change Password, Manage Products, Deals, Categories, Merchants, Analytics).
2. Public footer is preserved on public pages (/, /deals, /about, /disclaimer).
3. /dashboard universal redirect behavior.
4. User Dashboard elements (hero banner, 4 stat cards, category pills, favorites, featured deals).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Product, Category, Merchant, Favorite

def run_verification():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Setup test data
        admin_email = 'nagarajuchaintala2002@gmail.com'
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                full_name='Authorized Admin',
                username='admin',
                email=admin_email,
                role='admin'
            )
            admin.set_password('AdminSecure123!')
            db.session.add(admin)

        user_email = 'shopper@dealspark.test'
        user = User.query.filter_by(email=user_email).first()
        if not user:
            user = User(
                full_name='Regular Shopper',
                username='shopper',
                email=user_email,
                role='user'
            )
            user.set_password('Shopper123!')
            db.session.add(user)

        cat = Category.query.first()
        merch = Merchant.query.first()
        test_deal = Product.query.first()
        if not test_deal and cat and merch:
            test_deal = Product(
                title='Test Deal 1',
                slug='test-deal-1',
                image_url='https://example.com/test.jpg',
                category_id=cat.id,
                merchant_id=merch.id,
                merchant_product_url='https://amazon.in/dp/B001',
                is_published=True,
                is_available=True
            )
            test_deal.set_pricing(2000, 1000)
            db.session.add(test_deal)

        db.session.commit()

        client = app.test_client()

        print("\n--- 1. Testing Public Pages (Must Have Public Footer) ---")
        for pub_url in ['/', '/deals', '/about', '/disclaimer']:
            resp = client.get(pub_url)
            assert resp.status_code == 200, f"Expected 200 on {pub_url}, got {resp.status_code}"
            assert b'ds-footer' in resp.data, f"Expected ds-footer on public page {pub_url}"
            print(f"  [PASS] {pub_url} status=200, public footer present.")

        print("\n--- 2. Testing Unauthenticated /dashboard Redirect ---")
        dash_anon = client.get('/dashboard')
        assert dash_anon.status_code == 302, f"Expected redirect, got {dash_anon.status_code}"
        assert '/auth/login' in dash_anon.headers['Location']
        print(f"  [PASS] Anonymous /dashboard redirects to /auth/login")

        print("\n--- 3. Testing Regular Shopper Authenticated Pages ---")
        login_resp = client.post('/auth/login', data={
            'email': user_email,
            'password': 'Shopper123!'
        })
        assert login_resp.status_code == 302, f"Login failed with status {login_resp.status_code}"
        assert '/auth/profile' in login_resp.headers['Location'], f"Expected redirect to /auth/profile, got {login_resp.headers['Location']}"
        print(f"  [PASS] Regular user login redirects to /auth/profile")

        shopper_urls = [
            ('/dashboard', 302, '/auth/profile'),
            ('/auth/profile', 200, None),
            ('/auth/profile?tab=profile', 200, None),
            ('/favorites', 200, None),
            ('/auth/change-password', 200, None),
        ]

        for path, expected_status, redirect_target in shopper_urls:
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code == expected_status, f"Expected {expected_status} for {path}, got {resp.status_code}"
            if redirect_target:
                assert redirect_target in resp.headers['Location']
                print(f"  [PASS] {path} redirects to {redirect_target}")
            else:
                assert b'ds-dashboard-wrapper' in resp.data, f"Missing ds-dashboard-wrapper in {path}"
                assert b'ds-dashboard-sidebar' in resp.data, f"Missing ds-dashboard-sidebar in {path}"
                assert b'ds-footer' not in resp.data, f"Public footer found in authenticated page {path}!"
                print(f"  [PASS] {path} status=200, uses dashboard layout, NO public footer.")

        # Inspect User Dashboard contents
        prof_resp = client.get('/auth/profile')
        assert b'Welcome back, Regular Shopper' in prof_resp.data
        assert b'Saved Favorites' in prof_resp.data
        assert b'Live Deals Available' in prof_resp.data
        assert b'Deal Categories' in prof_resp.data
        assert b'Browse Deals by Category' in prof_resp.data
        print(f"  [PASS] User Dashboard contains all required metric cards, greeting, and category pills.")

        print("\n--- 4. Testing Administrator Authenticated Pages ---")
        # Logout user
        client.get('/auth/logout')

        # Login admin
        admin_login = client.post('/auth/login', data={
            'email': admin_email,
            'password': 'AdminSecure123!'
        })
        assert admin_login.status_code == 302
        assert '/admin/dashboard' in admin_login.headers['Location']
        print(f"  [PASS] Admin login redirects to /admin/dashboard")

        admin_urls = [
            ('/dashboard', 302, '/admin/dashboard'),
            ('/admin/dashboard', 200, None),
            ('/admin/products', 200, None),
            ('/admin/deals', 200, None),
            ('/admin/categories', 200, None),
            ('/admin/merchants', 200, None),
            ('/admin/analytics', 200, None),
            ('/auth/change-password', 200, None),
        ]

        for path, expected_status, redirect_target in admin_urls:
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code == expected_status, f"Expected {expected_status} for {path}, got {resp.status_code}"
            if redirect_target:
                assert redirect_target in resp.headers['Location']
                print(f"  [PASS] Admin {path} redirects to {redirect_target}")
            else:
                assert b'ds-dashboard-wrapper' in resp.data, f"Missing ds-dashboard-wrapper in {path}"
                assert b'ds-dashboard-sidebar' in resp.data, f"Missing ds-dashboard-sidebar in {path}"
                assert b'ds-footer' not in resp.data, f"Public footer found in authenticated admin page {path}!"
                print(f"  [PASS] Admin {path} status=200, uses dashboard layout, NO public footer.")

        print("\n=== ALL DASHBOARD UI/UX CONSISTENCY VERIFICATIONS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_verification()
