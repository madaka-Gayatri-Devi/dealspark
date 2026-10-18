import os
import uuid
from functools import wraps
from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from services.product_service import ProductService
from services.product_import_service import ProductImportService
from models import db, Product, OutboundClick, Category, Merchant
from models.product import slugify

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login')
def admin_login():
    """Convenience redirect to the dedicated admin login portal."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'avif', 'gif'}


def is_allowed_image(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_product_image_file(file_storage) -> str | None:
    """Save uploaded product image securely and return its static URL path."""
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_image(file_storage.filename):
        return None

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
    os.makedirs(upload_folder, exist_ok=True)

    clean_filename = secure_filename(file_storage.filename)
    unique_filename = f"prod_{uuid.uuid4().hex[:12]}_{clean_filename}"
    file_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(file_path)
    return f"/static/uploads/products/{unique_filename}"


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in with administrator privileges to access this area.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        authorized_email = current_app.config.get(
            'AUTHORIZED_ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com'
        ).strip().lower()

        # Enforce server-side role and authorized email verification
        if not current_user.is_admin or current_user.email.strip().lower() != authorized_email:
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def make_unique_slug(title, product_id=None):
    base_slug = slugify(title) or 'deal'
    slug = base_slug
    counter = 1
    while True:
        existing = Product.query.filter_by(slug=slug).first()
        if not existing or (product_id and existing.id == product_id):
            return slug
        counter += 1
        slug = f"{base_slug[:240]}-{counter}"


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Administrator Dashboard Overview."""
    stats = ProductService.get_admin_dashboard_stats()
    recent_products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_products=recent_products,
        categories=categories,
        merchants=merchants,
        active_tab='dashboard'
    )


@admin_bp.route('/profile')
@login_required
@admin_required
def profile():
    """Administrator Profile view redirecting to unified profile."""
    return redirect(url_for('auth.profile', tab='profile'))


@admin_bp.route('/products')
@login_required
@admin_required
def manage_products():
    """Manage Products view for administrator with search & filtering."""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', '').strip()
    status_filter = request.args.get('status', '').strip().lower()

    stmt = Product.query

    if query:
        stmt = stmt.filter(Product.title.ilike(f'%{query}%') | Product.description.ilike(f'%{query}%'))

    if category_id:
        try:
            cat_id_int = int(category_id)
            stmt = stmt.filter(Product.category_id == cat_id_int)
        except (ValueError, TypeError):
            pass

    now = datetime.now(timezone.utc)
    if status_filter == 'published':
        stmt = stmt.filter(Product.is_published.is_(True), (Product.expiry_date.is_(None)) | (Product.expiry_date > now))
    elif status_filter == 'draft':
        stmt = stmt.filter(Product.is_published.is_(False))
    elif status_filter == 'expired':
        stmt = stmt.filter(Product.expiry_date.isnot(None), Product.expiry_date <= now)

    products = stmt.order_by(Product.created_at.desc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    stats = ProductService.get_admin_dashboard_stats()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        products=products,
        categories=categories,
        merchants=merchants,
        active_tab='products',
        search_query=query,
        selected_category_id=category_id,
        selected_status=status_filter
    )


@admin_bp.route('/deals')
@login_required
@admin_required
def manage_deals():
    """Manage Deals view for administrator."""
    deals = Product.query.filter_by(is_published=True).order_by(Product.created_at.desc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    stats = ProductService.get_admin_dashboard_stats()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        deals=deals,
        categories=categories,
        merchants=merchants,
        active_tab='deals'
    )


@admin_bp.route('/categories')
@login_required
@admin_required
def manage_categories():
    """Manage Categories view for administrator."""
    categories = Category.query.order_by(Category.display_order.asc(), Category.name.asc()).all()
    category_counts = ProductService.get_category_product_counts()
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    stats = ProductService.get_admin_dashboard_stats()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        categories=categories,
        category_counts=category_counts,
        merchants=merchants,
        active_tab='categories'
    )


@admin_bp.route('/merchants')
@login_required
@admin_required
def manage_merchants():
    """Manage Merchants view for administrator."""
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    stats = ProductService.get_admin_dashboard_stats()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        merchants=merchants,
        categories=categories,
        active_tab='merchants'
    )


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Outbound Click & Product Analytics view."""
    recent_clicks = OutboundClick.query.order_by(OutboundClick.created_at.desc()).limit(50).all()
    top_clicked_products = Product.query.filter(Product.click_count > 0).order_by(Product.click_count.desc()).limit(10).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    stats = ProductService.get_admin_dashboard_stats()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_clicks=recent_clicks,
        top_clicked_products=top_clicked_products,
        categories=categories,
        merchants=merchants,
        active_tab='analytics'
    )


@admin_bp.route('/api/products/import-url', methods=['POST'])
@login_required
@admin_required
def api_import_product_url():
    """API endpoint to import product metadata from shopping URLs."""
    data = request.get_json(silent=True) or request.form
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'Product URL is required.'}), 400

    result = ProductImportService.import_from_url(url)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@admin_bp.route('/api/products/upload-image', methods=['POST'])
@login_required
@admin_required
def api_upload_product_image():
    """API endpoint to upload and securely store product deal images."""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No file part in request.'}), 400

    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No image file selected.'}), 400

    saved_url = save_product_image_file(file)
    if not saved_url:
        return jsonify({
            'success': False,
            'error': f'Invalid image format. Allowed formats: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}.'
        }), 400

    return jsonify({
        'success': True,
        'image_url': saved_url,
        'message': 'Image uploaded successfully.'
    }), 200


@admin_bp.route('/products/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    """
    Create and publish a new deal product with comprehensive field validation,
    automated savings and discount calculations, and safe database persistence.
    """
    title = request.form.get('title', '').strip()
    category_id = request.form.get('category_id', '').strip()
    merchant_id = request.form.get('merchant_id', '').strip()
    image_url = request.form.get('image_url', '').strip()
    merchant_product_url = request.form.get('merchant_product_url', '').strip()
    affiliate_url = request.form.get('affiliate_url', '').strip() or merchant_product_url
    original_price = request.form.get('original_price', '').strip()
    discounted_price = request.form.get('discounted_price', '').strip()
    description = request.form.get('description', '').strip()
    is_featured = bool(request.form.get('is_featured'))
    is_trending = bool(request.form.get('is_trending'))
    is_price_verified = bool(request.form.get('is_price_verified'))
    expiry_str = request.form.get('expiry_date', '').strip()

    # 1. Process uploaded image file if provided
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename != '':
            uploaded_image = save_product_image_file(file)
            if uploaded_image:
                image_url = uploaded_image
            else:
                flash(f'Invalid image file format. Allowed formats: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}.', 'danger')
                return redirect(url_for('admin.manage_products'))

    # 2. Validate required text fields
    if not title:
        flash('Product Title is required.', 'danger')
        return redirect(url_for('admin.manage_products'))

    if not category_id:
        flash('Please select a Category for the product.', 'danger')
        return redirect(url_for('admin.manage_products'))

    if not merchant_id:
        flash('Please select a Merchant for the product.', 'danger')
        return redirect(url_for('admin.manage_products'))

    # 3. Validate category and merchant existence in database
    try:
        cat_id_int = int(category_id)
        merch_id_int = int(merchant_id)
    except (ValueError, TypeError):
        flash('Invalid category or merchant selection.', 'danger')
        return redirect(url_for('admin.manage_products'))

    category = db.session.get(Category, cat_id_int)
    merchant = db.session.get(Merchant, merch_id_int)
    if not category:
        flash('The selected category does not exist.', 'danger')
        return redirect(url_for('admin.manage_products'))
    if not merchant:
        flash('The selected merchant does not exist.', 'danger')
        return redirect(url_for('admin.manage_products'))

    # 4. Validate pricing fields
    if not original_price or not discounted_price:
        flash('Both Original Price and Discounted Deal Price are required.', 'danger')
        return redirect(url_for('admin.manage_products'))

    try:
        orig_dec = Decimal(str(original_price))
        disc_dec = Decimal(str(discounted_price))
        if orig_dec <= Decimal('0'):
            flash('Original price must be greater than zero.', 'danger')
            return redirect(url_for('admin.manage_products'))
        if disc_dec < Decimal('0'):
            flash('Discounted price cannot be negative.', 'danger')
            return redirect(url_for('admin.manage_products'))
        if disc_dec > orig_dec:
            flash('Discounted price cannot be higher than original price.', 'danger')
            return redirect(url_for('admin.manage_products'))
    except Exception:
        flash('Original price and discounted price must be valid numeric amounts.', 'danger')
        return redirect(url_for('admin.manage_products'))

    # 5. Validate image and URL
    if not image_url:
        flash('Product Image is required (enter an image URL or upload an image file).', 'danger')
        return redirect(url_for('admin.manage_products'))

    if not merchant_product_url:
        flash('Merchant Product URL is required.', 'danger')
        return redirect(url_for('admin.manage_products'))

    if not merchant_product_url.startswith(('http://', 'https://')):
        flash('Merchant Product URL must be a valid web link starting with http:// or https://', 'danger')
        return redirect(url_for('admin.manage_products'))

    if affiliate_url and not affiliate_url.startswith(('http://', 'https://')):
        flash('Affiliate URL must be a valid web link starting with http:// or https://', 'danger')
        return redirect(url_for('admin.manage_products'))

    # 6. Parse expiry date if provided
    expiry_date = None
    if expiry_str:
        try:
            parsed_dt = datetime.fromisoformat(expiry_str)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            expiry_date = parsed_dt
        except Exception:
            expiry_date = None

    # 7. Create product and calculate pricing
    product = Product(
        title=title,
        slug=make_unique_slug(title),
        description=description,
        image_url=image_url,
        category_id=category.id,
        merchant_id=merchant.id,
        merchant_product_url=merchant_product_url,
        affiliate_url=affiliate_url,
        is_published=True,
        is_available=True,
        is_featured=is_featured,
        is_trending=is_trending,
        is_price_verified=is_price_verified,
        expiry_date=expiry_date
    )
    product.set_pricing(original_price, discounted_price)

    # 8. Save product to database
    try:
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{product.title[:45]}" successfully published and live in catalog!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Database error: Could not save product ({str(e)})', 'danger')

    return redirect(url_for('admin.manage_products'))


@admin_bp.route('/products/<int:product_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_product(product_id):
    """
    Update an existing deal product with validation, dynamic calculations,
    and database persistence.
    """
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    title = request.form.get('title', '').strip()
    category_id = request.form.get('category_id', '').strip()
    merchant_id = request.form.get('merchant_id', '').strip()
    image_url = request.form.get('image_url', '').strip()
    merchant_product_url = request.form.get('merchant_product_url', '').strip()
    affiliate_url = request.form.get('affiliate_url', '').strip() or merchant_product_url
    original_price = request.form.get('original_price', '').strip()
    discounted_price = request.form.get('discounted_price', '').strip()
    description = request.form.get('description', '').strip()
    is_featured = bool(request.form.get('is_featured'))
    is_trending = bool(request.form.get('is_trending'))
    is_price_verified = bool(request.form.get('is_price_verified'))
    is_published = bool(request.form.get('is_published'))
    expiry_str = request.form.get('expiry_date', '').strip()

    # 1. Process uploaded image file if provided
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename != '':
            uploaded_image = save_product_image_file(file)
            if uploaded_image:
                image_url = uploaded_image
            else:
                flash(f'Invalid image file format. Allowed formats: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}.', 'danger')
                return redirect(request.referrer or url_for('admin.manage_products'))

    # Fallback to existing image if empty
    if not image_url:
        image_url = product.image_url

    # 2. Validate required text fields
    if not title:
        flash('Product Title is required.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    if not category_id:
        flash('Please select a Category.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    if not merchant_id:
        flash('Please select a Merchant.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    # 3. Validate category & merchant existence
    try:
        cat_id_int = int(category_id)
        merch_id_int = int(merchant_id)
    except (ValueError, TypeError):
        flash('Invalid category or merchant selection.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    category = db.session.get(Category, cat_id_int)
    merchant = db.session.get(Merchant, merch_id_int)
    if not category or not merchant:
        flash('Selected category or merchant does not exist.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    # 4. Validate pricing
    if not original_price or not discounted_price:
        flash('Both Original Price and Discounted Deal Price are required.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    try:
        orig_dec = Decimal(str(original_price))
        disc_dec = Decimal(str(discounted_price))
        if orig_dec <= Decimal('0'):
            flash('Original price must be greater than zero.', 'danger')
            return redirect(request.referrer or url_for('admin.manage_products'))
        if disc_dec < Decimal('0'):
            flash('Discounted price cannot be negative.', 'danger')
            return redirect(request.referrer or url_for('admin.manage_products'))
        if disc_dec > orig_dec:
            flash('Discounted price cannot be higher than original price.', 'danger')
            return redirect(request.referrer or url_for('admin.manage_products'))
    except Exception:
        flash('Original price and discounted price must be valid numeric amounts.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    # 5. Validate URLs
    if not merchant_product_url or not merchant_product_url.startswith(('http://', 'https://')):
        flash('Merchant Product URL must be a valid web link starting with http:// or https://', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    if affiliate_url and not affiliate_url.startswith(('http://', 'https://')):
        flash('Affiliate URL must be a valid web link starting with http:// or https://', 'danger')
        return redirect(request.referrer or url_for('admin.manage_products'))

    # 6. Parse expiry date
    expiry_date = None
    if expiry_str:
        try:
            parsed_dt = datetime.fromisoformat(expiry_str)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            expiry_date = parsed_dt
        except Exception:
            expiry_date = None

    # 7. Update product fields
    if product.title != title:
        product.title = title
        product.slug = make_unique_slug(title, product_id=product.id)

    product.description = description
    product.image_url = image_url
    product.category_id = category.id
    product.merchant_id = merchant.id
    product.merchant_product_url = merchant_product_url
    product.affiliate_url = affiliate_url
    product.is_featured = is_featured
    product.is_trending = is_trending
    product.is_price_verified = is_price_verified
    product.is_published = is_published
    product.expiry_date = expiry_date
    product.set_pricing(original_price, discounted_price)

    try:
        db.session.commit()
        flash(f'Product "{product.title[:45]}" updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Database error: Could not update product ({str(e)})', 'danger')

    return redirect(request.referrer or url_for('admin.manage_products'))


@admin_bp.route('/products/<int:product_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_product_status(product_id):
    """Toggle product published/unpublished status."""
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    product.is_published = not product.is_published
    db.session.commit()
    status_str = 'published' if product.is_published else 'unpublished'
    flash(f'Product "{product.title[:30]}" is now {status_str}.', 'info')
    return redirect(request.referrer or url_for('admin.manage_products'))


@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    """Permanently delete a product."""
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    title = product.title[:30]
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{title}" was deleted.', 'warning')
    return redirect(request.referrer or url_for('admin.manage_products'))
