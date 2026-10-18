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


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        run_seed()
        print("Database initialized with baseline categories and merchants.")
