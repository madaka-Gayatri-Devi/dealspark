import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import db, Category, Merchant


def run_seed():
    db.create_all()

    # Baseline Categories (Standard e-commerce categories)
    initial_categories = [
        {'name': 'Electronics', 'icon': 'bi-laptop', 'description': 'Laptops, headphones, cameras and smart gadgets', 'order': 1},
        {'name': 'Mobiles & Accessories', 'icon': 'bi-phone', 'description': 'Smartphones, cases, chargers and power banks', 'order': 2},
        {'name': 'Fashion & Clothing', 'icon': 'bi-bag', 'description': 'Men, women and kids apparel and footwear', 'order': 3},
        {'name': 'Home & Kitchen', 'icon': 'bi-house-door', 'description': 'Home appliances, cookware, furniture and decor', 'order': 4},
        {'name': 'Beauty & Grooming', 'icon': 'bi-stars', 'description': 'Skincare, perfumes, hair care and wellness', 'order': 5},
        {'name': 'Footwear', 'icon': 'bi-activity', 'description': 'Casual shoes, sneakers, formal shoes and sandals', 'order': 6},
        {'name': 'Audio & Headphones', 'icon': 'bi-headphones', 'description': 'TWS earbuds, noise cancelling headphones & speakers', 'order': 7},
        {'name': 'Smart Watches & Bands', 'icon': 'bi-smartwatch', 'description': 'Fitness trackers, smartwatches & luxury watches', 'order': 8},
    ]

    for cat_data in initial_categories:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        if not existing:
            cat = Category(
                name=cat_data['name'],
                icon=cat_data['icon'],
                description=cat_data['description'],
                display_order=cat_data['order']
            )
            db.session.add(cat)

    # Baseline Verified Merchants
    initial_merchants = [
        {'name': 'Amazon India', 'domain': 'amazon.in', 'badge_color': '#ff9900', 'logo_url': ''},
        {'name': 'Flipkart', 'domain': 'flipkart.com', 'badge_color': '#2874f0', 'logo_url': ''},
        {'name': 'Myntra', 'domain': 'myntra.com', 'badge_color': '#ff3f6c', 'logo_url': ''},
        {'name': 'Ajio', 'domain': 'ajio.com', 'badge_color': '#2c4152', 'logo_url': ''},
        {'name': 'Croma', 'domain': 'croma.com', 'badge_color': '#00e9bf', 'logo_url': ''},
        {'name': 'Tata CLiQ', 'domain': 'tatacliq.com', 'badge_color': '#000000', 'logo_url': ''},
    ]

    for merch_data in initial_merchants:
        existing = Merchant.query.filter_by(name=merch_data['name']).first()
        if not existing:
            merch = Merchant(
                name=merch_data['name'],
                domain=merch_data['domain'],
                badge_color=merch_data['badge_color'],
                logo_url=merch_data['logo_url']
            )
            db.session.add(merch)

    db.session.commit()

    # Baseline Verified Deals
    from models import Product
    if Product.query.first() is None:
        initial_products = [
            {
                "title": "Rockerz 450 Wireless Bluetooth Headphone",
                "slug": "rockerz-450-wireless-bluetooth-headphone",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/61SUj2aKoEL._SL1500_.jpg",
                "category_name": "Electronics",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/Rockerz-450-Wireless-Bluetooth-Headphone/dp/B07PR1CL3S",
                "affiliate_url": "https://www.amazon.in/Rockerz-450-Wireless-Bluetooth-Headphone/dp/B07PR1CL3S",
                "original_price": 3990.0,
                "discounted_price": 1299.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "GoSriKi Women's Anarkali Viscose BAHURUP Lavender Kurta Set",
                "slug": "gosriki-womens-anarkali-viscose-bahurup-lavender-kurta-set",
                "description": "Women's lavender Anarkali viscose kurta set. Verify the included garments, fabric details, available sizes, and current price on Amazon before publishing.",
                "image_url": "https://m.media-amazon.com/images/I/61TKvc11RYL._SX569_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0HHX89YHM",
                "affiliate_url": "https://www.amazon.in/dp/B0HHX89YHM?tag=dealspark0e-21",
                "original_price": 2599.0,
                "discounted_price": 2100.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Celary Womens Kurtas Printed Straight",
                "slug": "celary-womens-kurtas-printed-straight",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/61zv-gYxr9L._SY741_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0H1D2L5FY",
                "affiliate_url": "https://www.amazon.in/dp/B0H1D2L5FY?tag=dealspark0e-21",
                "original_price": 2599.0,
                "discounted_price": 789.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Amazon Brand Tavasya Straight Comfortable",
                "slug": "amazon-brand-tavasya-straight-comfortable",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/51LT4nvMmRL._SY741_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0GV3PRTZM",
                "affiliate_url": "https://www.amazon.in/dp/B0GV3PRTZM?tag=dealspark0e-21",
                "original_price": 2599.0,
                "discounted_price": 689.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Amazon Deal (ASIN: B0D7PS5MYH)",
                "slug": "amazon-deal-asin-b0d7ps5myh",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/71nqelmB-pL._SX569_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0D7PS5MYH",
                "affiliate_url": "https://www.amazon.in/dp/B0D7PS5MYH?tag=dealspark0e-21",
                "original_price": 2599.0,
                "discounted_price": 769.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Yashika Womens Printed Minali Mustard Free",
                "slug": "yashika-womens-printed-minali-mustard-free",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/91z8vt1r4rL._SY741_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B09ZLMK2Q5",
                "affiliate_url": "https://www.amazon.in/dp/B09ZLMK2Q5?tag=dealspark0e-21",
                "original_price": 3000.0,
                "discounted_price": 1500.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Amazon Deal (ASIN: B0FCCH9D1V)",
                "slug": "amazon-deal-asin-b0fcch9d1v",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/713HSky6kVL._SX679_.jpg",
                "category_name": "Fashion & Clothing",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0FCCH9D1V",
                "affiliate_url": "https://www.amazon.in/dp/B0FCCH9D1V?tag=dealspark0e-21",
                "original_price": 3500.0,
                "discounted_price": 1699.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Boat Rockerz 480 Bluetooth Headphones",
                "slug": "boat-rockerz-480-bluetooth-headphones",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/61cIHzCDl6L._SY450_.jpg",
                "category_name": "Electronics",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0DGTTKCJX",
                "affiliate_url": "https://www.amazon.in/dp/B0DGTTKCJX?tag=dealspark0e-21",
                "original_price": 1500.0,
                "discounted_price": 1399.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Boat Headphone Lightweight Bluetooth Bubblegum",
                "slug": "boat-headphone-lightweight-bluetooth-bubblegum",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/614CDPXmolL._SY450_.jpg",
                "category_name": "Electronics",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0H1WXV25D",
                "affiliate_url": "https://www.amazon.in/dp/B0H1WXV25D?tag=dealspark0e-21",
                "original_price": 1600.0,
                "discounted_price": 1499.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Oneplus Playback Translation Dual Device Connectivity",
                "slug": "oneplus-playback-translation-dual-device-connectivity",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/51nBTTG3hNL._SY450_.jpg",
                "category_name": "Mobiles & Accessories",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0FMDL81GS",
                "affiliate_url": "https://www.amazon.in/dp/B0FMDL81GS?tag=dealspark0e-21",
                "original_price": 1900.0,
                "discounted_price": 1799.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            },
            {
                "title": "Boat Rockerz 650 Pro Headphones",
                "slug": "boat-rockerz-650-pro-headphones",
                "description": "",
                "image_url": "https://m.media-amazon.com/images/I/61-XNG5lPBL._SY450_.jpg",
                "category_name": "Electronics",
                "merchant_name": "Amazon India",
                "merchant_product_url": "https://www.amazon.in/dp/B0DV5J28LW",
                "affiliate_url": "https://www.amazon.in/dp/B0DV5J28LW?tag=dealspark0e-21",
                "original_price": 3000.0,
                "discounted_price": 2500.0,
                "is_published": True,
                "is_featured": False,
                "is_trending": False
            }
        ]
        for p_data in initial_products:
            cat = Category.query.filter_by(name=p_data['category_name']).first()
            merch = Merchant.query.filter_by(name=p_data['merchant_name']).first()
            if cat and merch:
                prod = Product(
                    title=p_data['title'],
                    slug=p_data['slug'],
                    description=p_data['description'],
                    image_url=p_data['image_url'],
                    category_id=cat.id,
                    merchant_id=merch.id,
                    merchant_product_url=p_data['merchant_product_url'],
                    affiliate_url=p_data['affiliate_url'],
                    original_price=p_data['original_price'],
                    discounted_price=p_data['discounted_price'],
                    is_published=p_data['is_published'],
                    is_featured=p_data['is_featured'],
                    is_trending=p_data['is_trending'],
                    is_available=True,
                    is_price_verified=True
                )
                db.session.add(prod)
        db.session.commit()

    # Baseline Administrator Account
    import os
    from models import User
    admin_email = os.getenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com').strip().lower()
    admin_user = User.query.filter(
        (db.func.lower(User.email) == admin_email) |
        (User.username == 'admin')
    ).first()
    admin_pass = os.getenv('ADMIN_INITIAL_PASSWORD', 'Mgayatri@123').strip()

    if not admin_user:
        admin_user = User(
            full_name='DealSpark Admin',
            username='admin',
            email=admin_email,
            role='admin',
            is_active=True
        )
        admin_user.set_password(admin_pass)
        db.session.add(admin_user)
        db.session.commit()
    else:
        updated = False
        if admin_user.role != 'admin':
            admin_user.role = 'admin'
            updated = True
        if not admin_user.is_active:
            admin_user.is_active = True
            updated = True
        if admin_user.email.lower() != admin_email:
            admin_user.email = admin_email
            updated = True
        if not admin_user.check_password(admin_pass):
            admin_user.set_password(admin_pass)
            updated = True
        if updated:
            db.session.commit()


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        run_seed()
        print("Database initialized with baseline categories and merchants.")
