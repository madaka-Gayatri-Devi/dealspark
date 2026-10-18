from urllib.parse import urlparse
from flask import current_app
from models import db, OutboundClick, Product


class ClickService:
    @staticmethod
    def is_allowed_destination(url):
        """
        Validates the destination URL against configured allowed affiliate domains
        to protect users against open redirects.
        """
        if not url:
            return False

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False

            hostname = parsed.netloc.lower()
            # Strip port if present
            if ':' in hostname:
                hostname = hostname.split(':')[0]

            allowed_domains = current_app.config.get('ALLOWED_REDIRECT_DOMAINS', [])
            for domain in allowed_domains:
                domain = domain.lower().strip()
                if hostname == domain or hostname.endswith('.' + domain):
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def record_click(product, request_obj, user_id=None):
        """
        Safely records an outbound deal click with timestamp and anonymized metadata.
        Increments the product's click count atomically.
        """
        try:
            # IP hashing for privacy compliance
            ip_address = request_obj.headers.get('X-Forwarded-For', request_obj.remote_addr)
            if ip_address and ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

            ip_hash = OutboundClick.hash_ip(ip_address)
            referrer = request_obj.referrer or ''
            user_agent = request_obj.user_agent.string[:500] if request_obj.user_agent else ''

            # Target is the product affiliate URL
            target_url = product.affiliate_url or product.merchant_product_url

            click = OutboundClick(
                product_id=product.id,
                user_id=user_id,
                destination_url=target_url,
                referrer=referrer[:1000],
                user_agent=user_agent,
                ip_hash=ip_hash
            )
            db.session.add(click)

            # Increment click count on product
            product.click_count = (product.click_count or 0) + 1
            db.session.commit()
            return click
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording click: {e}")
            return None
