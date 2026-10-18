import pytest
from flask import session
from models import db, User
from scripts.create_admin import initialize_admin


def test_visitor_registration_disabled(client):
    """Test that public visitor registration is disabled and informs user no account is required."""
    # 1. GET /auth/register displays open deals platform notice
    res_get = client.get('/auth/register')
    assert res_get.status_code == 200
    assert b'No Account Needed' in res_get.data

    # 2. POST /auth/register redirects to homepage with info notice
    res_post = client.post('/auth/register', data={
        'full_name': 'Ravi Kumar',
        'email': 'ravi@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }, follow_redirects=True)

    assert res_post.status_code == 200
    assert b'creating an account is not required' in res_post.data


def test_non_admin_login_rejected(client, app):
    """Test non-admin users or wrong credentials cannot log into the admin portal."""
    with app.app_context():
        # Create a non-admin user
        user = User(
            full_name='Regular Shopper',
            username='shopper',
            email='shopper@example.com',
            role='user'
        )
        user.set_password('ShopperPass123!')
        db.session.add(user)
        db.session.commit()

    # Attempting to log in as non-admin user must return 401
    res = client.post('/auth/login', data={
        'email': 'shopper@example.com',
        'password': 'ShopperPass123!'
    })
    assert res.status_code == 401
    assert b'Invalid administrator credentials' in res.data


def test_invalid_login_credentials(client, app):
    """Test admin login with wrong password returns 401."""
    with app.app_context():
        admin = User(
            full_name='DealSpark Admin',
            username='admin_test',
            email='nagarajuchaintala2002@gmail.com',
            role='admin'
        )
        admin.set_password('CorrectAdminPass123!')
        db.session.add(admin)
        db.session.commit()

    res = client.post('/auth/login', data={
        'email': 'nagarajuchaintala2002@gmail.com',
        'password': 'WrongPassword999!'
    })
    assert res.status_code == 401
    assert b'Invalid administrator credentials' in res.data


def test_authorized_administrator_can_login_and_access_admin_routes(client, app):
    """Test the single authorized administrator can log in and access the dashboard."""
    with app.app_context():
        admin = User(
            full_name='DealSpark Admin',
            username='admin',
            email='nagarajuchaintala2002@gmail.com',
            role='admin'
        )
        admin.set_password('AdminSecure123!')
        db.session.add(admin)
        db.session.commit()

    # Login as authorized admin
    login_res = client.post('/auth/login', data={
        'email': 'nagarajuchaintala2002@gmail.com',
        'password': 'AdminSecure123!'
    }, follow_redirects=True)

    assert login_res.status_code == 200
    assert b'Administrator Dashboard' in login_res.data


def test_admin_logout(client, app):
    """Test administrator logout clears session state."""
    with app.app_context():
        admin = User(
            full_name='Admin Logout Test',
            username='admin_logout',
            email='nagarajuchaintala2002@gmail.com',
            role='admin'
        )
        admin.set_password('AdminPass123!')
        db.session.add(admin)
        db.session.commit()

    # Log in
    client.post('/auth/login', data={
        'email': 'nagarajuchaintala2002@gmail.com',
        'password': 'AdminPass123!'
    })

    # Log out
    res = client.post('/auth/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b'logged out successfully' in res.data


def test_unauthorized_users_cannot_access_admin_routes(client):
    """Test unauthorized users cannot access admin routes."""
    # 1. Anonymous visitor accessing /admin/dashboard
    res_anon = client.get('/admin/dashboard')
    assert res_anon.status_code == 302
    assert '/auth/login' in res_anon.headers['Location']

    # 2. Accessing /admin/login redirects to /auth/login
    res_admin_login = client.get('/admin/login')
    assert res_admin_login.status_code == 302
    assert '/auth/login' in res_admin_login.headers['Location']


def test_admin_initialization_idempotency(app, monkeypatch):
    """Test admin initialization creates account once and does not reset password unexpectedly."""
    monkeypatch.setenv('ADMIN_INITIAL_PASSWORD', 'MyTestAdminPass123!')
    monkeypatch.setenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com')

    initialize_admin(app=app)
    with app.app_context():
        admin = User.query.filter_by(email='nagarajuchaintala2002@gmail.com').first()
        assert admin is not None
        assert admin.role == 'admin'
        assert admin.is_admin is True
        initial_hash = admin.password_hash

    # Run initialization again
    initialize_admin(app=app)
    with app.app_context():
        admin_after = User.query.filter_by(email='nagarajuchaintala2002@gmail.com').first()
        # Ensure password hash was NOT altered or reset
        assert admin_after.password_hash == initial_hash


def test_administrator_can_change_own_password(client, app):
    """Test administrator can change password and reauthenticate into admin dashboard."""
    with app.app_context():
        admin = User(
            full_name='Admin User',
            username='admin',
            email='nagarajuchaintala2002@gmail.com',
            role='admin'
        )
        admin.set_password('AdminOldPass123!')
        db.session.add(admin)
        db.session.commit()

    # Log in
    client.post('/auth/login', data={'email': 'nagarajuchaintala2002@gmail.com', 'password': 'AdminOldPass123!'})

    # Change password
    res = client.post('/auth/change-password', data={
        'current_password': 'AdminOldPass123!',
        'new_password': 'AdminNewPass2026!',
        'confirm_password': 'AdminNewPass2026!'
    }, follow_redirects=True)
    assert res.status_code == 200

    # Old password no longer works
    res_old = client.post('/auth/login', data={'email': 'nagarajuchaintala2002@gmail.com', 'password': 'AdminOldPass123!'})
    assert res_old.status_code == 401

    # Reauthenticate with new password
    res_reauth = client.post('/auth/login', data={
        'email': 'nagarajuchaintala2002@gmail.com',
        'password': 'AdminNewPass2026!'
    }, follow_redirects=True)
    assert res_reauth.status_code == 200
    assert b'Administrator Dashboard' in res_reauth.data


def test_change_password_validations(client, app):
    """Test change password validation errors (wrong current, mismatch, reuse) for administrator."""
    with app.app_context():
        admin = User(
            full_name='Admin Val User',
            username='admin_val',
            email='nagarajuchaintala2002@gmail.com',
            role='admin'
        )
        admin.set_password('CurrentAdminPass123!')
        db.session.add(admin)
        db.session.commit()

    client.post('/auth/login', data={'email': 'nagarajuchaintala2002@gmail.com', 'password': 'CurrentAdminPass123!'})

    # Wrong current password
    res_wrong = client.post('/auth/change-password', data={
        'current_password': 'WrongCurrentPassword999!',
        'new_password': 'BrandNewPass2026!',
        'confirm_password': 'BrandNewPass2026!'
    })
    assert res_wrong.status_code == 400
    assert b'current password was entered incorrectly' in res_wrong.data

    # Mismatched confirmation
    res_mismatch = client.post('/auth/change-password', data={
        'current_password': 'CurrentAdminPass123!',
        'new_password': 'BrandNewPass2026!',
        'confirm_password': 'DifferentPass2026!'
    })
    assert res_mismatch.status_code == 400
    assert b'do not match' in res_mismatch.data

    # Reusing current password
    res_reuse = client.post('/auth/change-password', data={
        'current_password': 'CurrentAdminPass123!',
        'new_password': 'CurrentAdminPass123!',
        'confirm_password': 'CurrentAdminPass123!'
    })
    assert res_reuse.status_code == 400
    assert b'cannot be the same' in res_reuse.data


def test_admin_repair_synchronizes_password(app, monkeypatch):
    """Test initialize_admin with force_repair=True synchronizes the password."""
    monkeypatch.setenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com')
    monkeypatch.setenv('ADMIN_INITIAL_PASSWORD', 'FirstPassword123!')

    initialize_admin(app=app)
    with app.app_context():
        admin = User.query.filter_by(email='nagarajuchaintala2002@gmail.com').first()
        assert admin.check_password('FirstPassword123!') is True

    # Update environment variable to new password and run with force_repair=True
    monkeypatch.setenv('ADMIN_INITIAL_PASSWORD', 'RepairedPassword2026!')
    initialize_admin(app=app, force_repair=True)

    with app.app_context():
        admin_repaired = User.query.filter_by(email='nagarajuchaintala2002@gmail.com').first()
        assert admin_repaired.check_password('RepairedPassword2026!') is True
        assert admin_repaired.check_password('FirstPassword123!') is False
