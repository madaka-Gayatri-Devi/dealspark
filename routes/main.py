from flask import Blueprint, render_template, request, current_app, jsonify, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from models import db, Product, Category, Merchant, Favorite
from services.product_service import ProductService

main_bp = Blueprint('main', __name__)


@main_bp.route('/api/debug-env')
@main_bp.route('/debug-env')
def debug_env():
    return jsonify({
        'PATH_INFO': request.environ.get('PATH_INFO'),
        'REQUEST_URI': request.environ.get('REQUEST_URI'),
        'HTTP_X_VERCEL_URI': request.environ.get('HTTP_X_VERCEL_URI'),
        'HTTP_X_MATCHED_PATH': request.environ.get('HTTP_X_MATCHED_PATH'),
        'QUERY_STRING': request.environ.get('QUERY_STRING'),
        'request.path': request.path,
        'request.url': request.url,
        'http_headers': {k: str(v) for k, v in request.environ.items() if k.startswith('HTTP_')}
    })


@main_bp.route('/api/index')
@main_bp.route('/')
def index():
    """
    Homepage displaying hero section, categories,
    featured price drops, trending offers, latest deals, best discounts,
    popular products (if clicks exist), and trust badges.
    """
    categories = ProductService.get_active_categories()
    merchants = ProductService.get_active_merchants()
    category_counts = ProductService.get_category_product_counts()

    used_ids = set()
    featured_deals = ProductService.get_featured_deals(limit=8)
    used_ids.update(p.id for p in featured_deals)

    trending_deals = ProductService.get_trending_deals(limit=8, exclude_ids=used_ids)
    used_ids.update(p.id for p in trending_deals)

    best_discount_deals = ProductService.get_best_discount_deals(limit=8, exclude_ids=used_ids)
    used_ids.update(p.id for p in best_discount_deals)

    latest_deals = ProductService.get_latest_deals(limit=12, exclude_ids=used_ids)
    popular_deals = ProductService.get_popular_deals(limit=8)
    stats = ProductService.get_homepage_stats()

    return render_template(
        'index.html',
        categories=categories,
        merchants=merchants,
        category_counts=category_counts,
        featured_deals=featured_deals,
        trending_deals=trending_deals,
        latest_deals=latest_deals,
        best_discount_deals=best_discount_deals,
        popular_deals=popular_deals,
        stats=stats
    )


@main_bp.route('/deals')
def deals_list():
    """
    Unified product listing page with responsive grid (6 cols on XXL, 4 on desktop, 2 on tablet/mobile),
    filters (category, merchant, price range, discount), sorting, and server-side pagination.
    """
    query_str = request.args.get('q', '').strip()
    category_slug = request.args.get('category', '').strip()
    merchant_slug = request.args.get('merchant', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    min_discount = request.args.get('min_discount', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1)
    per_page = current_app.config.get('DEALS_PER_PAGE', 12)

    categories = ProductService.get_active_categories()
    merchants = ProductService.get_active_merchants()
    category_counts = ProductService.get_category_product_counts()

    selected_category = Category.query.filter_by(slug=category_slug).first() if category_slug else None
    selected_merchant = Merchant.query.filter_by(slug=merchant_slug).first() if merchant_slug else None

    pagination = ProductService.filter_and_paginate_deals(
        query_str=query_str,
        category_slug=category_slug,
        merchant_slug=merchant_slug,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by,
        page=page,
        per_page=per_page
    )

    return render_template(
        'deals/list.html',
        pagination=pagination,
        deals=pagination.items,
        categories=categories,
        merchants=merchants,
        category_counts=category_counts,
        query_str=query_str,
        selected_category=selected_category,
        selected_merchant=selected_merchant,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by,
        page_title='Explore All Deals'
    )


@main_bp.route('/category/<slug>')
def category_deals(slug):
    """
    Dedicated category deals discovery route with product counts and active category pills.
    Supports filtering, sorting, and pagination within the category.
    """
    category = Category.query.filter_by(slug=slug, is_active=True).first_or_404()

    query_str = request.args.get('q', '').strip()
    merchant_slug = request.args.get('merchant', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    min_discount = request.args.get('min_discount', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1)
    per_page = current_app.config.get('DEALS_PER_PAGE', 12)

    categories = ProductService.get_active_categories()
    merchants = ProductService.get_active_merchants()
    category_counts = ProductService.get_category_product_counts()
    selected_merchant = Merchant.query.filter_by(slug=merchant_slug).first() if merchant_slug else None

    pagination = ProductService.filter_and_paginate_deals(
        query_str=query_str,
        category_slug=category.slug,
        merchant_slug=merchant_slug,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by,
        page=page,
        per_page=per_page
    )

    return render_template(
        'deals/list.html',
        pagination=pagination,
        deals=pagination.items,
        categories=categories,
        merchants=merchants,
        category_counts=category_counts,
        query_str=query_str,
        selected_category=category,
        selected_merchant=selected_merchant,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by,
        page_title=f"{category.name} Deals",
        is_category_view=True
    )


@main_bp.route('/deal/<slug>')
def deal_detail(slug):
    """
    Product details page with large image, pricing, savings, verification status,
    deal expiry info, Buy Now CTA, share actions, and related category products.
    """
    product = ProductService.get_deal_by_id_or_slug(slug)
    if not product:
        abort(404)

    # Related deals ranked by category, keywords, merchant and price proximity
    related_deals = ProductService.get_related_deals(product, limit=4)
    related_heading = ProductService.get_related_deals_heading(product)

    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = Favorite.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first() is not None

    return render_template(
        'deals/detail.html',
        product=product,
        related_deals=related_deals,
        related_heading=related_heading,
        hide_footer=True,
        is_favorited=is_favorited
    )


@main_bp.route('/search')
def search():
    """
    Search results route querying product title and description in the database.
    Supports filtering, sorting, and pagination.
    """
    query_str = request.args.get('q', '').strip()
    category_slug = request.args.get('category', '').strip()
    merchant_slug = request.args.get('merchant', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    min_discount = request.args.get('min_discount', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1)
    per_page = current_app.config.get('DEALS_PER_PAGE', 12)

    categories = ProductService.get_active_categories()
    merchants = ProductService.get_active_merchants()
    category_counts = ProductService.get_category_product_counts()

    selected_category = Category.query.filter_by(slug=category_slug).first() if category_slug else None
    selected_merchant = Merchant.query.filter_by(slug=merchant_slug).first() if merchant_slug else None

    pagination = ProductService.filter_and_paginate_deals(
        query_str=query_str,
        category_slug=category_slug,
        merchant_slug=merchant_slug,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by,
        page=page,
        per_page=per_page
    )

    return render_template(
        'search.html',
        pagination=pagination,
        deals=pagination.items,
        total_results=pagination.total,
        query=query_str,
        categories=categories,
        merchants=merchants,
        category_counts=category_counts,
        selected_category=selected_category,
        selected_merchant=selected_merchant,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_by=sort_by
    )


@main_bp.route('/api/search/suggestions')
def search_suggestions():
    """
    Debounced autocomplete suggestions JSON endpoint.
    Returns product suggestions and matching categories.
    """
    query_str = request.args.get('q', '').strip()
    suggestions = ProductService.get_search_suggestions(query_str, limit=6)
    categories = ProductService.get_category_suggestions(query_str, limit=3)
    return jsonify({
        'suggestions': suggestions,
        'categories': categories
    })


@main_bp.route('/favorites/toggle/<int:product_id>', methods=['POST'])
def toggle_favorite(product_id):
    """
    Bookmark or remove a product from favorites.
    Supports authenticated users (saved to database) and anonymous visitors (confirmed for localStorage sync).
    """
    product = Product.query.get_or_404(product_id)

    if current_user.is_authenticated:
        fav = Favorite.query.filter_by(user_id=current_user.id, product_id=product.id).first()

        if fav:
            db.session.delete(fav)
            db.session.commit()
            favorited = False
            message = f'Removed "{product.title[:30]}" from favorites.'
        else:
            new_fav = Favorite(user_id=current_user.id, product_id=product.id)
            db.session.add(new_fav)
            db.session.commit()
            favorited = True
            message = f'Added "{product.title[:30]}" to favorites.'

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'ok',
                'favorited': favorited,
                'message': message,
                'product_id': product.id
            })

        flash(message, 'success')
        return redirect(request.referrer or url_for('main.deals_list'))

    # Anonymous visitor: returns ok status so client manages localStorage
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'ok',
            'anonymous': True,
            'product_id': product.id,
            'title': product.title
        })

    return redirect(request.referrer or url_for('main.deals_list'))


@main_bp.route('/dashboard')
def dashboard():
    """Universal dashboard entry point: redirects admin to admin dashboard, and visitors to homepage."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.index'))


@main_bp.route('/favorites')
def favorites():
    """Public saved deals view powered by local storage and database lookup."""
    ids_param = request.args.get('ids', '').strip()
    saved_deal_ids = []

    if ids_param:
        for part in ids_param.split(','):
            part = part.strip()
            if part.isdigit():
                saved_deal_ids.append(int(part))
    elif current_user.is_authenticated:
        fav_records = current_user.favorites.order_by(Favorite.created_at.desc()).all()
        saved_deal_ids = [f.product_id for f in fav_records]

    products = []
    if saved_deal_ids:
        found_products = Product.query.filter(
            Product.id.in_(saved_deal_ids),
            Product.is_published.is_(True),
            Product.is_available.is_(True)
        ).all()
        id_to_prod = {p.id: p for p in found_products}
        products = [id_to_prod[pid] for pid in saved_deal_ids if pid in id_to_prod]

    return render_template(
        'deals/favorites.html',
        products=products,
        favorites=products,
        user_fav_ids=saved_deal_ids
    )


@main_bp.route('/about')
def about():
    """About DealSpark information page."""
    return render_template('about.html')


@main_bp.route('/disclaimer')
def disclaimer():
    """Affiliate and pricing disclaimer page."""
    return render_template('disclaimer.html')
