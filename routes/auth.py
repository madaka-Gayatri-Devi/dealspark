import re
import uuid
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Product, Category, Favorite
from services.product_service import ProductService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


def is_safe_redirect_url(target):
    """
    Prevents open-redirect attacks by ensuring the target redirect
    URL points strictly to the same host.
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Public registration route.
    DealSpark is an open shopping deals portal where browsing, searching, and
    purchasing do not require creating an account.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        flash('DealSpark is an open deals platform; creating an account is not required to browse or save deals.', 'info')
        return redirect(url_for('main.index'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Administrator sign-in route.
    Authenticates exclusively authorized administrator accounts.
    Normal visitors browse deals openly without an account.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        identifier = (request.form.get('email') or request.form.get('username') or '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        next_url = request.args.get('next') or request.form.get('next')

        if not identifier or not password:
            flash('Please enter both your email address and password.', 'danger')
            return render_template('auth/login.html'), 400

        clean_id = identifier.lower()
        authorized_email = current_app.config.get(
            'AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com'
        ).strip().lower()

        # Lookup by email or username (case-insensitive)
        user = User.query.filter(
            (db.func.lower(User.email) == clean_id) |
            (db.func.lower(User.username) == clean_id)
        ).first()

        # Strict admin check: Only admin user with matching authorized email can log in!
        if not user or not user.check_password(password) or not user.is_admin or user.email.lower() != authorized_email:
            flash('Invalid administrator credentials. DealSpark is an open shopping portal without visitor accounts.', 'danger')
            return render_template('auth/login.html'), 401

        if not user.is_active:
            flash('This administrator account has been deactivated.', 'warning')
            return render_template('auth/login.html'), 403

        # Login administrator session
        login_user(user, remember=remember)
        flash('Logged in to the Administrator Dashboard.', 'success')

        if next_url and is_safe_redirect_url(next_url) and next_url.startswith('/admin'):
            return redirect(next_url)
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Secure administrator password change.
    - Requires current password verification
    - Enforces password policy (min 8 chars, letter + digit)
    - Rejects reusing the current password
    - Clears active session and requires reauthentication
    """
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Check non-empty
        if not current_password or not new_password or not confirm_password:
            flash('Please complete all password fields.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 400

        # 2. Verify current password
        if not current_user.check_password(current_password):
            flash('Your current password was entered incorrectly.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 400

        # 3. Reject reuse of current password
        if current_user.check_password(new_password):
            flash('New password cannot be the same as your current password.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 400

        # 4. Validate new password strength
        if len(new_password) < 8 or not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
            flash('New password must be at least 8 characters long and contain at least one letter and one number.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 400

        # 5. Confirm password match
        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 400

        # 6. Securely set and commit new password hash
        current_user.set_password(new_password)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating password: {e}")
            flash('A database error occurred while updating your password. Please try again.', 'danger')
            return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password'), 500

        # Invalidate current session and require reauthentication
        logout_user()
        session.clear()
        flash('Password updated successfully! Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/change_password.html', active_tab='change_password', active_user_tab='change_password')


@auth_bp.route('/dashboard')
def dashboard():
    """Redirects to admin dashboard if admin, or homepage for visitors."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Admin Account Profile and Settings view."""
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    tab = request.args.get('tab', 'profile')

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        # Validation: Full Name
        if not full_name or len(full_name) < 2:
            flash('Full Name must be at least 2 characters long.', 'danger')
            return redirect(url_for('auth.profile', tab='profile'))

        # Validation: Email
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('auth.profile', tab='profile'))

        # Validation: Admin email cannot be changed away from configured AUTHORIZED_ADMIN_EMAIL
        authorized_admin_email = current_app.config.get(
            'AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com'
        ).strip().lower()
        if email != authorized_admin_email:
            flash(f'Administrator email address cannot be changed from {authorized_admin_email}.', 'danger')
            return redirect(url_for('auth.profile', tab='profile'))

        # Update profile fields
        try:
            current_user.full_name = full_name
            current_user.email = email
            current_user.phone = phone[:20] if phone else ''
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {str(e)}', 'danger')

        return redirect(url_for('auth.profile', tab='profile'))

    # Discovery recommendations (trending or featured deals)
    featured_deals = Product.query.filter_by(is_published=True, is_featured=True).order_by(Product.created_at.desc()).limit(6).all()
    categories = Category.query.order_by(Category.display_order.asc()).all()
    category_counts = ProductService.get_category_product_counts()
    total_active_deals = Product.query.filter_by(is_published=True, is_available=True).count()

    return render_template(
        'auth/profile.html',
        active_user_tab=tab,
        active_tab='profile',
        saved_deals=[],
        favorites_count=0,
        featured_deals=featured_deals,
        categories=categories,
        category_counts=category_counts,
        total_active_deals=total_active_deals
    )


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logs out the current user and clears session state."""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))
