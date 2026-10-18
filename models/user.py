from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), default='', nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), default='', nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    clicks = db.relationship('OutboundClick', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        from flask import current_app
        try:
            authorized_email = current_app.config.get('AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com').strip().lower()
        except Exception:
            authorized_email = 'nagarajuchaintala2002@gmail.com'
        return self.role == 'admin' and (self.email.strip().lower() == authorized_email)

    @property
    def display_name(self):
        return self.full_name or self.username or self.email.split('@')[0]

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
