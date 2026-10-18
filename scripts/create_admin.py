import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / '.env')

from app import create_app
from models import db, User

AUTHORIZED_ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com').strip().lower()


def initialize_admin(app=None, force_repair=False):
    """
    Initializes or repairs the single authorized administrator account.
    - Authorized email: nagarajuchaintala2002@gmail.com
    - Password read securely from ADMIN_INITIAL_PASSWORD environment variable
    - In normal mode, does NOT reset an existing password automatically
    - In repair/force mode (--repair / --reset-password), securely synchronizes the
      password hash from ADMIN_INITIAL_PASSWORD without duplicate account creation
    - Reassigns username 'admin' to the authorized administrator
    - Enforces strictly one admin in the system
    - Never prints or logs raw passwords or hashes
    """
    if app is None:
        app = create_app()

    with app.app_context():
        # 1. Demote any unauthorized accounts that mistakenly have role='admin'
        stale_admins = User.query.filter(User.role == 'admin', User.email != AUTHORIZED_ADMIN_EMAIL).all()
        for stale in stale_admins:
            stale.role = 'user'
            db.session.add(stale)
        if stale_admins:
            db.session.commit()

        # 2. Free up username 'admin' if used by an older dummy/stale account
        stale_user_with_admin_username = User.query.filter(
            User.username == 'admin',
            User.email != AUTHORIZED_ADMIN_EMAIL
        ).first()
        if stale_user_with_admin_username:
            stale_user_with_admin_username.username = f"user_{stale_user_with_admin_username.id}"
            db.session.add(stale_user_with_admin_username)
            db.session.commit()

        # 3. Read password from environment
        admin_password = os.getenv('ADMIN_INITIAL_PASSWORD', '').strip()

        # 4. Check if authorized admin already exists
        existing_admin = User.query.filter_by(email=AUTHORIZED_ADMIN_EMAIL).first()

        if existing_admin:
            # Ensure correct role and username
            changed = False
            if existing_admin.role != 'admin':
                existing_admin.role = 'admin'
                changed = True
            if existing_admin.username != 'admin':
                existing_admin.username = 'admin'
                changed = True
            if not existing_admin.is_active:
                existing_admin.is_active = True
                changed = True

            if force_repair:
                if not admin_password:
                    print("[ERROR] Cannot repair password: ADMIN_INITIAL_PASSWORD is not set in environment or .env.")
                    sys.exit(1)
                if len(admin_password) < 8 or not any(c.isalpha() for c in admin_password) or not any(c.isdigit() for c in admin_password):
                    print("[ERROR] ADMIN_INITIAL_PASSWORD must be at least 8 characters with at least one letter and one number.")
                    sys.exit(1)

                existing_admin.set_password(admin_password)
                changed = True
                db.session.commit()
                print(f"[OK] Authorized administrator account ({AUTHORIZED_ADMIN_EMAIL}) successfully repaired and password synchronized from ADMIN_INITIAL_PASSWORD.")
                return

            if changed:
                db.session.commit()

            print(f"[INFO] Authorized administrator account ({AUTHORIZED_ADMIN_EMAIL}) is active. Password was NOT reset. (Use --repair to sync password from ADMIN_INITIAL_PASSWORD)")
            return

        # 5. Account does not exist yet: create it from ADMIN_INITIAL_PASSWORD
        if not admin_password:
            print("[ERROR] Environment variable ADMIN_INITIAL_PASSWORD is not set.")
            print("Please define ADMIN_INITIAL_PASSWORD in your .env file before running this script.")
            sys.exit(1)

        if len(admin_password) < 8 or not any(c.isalpha() for c in admin_password) or not any(c.isdigit() for c in admin_password):
            print("[ERROR] ADMIN_INITIAL_PASSWORD must be at least 8 characters and include at least one letter and one number.")
            sys.exit(1)

        admin = User(
            full_name='DealSpark Admin',
            username='admin',
            email=AUTHORIZED_ADMIN_EMAIL,
            role='admin',
            is_active=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"[OK] Authorized administrator account created successfully for '{AUTHORIZED_ADMIN_EMAIL}' with username 'admin'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize or repair DealSpark administrator account.')
    parser.add_argument('--repair', '--reset-password', action='store_true', dest='force_repair',
                        help='Synchronize password hash from ADMIN_INITIAL_PASSWORD environment variable for existing admin')
    args = parser.parse_args()

    initialize_admin(force_repair=args.force_repair)
