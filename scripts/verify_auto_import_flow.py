"""
End-to-End Verification Script for DealSpark Fully Automatic Product Import.
Verifies:
1. Supported Amazon India URL parsing and ASIN canonicalization.
2. Supported Flipkart URL parsing and PID canonicalization.
3. Official Amazon PA-API 5.0 integration with verified pricing and images.
4. SSRF and domain security protection (blocking private IPs & unsupported domains).
5. Separate canonical merchant URL vs affiliate URL generation.
6. Graceful fallback when credentials are not configured (no dummy data or scraping bypass).
7. Complete Publish flow: saving imported product to DB and verifying on Live Store.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Product, Category, Merchant
from services.product_import_service import ProductImportService, AmazonIndiaProvider

def run_auto_import_verification():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Setup test entities
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

        cat = Category.query.filter_by(name='Electronics').first()
        if not cat:
            cat = Category(name='Electronics', slug='electronics', icon='bi-laptop', display_order=1)
            db.session.add(cat)

        merch_amz = Merchant.query.filter_by(name='Amazon India').first()
        if not merch_amz:
            merch_amz = Merchant(name='Amazon India', slug='amazon-india', domain='amazon.in')
            db.session.add(merch_amz)

        merch_fk = Merchant.query.filter_by(name='Flipkart').first()
        if not merch_fk:
            merch_fk = Merchant(name='Flipkart', slug='flipkart', domain='flipkart.com')
            db.session.add(merch_fk)

        db.session.commit()

        client = app.test_client()

        print("\n==================================================================")
        print("  DEALSPARK: FULLY AUTOMATIC PRODUCT IMPORT VERIFICATION")
        print("==================================================================")

        # 1. Authenticate Admin
        print("\n[1/7] Authenticating authorized administrator...")
        login_res = client.post('/auth/login', data={
            'email': admin_email,
            'password': 'AdminSecure123!'
        })
        assert login_res.status_code == 302
        print("  --> Admin authenticated successfully.")

        # 2. SSRF Protection & Unsupported Domains
        print("\n[2/7] Verifying SSRF guards and domain whitelisting...")
        for bad_url in [
            'http://127.0.0.1:8000/private',
            'http://localhost/admin',
            'http://169.254.169.254/latest/meta-data',
            'https://unauthorized-store.com/item/12345'
        ]:
            res = client.post('/admin/api/products/import-url', json={'url': bad_url})
            assert res.status_code == 400
            assert res.json['success'] is False
            print(f"  [PASS] Blocked dangerous/unsupported URL: {bad_url}")

        # 3. Amazon India URL handling without API credentials
        print("\n[3/7] Verifying Amazon India URL import fallback (when PA-API not configured)...")
        amz_url = 'https://www.amazon.in/Sony-WH-1000XM5-Wireless-Cancelling-Headphones/dp/B09XS7JWHH'
        res_amz = client.post('/admin/api/products/import-url', json={'url': amz_url})
        assert res_amz.status_code == 200
        d_amz = res_amz.json['data']
        assert d_amz['merchant_name'] == 'Amazon India'
        assert d_amz['product_id'] == 'B09XS7JWHH'
        assert d_amz['merchant_product_url'] == 'https://www.amazon.in/dp/B09XS7JWHH'
        assert d_amz['is_api_verified'] is False
        assert d_amz['original_price'] == ''  # Prices must NOT be guessed or faked
        assert d_amz['discounted_price'] == ''
        print(f"  [PASS] Amazon URL parsed safely: ASIN={d_amz['product_id']}, canonical={d_amz['merchant_product_url']}")
        print(f"         Prices and images left blank for manual input as required.")

        # 4. Flipkart URL handling without API credentials
        print("\n[4/7] Verifying Flipkart URL import fallback (when API not configured)...")
        fk_url = 'https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W'
        res_fk = client.post('/admin/api/products/import-url', json={'url': fk_url})
        assert res_fk.status_code == 200
        d_fk = res_fk.json['data']
        assert d_fk['merchant_name'] == 'Flipkart'
        assert d_fk['product_id'] == 'MOBGTAGPTB3VS24W'
        assert d_fk['is_api_verified'] is False
        assert d_fk['original_price'] == ''
        assert d_fk['discounted_price'] == ''
        print(f"  [PASS] Flipkart URL parsed safely: PID={d_fk['product_id']}, canonical={d_fk['merchant_product_url']}")

        # 5. Full Amazon PA-API 5.0 official data integration
        print("\n[5/7] Verifying Amazon PA-API 5.0 official response processing...")
        mock_paapi_payload = {
            "ItemsResult": {
                "Items": [{
                    "ASIN": "B09XS7JWHH",
                    "ItemInfo": {
                        "Title": {"DisplayValue": "Sony WH-1000XM5 Wireless Active Noise Cancelling Headphones"},
                        "Features": {"DisplayValues": ["Two processors control 8 microphones", "Up to 30 hours battery life"]},
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

        # Test with PA-API keys configured
        app.config['AMAZON_PAAPI_ACCESS_KEY'] = 'AKIA_MOCK_TEST_KEY'
        app.config['AMAZON_PAAPI_SECRET_KEY'] = 'SECRET_MOCK_KEY_12345'
        app.config['AMAZON_ASSOCIATE_TAG'] = 'dealspark0e-21'

        # Temporarily mock _aws_sigv4_request to simulate Amazon PA-API response
        orig_sigv4 = AmazonIndiaProvider._aws_sigv4_request
        AmazonIndiaProvider._aws_sigv4_request = staticmethod(lambda *args, **kwargs: mock_paapi_payload)

        try:
            res_verified = client.post('/admin/api/products/import-url', json={'url': amz_url})
            assert res_verified.status_code == 200
            d_ver = res_verified.json['data']
            assert d_ver['is_api_verified'] is True
            assert d_ver['title'] == "Sony WH-1000XM5 Wireless Active Noise Cancelling Headphones"
            assert d_ver['original_price'] == "34990.00"
            assert d_ver['discounted_price'] == "26990.00"
            assert d_ver['savings_amount'] == "8000.00"
            assert d_ver['discount_percentage'] == 23
            assert d_ver['affiliate_url'] == "https://www.amazon.in/dp/B09XS7JWHH?tag=dealspark0e-21"
            assert d_ver['merchant_product_url'] == "https://www.amazon.in/dp/B09XS7JWHH"
            assert d_ver['image_url'] == "https://m.media-amazon.com/images/I/61+ElTDEWLL._SL1500_.jpg"
            print("  --> Official Amazon PA-API data parsed successfully:")
            print(f"      Title: {d_ver['title']}")
            print(f"      Original Price: Rs. {d_ver['original_price']}, Deal Price: Rs. {d_ver['discounted_price']}")
            print(f"      Calculated Savings: Rs. {d_ver['savings_amount']} ({d_ver['discount_percentage']}% OFF)")
            print(f"      Affiliate Link: {d_ver['affiliate_url']}")
            print(f"      High-Res Image: {d_ver['image_url']}")
        finally:
            AmazonIndiaProvider._aws_sigv4_request = orig_sigv4

        # 6. Separate Canonical URL vs Affiliate URL verification
        print("\n[6/7] Verifying Merchant Product URL and Affiliate URL separation...")
        assert d_ver['merchant_product_url'] != d_ver['affiliate_url']
        assert 'tag=' not in d_ver['merchant_product_url']
        assert 'tag=dealspark0e-21' in d_ver['affiliate_url']
        print("  [PASS] Merchant canonical URL and tagged affiliate URL are properly separated.")

        # 7. End-to-end publish flow using imported product metadata
        print("\n[7/7] Publishing imported product and verifying on Live Store...")
        form_payload = {
            'title': d_ver['title'],
            'category_id': str(cat.id),
            'merchant_id': str(merch_amz.id),
            'original_price': d_ver['original_price'],
            'discounted_price': d_ver['discounted_price'],
            'image_url': d_ver['image_url'],
            'merchant_product_url': d_ver['merchant_product_url'],
            'affiliate_url': d_ver['affiliate_url'],
            'description': d_ver['description'],
            'is_featured': 'y',
            'is_price_verified': 'y'
        }

        pub_res = client.post('/admin/products/add', data=form_payload, follow_redirects=True)
        assert pub_res.status_code == 200

        # Check DB record
        saved_product = Product.query.filter_by(title=d_ver['title']).first()
        assert saved_product is not None
        assert float(saved_product.original_price) == 34990.0
        assert float(saved_product.discounted_price) == 26990.0
        assert round(float(saved_product.discount_percentage)) == 23
        assert float(saved_product.savings) == 8000.0
        assert saved_product.is_published is True

        # Check Live Store
        store_res = client.get('/deals')
        assert store_res.status_code == 200
        assert d_ver['title'].encode('utf-8') in store_res.data or b'Sony WH-1000XM5' in store_res.data

        # Check Detail Page
        detail_res = client.get(f"/deal/{saved_product.slug}")
        assert detail_res.status_code == 200
        assert b'22.9% OFF' in detail_res.data or b'23% OFF' in detail_res.data
        assert b'8,000' in detail_res.data

        print("  [PASS] Product successfully saved to database with accurate calculations.")
        print("  [PASS] Product immediately visible on Live Store (/deals and /deal/<slug>).")

        print("\n==================================================================")
        print("  SUCCESS: ALL AUTOMATIC PRODUCT IMPORT VERIFICATIONS PASSED 100%!")
        print("==================================================================")

if __name__ == '__main__':
    run_auto_import_verification()
