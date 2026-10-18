from datetime import datetime, timezone
import re
from decimal import Decimal, ROUND_HALF_UP
from models import db


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)[:250]


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    image_url = db.Column(db.String(1000), nullable=False)

    # Foreign Keys
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchants.id'), nullable=False, index=True)

    # URLs
    merchant_product_url = db.Column(db.String(2048), nullable=False)
    affiliate_url = db.Column(db.String(2048), nullable=False)

    # Pricing (Precision 10, scale 2)
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    discounted_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0.0)
    savings_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)

    # Status flags
    is_published = db.Column(db.Boolean, default=True, index=True, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, index=True, nullable=False)
    is_trending = db.Column(db.Boolean, default=False, index=True, nullable=False)
    is_expired = db.Column(db.Boolean, default=False, index=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    is_price_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Timing & Analytics
    expiry_date = db.Column(db.DateTime, nullable=True)
    last_price_verification = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    click_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    price_history = db.relationship('ProductPriceHistory', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    clicks = db.relationship('OutboundClick', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, 'affiliate_url', None) and getattr(self, 'merchant_product_url', None):
            self.affiliate_url = self.merchant_product_url

    @staticmethod
    def calculate_pricing(original_price, discounted_price):
        """
        Validates prices and calculates exact savings and discount percentage.
        Prevents division by zero and negative prices.
        """
        try:
            orig = Decimal(str(original_price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            disc = Decimal(str(discounted_price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), Decimal('0.0')

        if orig < Decimal('0.00'):
            orig = Decimal('0.00')
        if disc < Decimal('0.00'):
            disc = Decimal('0.00')

        # If discounted price is higher than original, clamp it
        if disc > orig:
            disc = orig

        savings = (orig - disc).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if orig > Decimal('0.00'):
            discount_pct = ((savings / orig) * Decimal('100.00')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        else:
            discount_pct = Decimal('0.0')

        return orig, disc, savings, discount_pct

    def set_pricing(self, original_price, discounted_price):
        """Updates prices and recalculates savings and discount percentage."""
        orig, disc, savings, discount_pct = self.calculate_pricing(original_price, discounted_price)
        self.original_price = orig
        self.discounted_price = disc
        self.savings_amount = savings
        self.discount_percentage = discount_pct

    @property
    def is_active_deal(self):
        """Check if deal is published, available, and not expired."""
        if not self.is_published or not self.is_available or self.is_expired:
            return False
        if self.expiry_date:
            now = datetime.now(timezone.utc)
            exp = self.expiry_date
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                return False
        return True

    @property
    def is_deal_expired(self):
        """Returns True if the deal has been marked expired or its expiry_date has passed."""
        if self.is_expired:
            return True
        if self.expiry_date:
            now = datetime.now(timezone.utc)
            exp = self.expiry_date
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return exp < now
        return False

    @property
    def formatted_original_price(self):
        return f"₹{self.original_price:,.2f}".rstrip('0').rstrip('.')

    @property
    def formatted_discounted_price(self):
        return f"₹{self.discounted_price:,.2f}".rstrip('0').rstrip('.')

    @property
    def formatted_savings(self):
        return f"₹{self.savings_amount:,.2f}".rstrip('0').rstrip('.')

    @property
    def formatted_discount_percentage(self):
        if not self.discount_percentage:
            return '0'
        val = float(self.discount_percentage)
        if val.is_integer():
            return f"{int(val)}"
        return f"{val:.1f}"

    @property
    def savings(self):
        """Float convenience property for savings amount."""
        return float(self.savings_amount) if self.savings_amount is not None else 0.0

    def __repr__(self):
        return f"<Product id={self.id} title='{self.title[:30]}' disc={self.discount_percentage}%>"
