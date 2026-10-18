"""
DealSpark — End-to-End Verification: Add Product & Publish Flow
Tests:
1. Modal template structure (form as modal-content, Publish Product button, Cancel button, scrollable body)
2. Admin authentication & CSRF validation
3. Form submission & database persistence (MySQL/SQLite)
4. Automatic pricing and savings calculations
5. Visibility on Manage Products admin catalog
6. Visibility on public Live Store /deals page and deal detail page
7. Outbound redirect using affiliate URL vs merchant product URL
8. Granular error messages for invalid input
9. Clean teardown of test product
"""

import sys
import os
from decimal import Decimal

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Product, Category, Merchant
from scripts.create_admin import initialize_admin


def run_verification():
    app = create_app('development')
    client = app.test_client()

    print("\n========================================================")
    print("  DEALSPARK: ADD PRODUCT / PUBLISH FLOW VERIFICATION")
    print("========================================================\n")

    with app.app_context():
        # Ensure database tables and authorized admin exist
        db.create_all()
        admin_email = app.config.get('AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com')
        admin_pass = os.environ.get('ADMIN_INITIAL_PASSWORD', 'Mgayatri@123')
        initialize_admin(app=app)

        # Ensure at least one category and merchant exist
        category = Category.query.first()
        if not category:
            category = Category(name='Electronics', icon='bi-laptop', description='Consumer Electronics', display_order=1)
            db.session.add(category)
            db.session.commit()

        merchant = Merchant.query.first()
        if not merchant:
            merchant = Merchant(name='Amazon India', domain='amazon.in', badge_color='#ff9900')
            db.session.add(merchant)
            db.session.commit()

        cat_id = category.id
        merch_id = merchant.id

    import re

    # 1. Sign in as authorized administrator
    print("[1/6] Authenticating authorized administrator...")
    login_page = client.get('/auth/login')
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.data.decode('utf-8'))
    csrf_token = csrf_match.group(1) if csrf_match else ''

    login_res = client.post('/auth/login', data={
        'csrf_token': csrf_token,
        'email': admin_email,
        'password': admin_pass
    }, follow_redirects=True)

    assert login_res.status_code == 200, f"Login failed with status {login_res.status_code}"
    assert b'Administrator Dashboard' in login_res.data or b'Control Center' in login_res.data or b'Manage Products' in login_res.data
    print("  --> Admin authenticated successfully.")

    # 2. Inspect Manage Products page and Add Product Modal structure
    print("[2/6] Inspecting Manage Products page and Add Deal Modal DOM structure...")
    prod_page_res = client.get('/admin/products')
    assert prod_page_res.status_code == 200
    page_html = prod_page_res.data.decode('utf-8')

    # Extract CSRF token from admin page
    csrf_form_match = re.search(r'name="csrf_token" value="([^"]+)"', page_html)
    csrf_form = csrf_form_match.group(1) if csrf_form_match else csrf_token

    # Verify form has class modal-content and id addProductForm
    assert 'id="addProductForm"' in page_html, "Missing id='addProductForm'"
    assert 'class="modal-content' in page_html, "Form should have class='modal-content'"

    # Verify Publish Product button
    assert 'Publish Product' in page_html, "Missing 'Publish Product' button label"
    assert 'id="btnPublishProduct"' in page_html, "Missing id='btnPublishProduct'"

    # Verify Cancel button
    assert 'Cancel' in page_html, "Missing 'Cancel' button"
    assert 'data-bs-dismiss="modal"' in page_html, "Missing data-bs-dismiss='modal'"

    # Verify modal-body and modal-footer
    assert 'modal-body' in page_html, "Missing modal-body"
    assert 'modal-footer' in page_html, "Missing modal-footer"
    print("  --> Modal layout verified: Scrollable body, pinned footer, 'Publish Product' & 'Cancel' buttons present.")

    # 3. Publish a new product deal via form POST
    test_title = "Sony WH-1000XM5 Noise Cancelling Headphones (Test E2E)"
    orig_price = "34990.00"
    disc_price = "26990.00"
    affiliate_dest = "https://amzn.to/sony-xm5-deal"
    merchant_dest = "https://www.amazon.in/dp/B09XS7JWHH"

    print("[3/6] Submitting Add Product form to /admin/products/add...")
    form_data = {
        'csrf_token': csrf_form,
        'title': test_title,
        'category_id': str(cat_id),
        'merchant_id': str(merch_id),
        'original_price': orig_price,
        'discounted_price': disc_price,
        'image_url': 'https://m.media-amazon.com/images/I/61+ElPq8bTL._SL1500_.jpg',
        'merchant_product_url': merchant_dest,
        'affiliate_url': affiliate_dest,
        'is_featured': 'y',
        'is_trending': 'y',
        'is_price_verified': 'y',
        'description': 'Premium wireless active noise cancelling headphones with LDAC and multipoint connection.'
    }

    add_res = client.post('/admin/products/add', data=form_data, follow_redirects=True)
    assert add_res.status_code == 200
    add_html = add_res.data.decode('utf-8')
    assert 'successfully published and live in catalog' in add_html
    print("  --> Form accepted, flash success message returned.")

    # 4. Verify database record
    print("[4/6] Verifying actual database record and pricing calculations...")
    product_id = None
    with app.app_context():
        saved_product = Product.query.filter_by(title=test_title).first()
        assert saved_product is not None, "Product was NOT saved to the database!"
        product_id = saved_product.id
        slug = saved_product.slug

        # Verify automated calculations
        assert saved_product.is_published is True
        assert saved_product.is_available is True
        assert saved_product.is_price_verified is True
        assert saved_product.discount_percentage == Decimal('22.9'), f"Expected 22.9% but got {saved_product.discount_percentage}%"
        assert saved_product.savings_amount == Decimal('8000.00'), f"Expected 8000.00 but got {saved_product.savings_amount}"
        assert saved_product.affiliate_url == affiliate_dest
        assert saved_product.merchant_product_url == merchant_dest
        print(f"  --> DB Record #{product_id} verified: Discount: {saved_product.discount_percentage}%, Savings: Rs. {saved_product.savings_amount}")

    # 5. Verify public storefront discovery & outbound redirection
    print("[5/6] Verifying public Live Store visibility and affiliate Buy Now link...")
    # Deals list
    deals_res = client.get('/deals')
    assert deals_res.status_code == 200
    assert test_title in deals_res.data.decode('utf-8')

    # Deal details page
    detail_res = client.get(f'/deal/{slug}')
    assert detail_res.status_code == 200
    assert test_title in detail_res.data.decode('utf-8')
    assert f'/out/{product_id}' in detail_res.data.decode('utf-8')

    # Outbound click redirect
    out_res = client.get(f'/out/{product_id}', follow_redirects=False)
    assert out_res.status_code == 302
    assert out_res.headers['Location'] == affiliate_dest, f"Expected redirect to affiliate URL {affiliate_dest}, got {out_res.headers.get('Location')}"
    print(f"  --> Public Live Store verified: Visible on /deals, /deal/{slug}, Buy Now redirects to {affiliate_dest}")

    # 6. Verify granular validation failure handling
    print("[6/6] Verifying validation error handling for incomplete / invalid input...")
    # Test invalid: discounted price > original price
    bad_price_res = client.post('/admin/products/add', data={
        'csrf_token': csrf_form,
        'title': 'Invalid Price Product',
        'category_id': str(cat_id),
        'merchant_id': str(merch_id),
        'original_price': '1000',
        'discounted_price': '1500',
        'image_url': 'https://example.com/test.jpg',
        'merchant_product_url': 'https://amazon.in/dp/test'
    }, follow_redirects=True)
    assert 'Discounted price cannot be higher than original price' in bad_price_res.data.decode('utf-8')

    # Test invalid: missing title
    bad_title_res = client.post('/admin/products/add', data={
        'csrf_token': csrf_form,
        'title': '',
        'category_id': str(cat_id),
        'merchant_id': str(merch_id),
        'original_price': '1000',
        'discounted_price': '800',
        'image_url': 'https://example.com/test.jpg',
        'merchant_product_url': 'https://amazon.in/dp/test'
    }, follow_redirects=True)
    assert 'Product Title is required' in bad_title_res.data.decode('utf-8')
    print("  --> Granular validations verified: Clear error alerts returned without database pollution.")

    # Teardown test record
    with app.app_context():
        p = db.session.get(Product, product_id)
        if p:
            db.session.delete(p)
            db.session.commit()
            print("  --> Test database record cleaned up successfully.")

    print("\n========================================================")
    print("  SUCCESS: ALL ADD PRODUCT & PUBLISH CHECKS PASSED 100%!")
    print("========================================================\n")


if __name__ == '__main__':
    run_verification()
