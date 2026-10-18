from datetime import datetime, timezone
import re
from models import db


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)


class Merchant(db.Model):
    __tablename__ = 'merchants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(150), nullable=False)
    logo_url = db.Column(db.String(500), default='')
    badge_color = db.Column(db.String(20), default='#ff6f00', nullable=False)
    affiliate_tag = db.Column(db.String(100), default='')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    products = db.relationship('Product', backref='merchant', lazy='dynamic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.slug and self.name:
            self.slug = slugify(self.name)

    def __repr__(self):
        return f"<Merchant id={self.id} name='{self.name}'>"
