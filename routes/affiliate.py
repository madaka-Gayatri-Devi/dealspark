from flask import Blueprint, redirect, abort, request, flash, url_for, render_template
from flask_login import current_user
from models import Product
from services.click_service import ClickService

affiliate_bp = Blueprint('affiliate', __name__, url_prefix='/out')


@affiliate_bp.route('/<int:product_id>')
def redirect_deal(product_id):
    """
    Secure outbound redirect endpoint for affiliate 'Buy Now' links.
    - Validates product existence and availability.
    - Validates destination domain against open redirect whitelist.
    - Asynchronously records the click with privacy-safe tracking.
    """
    product = Product.query.get_or_404(product_id)

    if not product.is_published or not product.is_available:
        flash('This deal is currently unavailable or has expired.', 'warning')
        return redirect(url_for('main.index'))

    target_url = product.affiliate_url or product.merchant_product_url

    # Protect against open redirect vulnerabilities
    if not ClickService.is_allowed_destination(target_url):
        # In case the URL is not in whitelist, block the redirect
        flash('Destination merchant URL could not be verified for security.', 'danger')
        return redirect(url_for('main.index'))

    # Record outbound click
    user_id = current_user.id if current_user.is_authenticated else None
    ClickService.record_click(product, request, user_id=user_id)

    return redirect(target_url)
