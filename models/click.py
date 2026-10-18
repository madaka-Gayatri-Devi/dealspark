from datetime import datetime, timezone
import hashlib
from models import db


class OutboundClick(db.Model):
    __tablename__ = 'outbound_clicks'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    destination_url = db.Column(db.String(2048), nullable=False)
    referrer = db.Column(db.String(1000), default='')
    user_agent = db.Column(db.String(500), default='')
    ip_hash = db.Column(db.String(64), default='')  # Salted hash for privacy compliance
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    @staticmethod
    def hash_ip(ip_address, salt='dealspark-ip-salt'):
        if not ip_address:
            return ''
        return hashlib.sha256(f"{ip_address}{salt}".encode('utf-8')).hexdigest()

    def __repr__(self):
        return f"<OutboundClick id={self.id} prod={self.product_id} at={self.created_at}>"
