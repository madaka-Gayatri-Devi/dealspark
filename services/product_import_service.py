import os
import re
import json
import hmac
import hashlib
import ipaddress
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from models import db, Merchant, Category


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private, loopback, or cloud-metadata IP (SSRF guard)."""
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or str(ip) == '169.254.169.254'
    except ValueError:
        return False


def validate_shopping_url(url: str) -> tuple[bool, str, str]:
    """
    Validate and sanitize merchant shopping URLs.
    Guards against SSRF, disallows private IPs, and enforces supported merchant domains.
    Returns: (is_valid, sanitized_url_or_error, domain)
    """
    if not url or not isinstance(url, str):
        return False, "Shopping URL is required.", ""

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False, "Invalid URL. Please enter a valid web URL starting with https:// or http://", ""

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "Invalid or malformed URL format.", ""

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Only HTTP and HTTPS protocols are allowed.", ""

    netloc = parsed.netloc.lower().split(":")[0]  # strip port if present

    if not netloc or is_private_ip(netloc) or netloc in ("localhost", "0.0.0.0", "127.0.0.1"):
        return False, "Invalid host address or restricted local destination.", ""

    # Normalize domain without www.
    domain = netloc[4:] if netloc.startswith("www.") else netloc

    supported_domains = {
        "amazon.in", "amzn.in", "amzn.to", "flipkart.com", "dl.flipkart.com", "fkrt.it"
    }

    is_supported = any(domain == d or domain.endswith("." + d) for d in supported_domains)
    if not is_supported:
        return False, (
            f"Unsupported merchant domain '{domain}'. Currently authorized automatic import providers: "
            "Amazon India (amazon.in) and Flipkart (flipkart.com). Please enter details manually."
        ), domain

    # Reconstruct sanitized URL without fragments
    clean_url = urllib.parse.urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        parsed.query,
        ""
    ))
    return True, clean_url, domain


# ==============================================================================
# Abstract Provider Interface
# ==============================================================================

class BaseProductImportProvider(ABC):
    """Abstract base class for authorized merchant product-data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Friendly provider display name."""
        pass

    @property
    @abstractmethod
    def supported_domains(self) -> set[str]:
        """Set of supported domains (without www)."""
        pass

    def can_handle(self, domain: str, url: str) -> bool:
        """Returns True if this provider handles the specified domain or URL."""
        return any(domain == d or domain.endswith("." + d) for d in self.supported_domains)

    @abstractmethod
    def extract_product_id(self, url: str) -> str | None:
        """Extract canonical product identifier (e.g. ASIN or Flipkart PID)."""
        pass

    @abstractmethod
    def get_canonical_url(self, product_id: str | None, original_url: str) -> str:
        """Construct canonical merchant shopping URL."""
        pass

    @abstractmethod
    def generate_affiliate_url(self, canonical_url: str, product_id: str | None) -> str | None:
        """Generate affiliate tracking link if affiliate tag/ID is configured."""
        pass

    @abstractmethod
    def fetch_details(self, url: str) -> dict:
        """
        Execute product data retrieval via authorized API or safe metadata fallback.
        Must return structured dictionary matching the import payload contract.
        """
        pass

    @staticmethod
    def extract_title_from_slug(url: str) -> str:
        """Extract readable product title candidate from URL path slug."""
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.strip("/")
            segments = [s for s in path.split("/") if s]

            for seg in segments:
                if len(seg) > 8 and not re.match(r'^(dp|gp|product|itm|p|buy|[A-Z0-9]{10})$', seg, re.IGNORECASE):
                    clean_slug = urllib.parse.unquote(seg)
                    clean_slug = re.sub(r'[-_+]+', ' ', clean_slug).strip()
                    words = [w.capitalize() for w in clean_slug.split() if len(w) > 0]
                    if len(words) >= 2:
                        return " ".join(words)
        except Exception:
            pass
        return ""


# ==============================================================================
# Amazon India Provider (Amazon Associates PA-API 5.0 / Creators API)
# ==============================================================================

class AmazonIndiaProvider(BaseProductImportProvider):
    """
    Authorized provider for Amazon India products.
    Uses official Amazon Product Advertising API (PA-API 5.0) with AWS SigV4
    when credentials are configured in environment variables.
    Never scrapes Amazon pages or circumvents anti-bot controls.
    """

    @property
    def name(self) -> str:
        return "Amazon India"

    @property
    def supported_domains(self) -> set[str]:
        return {"amazon.in", "amzn.in", "amzn.to"}

    def extract_product_id(self, url: str) -> str | None:
        """Extract 10-character alphanumeric ASIN from Amazon URL."""
        # Common patterns: /dp/B09XS7JWHH, /gp/product/B09XS7JWHH, /d/B09XS7JWHH
        match = re.search(r'/(?:dp|gp/product|d|product)/([A-Za-z0-9]{10})', url, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # Query param pattern: ?asin=B09XS7JWHH
        param_match = re.search(r'[?&]asin=([A-Za-z0-9]{10})', url, re.IGNORECASE)
        if param_match:
            return param_match.group(1).upper()

        # Path segment containing 10-char ASIN (often starting with B0)
        asin_match = re.search(r'/(B0[A-Za-z0-9]{8})(?:[/?]|$)', url)
        if asin_match:
            return asin_match.group(1).upper()

        return None

    def get_canonical_url(self, product_id: str | None, original_url: str) -> str:
        if product_id:
            return f"https://www.amazon.in/dp/{product_id}"
        # Fallback: clean query parameters
        parsed = urllib.parse.urlparse(original_url)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    def generate_affiliate_url(self, canonical_url: str, product_id: str | None) -> str | None:
        from flask import current_app
        tag = ""
        try:
            tag = current_app.config.get('AMAZON_ASSOCIATE_TAG', '') or os.getenv('AMAZON_ASSOCIATE_TAG', '')
        except Exception:
            tag = os.getenv('AMAZON_ASSOCIATE_TAG', '')
        tag = tag.strip()

        if tag:
            sep = "&" if "?" in canonical_url else "?"
            return f"{canonical_url}{sep}tag={tag}"
        return None

    @staticmethod
    def _aws_sigv4_request(access_key: str, secret_key: str, partner_tag: str, asin: str, region: str = "eu-west-1") -> dict:
        """
        Execute official Amazon PA-API 5.0 GetItems request with AWS Signature Version 4.
        Complies strictly with Amazon Associates API documentation.
        """
        host = "webservices.amazon.in"
        endpoint = f"https://{host}/paapi5/getitems"
        service = "ProductAdvertisingAPI"
        content_type = "application/json; charset=utf-8"
        amz_target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"

        payload_dict = {
            "ItemIds": [asin],
            "Resources": [
                "Images.Primary.Large",
                "ItemInfo.Title",
                "ItemInfo.Features",
                "ItemInfo.Classifications",
                "Offers.Listings.Price",
                "Offers.Listings.SavingBasis"
            ],
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.in"
        }
        payload_bytes = json.dumps(payload_dict, separators=(',', ':')).encode('utf-8')

        now = datetime.now(timezone.utc)
        amz_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = now.strftime('%Y%m%d')

        canonical_uri = "/paapi5/getitems"
        canonical_querystring = ""
        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:{content_type}\n"
            f"host:{host}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:{amz_target}\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        canonical_request = (
            f"POST\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # Derive signing key
        def _sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        k_date = _sign(('AWS4' + secret_key).encode('utf-8'), date_stamp)
        k_region = _sign(k_date, region)
        k_service = _sign(k_region, service)
        k_signing = _sign(k_service, "aws4_request")

        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        authorization_header = (
            f"{algorithm} Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        headers = {
            "Content-Type": content_type,
            "Content-Encoding": "amz-1.0",
            "Host": host,
            "X-Amz-Date": amz_date,
            "X-Amz-Target": amz_target,
            "Authorization": authorization_header
        }

        req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5.0) as response:
            return json.loads(response.read().decode('utf-8'))

    def fetch_details(self, url: str) -> dict:
        asin = self.extract_product_id(url)
        canonical_url = self.get_canonical_url(asin, url)
        affiliate_url = self.generate_affiliate_url(canonical_url, asin)
        slug_title = self.extract_title_from_slug(url)

        from flask import current_app
        access_key = ""
        secret_key = ""
        partner_tag = ""
        region = "eu-west-1"

        try:
            access_key = current_app.config.get('AMAZON_PAAPI_ACCESS_KEY', '') or os.getenv('AMAZON_PAAPI_ACCESS_KEY', '')
            secret_key = current_app.config.get('AMAZON_PAAPI_SECRET_KEY', '') or os.getenv('AMAZON_PAAPI_SECRET_KEY', '')
            partner_tag = current_app.config.get('AMAZON_ASSOCIATE_TAG', '') or os.getenv('AMAZON_ASSOCIATE_TAG', '')
            region = current_app.config.get('AMAZON_REGION', 'eu-west-1') or os.getenv('AMAZON_REGION', 'eu-west-1')
        except Exception:
            access_key = os.getenv('AMAZON_PAAPI_ACCESS_KEY', '')
            secret_key = os.getenv('AMAZON_PAAPI_SECRET_KEY', '')
            partner_tag = os.getenv('AMAZON_ASSOCIATE_TAG', '')
            region = os.getenv('AMAZON_REGION', 'eu-west-1')

        has_api_credentials = bool(access_key and secret_key and partner_tag)

        # 1. Attempt official Amazon PA-API call if credentials are configured
        if has_api_credentials and asin:
            try:
                api_response = self._aws_sigv4_request(access_key, secret_key, partner_tag, asin, region)
                items = api_response.get('ItemsResult', {}).get('Items', [])
                if items:
                    item = items[0]
                    item_info = item.get('ItemInfo', {})
                    title = item_info.get('Title', {}).get('DisplayValue', slug_title or '')

                    # Image
                    images = item.get('Images', {})
                    image_url = (
                        images.get('Primary', {}).get('Large', {}).get('URL')
                        or images.get('Primary', {}).get('Medium', {}).get('URL')
                        or ''
                    )

                    # Description / Features
                    features = item_info.get('Features', {}).get('DisplayValues', [])
                    description = " • ".join(features) if features else ""

                    # Pricing
                    original_price = ""
                    discounted_price = ""
                    savings_amount = ""
                    discount_percentage = None

                    offers = item.get('Offers', {}).get('Listings', [])
                    if offers:
                        listing = offers[0]
                        price_obj = listing.get('Price', {})
                        saving_basis_obj = listing.get('SavingBasis', {})

                        current_amt = price_obj.get('Amount')
                        list_amt = saving_basis_obj.get('Amount')

                        if current_amt is not None:
                            discounted_price = f"{float(current_amt):.2f}"
                        if list_amt is not None:
                            original_price = f"{float(list_amt):.2f}"
                        elif discounted_price:
                            # If saving basis is not separate, original price is current price
                            original_price = discounted_price

                        if original_price and discounted_price:
                            try:
                                orig_f = float(original_price)
                                disc_f = float(discounted_price)
                                if orig_f >= disc_f and orig_f > 0:
                                    savings_amount = f"{orig_f - disc_f:.2f}"
                                    discount_percentage = round(((orig_f - disc_f) / orig_f) * 100)
                            except ValueError:
                                pass

                    retrieved_fields = ["title", "merchant", "canonical_url"]
                    if image_url:
                        retrieved_fields.append("image_url")
                    if original_price and discounted_price:
                        retrieved_fields.extend(["original_price", "discounted_price"])
                    if description:
                        retrieved_fields.append("description")
                    if affiliate_url:
                        retrieved_fields.append("affiliate_url")

                    return {
                        "success": True,
                        "data": {
                            "title": title,
                            "merchant_name": self.name,
                            "domain": "amazon.in",
                            "product_id": asin,
                            "merchant_product_url": canonical_url,
                            "affiliate_url": affiliate_url or "",
                            "image_url": image_url,
                            "original_price": original_price,
                            "discounted_price": discounted_price,
                            "savings_amount": savings_amount,
                            "discount_percentage": discount_percentage,
                            "description": description[:800],
                            "is_api_verified": True,
                            "retrieved_fields": retrieved_fields,
                            "fetch_status": "api_verified"
                        },
                        "message": f"Successfully retrieved verified product details from Amazon Associates API for ASIN {asin}."
                    }
            except Exception as e:
                # If API credentials fail, log or fall back gracefully
                pass

        # 2. Authorized fallback when PA-API credentials are not configured or account lacks API approval
        # Do not scrape Amazon pages to avoid anti-bot CAPTCHAs and policy violations.
        title_candidate = slug_title or (f"Amazon Deal (ASIN: {asin})" if asin else "Amazon India Product")
        retrieved_fields = ["merchant", "canonical_url"]
        if slug_title:
            retrieved_fields.append("title")
        if affiliate_url:
            retrieved_fields.append("affiliate_url")

        message = (
            f"Recognized Amazon India product (ASIN: {asin or 'N/A'}). "
            "Official Amazon Associates PA-API credentials are not configured in .env "
            "(AMAZON_PAAPI_ACCESS_KEY, AMAZON_PAAPI_SECRET_KEY, AMAZON_ASSOCIATE_TAG). "
            "Product URL and title candidate populated. Please verify deal price and image manually."
        )

        return {
            "success": True,
            "data": {
                "title": title_candidate,
                "merchant_name": self.name,
                "domain": "amazon.in",
                "product_id": asin or "",
                "merchant_product_url": canonical_url,
                "affiliate_url": affiliate_url or "",
                "image_url": "",
                "original_price": "",
                "discounted_price": "",
                "savings_amount": "",
                "discount_percentage": None,
                "description": "",
                "is_api_verified": False,
                "retrieved_fields": retrieved_fields,
                "fetch_status": "credentials_required"
            },
            "message": message
        }


# ==============================================================================
# Flipkart Provider (Flipkart Affiliate API)
# ==============================================================================

class FlipkartProvider(BaseProductImportProvider):
    """
    Authorized provider for Flipkart products.
    Uses official Flipkart Affiliate API when credentials are configured in environment.
    Never scrapes protected pages.
    """

    @property
    def name(self) -> str:
        return "Flipkart"

    @property
    def supported_domains(self) -> set[str]:
        return {"flipkart.com", "dl.flipkart.com", "fkrt.it"}

    def extract_product_id(self, url: str) -> str | None:
        """Extract Flipkart PID or Item ID."""
        # Query parameter: ?pid=MOBGTAGPTB3VS24W
        match_pid = re.search(r'[?&]pid=([A-Za-z0-9]+)', url)
        if match_pid:
            return match_pid.group(1).upper()

        # Path: /p/itm...
        match_p = re.search(r'/p/(itm[A-Za-z0-9]+)', url, re.IGNORECASE)
        if match_p:
            return match_p.group(1)

        match_itm = re.search(r'/(itm[A-Za-z0-9]+)', url, re.IGNORECASE)
        if match_itm:
            return match_itm.group(1)

        return None

    def get_canonical_url(self, product_id: str | None, original_url: str) -> str:
        parsed = urllib.parse.urlparse(original_url)
        clean_path = parsed.path
        query = f"pid={product_id}" if product_id and "pid=" not in clean_path else ""
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, clean_path, "", query, ""))

    def generate_affiliate_url(self, canonical_url: str, product_id: str | None) -> str | None:
        from flask import current_app
        aff_id = ""
        try:
            aff_id = current_app.config.get('FLIPKART_AFFILIATE_ID', '') or os.getenv('FLIPKART_AFFILIATE_ID', '')
        except Exception:
            aff_id = os.getenv('FLIPKART_AFFILIATE_ID', '')
        aff_id = aff_id.strip()

        if aff_id:
            sep = "&" if "?" in canonical_url else "?"
            return f"{canonical_url}{sep}affid={aff_id}"
        return None

    def fetch_details(self, url: str) -> dict:
        pid = self.extract_product_id(url)
        canonical_url = self.get_canonical_url(pid, url)
        affiliate_url = self.generate_affiliate_url(canonical_url, pid)
        slug_title = self.extract_title_from_slug(url)

        from flask import current_app
        aff_id = ""
        aff_token = ""
        try:
            aff_id = current_app.config.get('FLIPKART_AFFILIATE_ID', '') or os.getenv('FLIPKART_AFFILIATE_ID', '')
            aff_token = current_app.config.get('FLIPKART_AFFILIATE_TOKEN', '') or os.getenv('FLIPKART_AFFILIATE_TOKEN', '')
        except Exception:
            aff_id = os.getenv('FLIPKART_AFFILIATE_ID', '')
            aff_token = os.getenv('FLIPKART_AFFILIATE_TOKEN', '')

        has_api_credentials = bool(aff_id and aff_token)

        # 1. Attempt official Flipkart Affiliate API if credentials configured
        if has_api_credentials and pid:
            try:
                api_url = f"https://affiliate-api.flipkart.net/affiliate/1.0/product.json?id={pid}"
                req = urllib.request.Request(
                    api_url,
                    headers={
                        "Fk-Affiliate-Id": aff_id,
                        "Fk-Affiliate-Token": aff_token,
                        "Accept": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    base_info = data.get('productBaseInfoV1', {})
                    attrs = base_info.get('productAttributes', {})

                    title = attrs.get('title', slug_title or '')
                    desc = attrs.get('productDescription', '')

                    # Images
                    img_dict = attrs.get('imageUrls', {})
                    image_url = img_dict.get('800x800') or img_dict.get('400x400') or img_dict.get('unknown', '')

                    # Pricing
                    mrp = attrs.get('maximumRetailPrice', {}).get('amount')
                    selling = (
                        attrs.get('flipkartSpecialPrice', {}).get('amount')
                        or attrs.get('flipkartSellingPrice', {}).get('amount')
                    )

                    original_price = f"{float(mrp):.2f}" if mrp is not None else ""
                    discounted_price = f"{float(selling):.2f}" if selling is not None else ""
                    savings_amount = ""
                    discount_percentage = None

                    if original_price and discounted_price:
                        try:
                            orig_f = float(original_price)
                            disc_f = float(discounted_price)
                            if orig_f >= disc_f and orig_f > 0:
                                savings_amount = f"{orig_f - disc_f:.2f}"
                                discount_percentage = round(((orig_f - disc_f) / orig_f) * 100)
                        except ValueError:
                            pass

                    retrieved_fields = ["title", "merchant", "canonical_url"]
                    if image_url:
                        retrieved_fields.append("image_url")
                    if original_price and discounted_price:
                        retrieved_fields.extend(["original_price", "discounted_price"])
                    if desc:
                        retrieved_fields.append("description")
                    if affiliate_url:
                        retrieved_fields.append("affiliate_url")

                    return {
                        "success": True,
                        "data": {
                            "title": title,
                            "merchant_name": self.name,
                            "domain": "flipkart.com",
                            "product_id": pid,
                            "merchant_product_url": canonical_url,
                            "affiliate_url": affiliate_url or "",
                            "image_url": image_url,
                            "original_price": original_price,
                            "discounted_price": discounted_price,
                            "savings_amount": savings_amount,
                            "discount_percentage": discount_percentage,
                            "description": desc[:800],
                            "is_api_verified": True,
                            "retrieved_fields": retrieved_fields,
                            "fetch_status": "api_verified"
                        },
                        "message": f"Successfully retrieved verified product details from Flipkart Affiliate API for ID {pid}."
                    }
            except Exception:
                pass

        # 2. Fallback when Flipkart API credentials not configured
        title_candidate = slug_title or (f"Flipkart Deal (ID: {pid})" if pid else "Flipkart Product")
        retrieved_fields = ["merchant", "canonical_url"]
        if slug_title:
            retrieved_fields.append("title")
        if affiliate_url:
            retrieved_fields.append("affiliate_url")

        message = (
            f"Recognized Flipkart product (ID: {pid or 'N/A'}). "
            "Official Flipkart Affiliate API credentials are not configured in .env "
            "(FLIPKART_AFFILIATE_ID, FLIPKART_AFFILIATE_TOKEN). "
            "Product URL and title candidate populated. Please enter deal price and image manually."
        )

        return {
            "success": True,
            "data": {
                "title": title_candidate,
                "merchant_name": self.name,
                "domain": "flipkart.com",
                "product_id": pid or "",
                "merchant_product_url": canonical_url,
                "affiliate_url": affiliate_url or "",
                "image_url": "",
                "original_price": "",
                "discounted_price": "",
                "savings_amount": "",
                "discount_percentage": None,
                "description": "",
                "is_api_verified": False,
                "retrieved_fields": retrieved_fields,
                "fetch_status": "credentials_required"
            },
            "message": message
        }


# ==============================================================================
# Primary Product Import Service Orchestrator
# ==============================================================================

class ProductImportService:
    """
    Orchestrates authorized merchant product-data imports with provider-based
    architecture, strict SSRF security, price accuracy, and manual fallback.
    """

    PROVIDERS: list[BaseProductImportProvider] = [
        AmazonIndiaProvider(),
        FlipkartProvider()
    ]

    CATEGORY_KEYWORDS = {
        "Electronics": [
            "laptop", "phone", "smartphone", "headphone", "earphone", "earbuds", "audio",
            "tv", "camera", "tablet", "watch", "smartwatch", "speaker", "bluetooth",
            "charger", "cable", "ssd", "ram", "mouse", "keyboard", "monitor"
        ],
        "Mobiles & Accessories": [
            "mobile", "smartphone", "iphone", "galaxy", "oneplus", "realme", "redmi",
            "case", "cover", "tempered", "charger", "earbuds"
        ],
        "Fashion": [
            "shirt", "t-shirt", "jeans", "dress", "shoes", "sneakers", "jacket",
            "hoodie", "pants", "kurta", "saree", "watch", "wallet", "belt", "handbag"
        ],
        "Home & Kitchen": [
            "cookware", "pan", "pot", "kitchen", "blender", "mixer", "furniture",
            "bed", "chair", "sofa", "pillow", "curtain", "lamp", "vacuum", "purifier"
        ],
        "Beauty": [
            "cream", "serum", "lotion", "lipstick", "perfume", "fragrance", "shampoo",
            "conditioner", "sunscreen", "makeup", "facewash", "skincare"
        ],
        "Books": [
            "book", "novel", "paperback", "hardcover", "edition", "author", "guide"
        ],
        "Sports & Fitness": [
            "fitness", "dumbbells", "yoga", "mat", "cycle", "bicycle", "treadmill",
            "protein", "gym", "workout"
        ]
    }

    @classmethod
    def get_provider_for_domain(cls, domain: str, url: str) -> BaseProductImportProvider | None:
        """Find registered provider matching domain or URL."""
        for provider in cls.PROVIDERS:
            if provider.can_handle(domain, url):
                return provider
        return None

    @classmethod
    def suggest_category_id(cls, text: str) -> int | None:
        """Match existing DealSpark category based on keywords in title/description."""
        from flask import has_app_context
        if not text or not has_app_context():
            return None
        text_lower = text.lower()

        best_cat_name = None
        best_count = 0
        for cat_name, keywords in cls.CATEGORY_KEYWORDS.items():
            count = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
            if count > best_count:
                best_count = count
                best_cat_name = cat_name

        if best_cat_name:
            cat = Category.query.filter(Category.name.ilike(f"%{best_cat_name}%")).first()
            if cat:
                return cat.id

        first_cat = Category.query.order_by(Category.display_order.asc()).first()
        return first_cat.id if first_cat else None

    @classmethod
    def suggest_merchant_id(cls, merchant_name: str, domain: str) -> int | None:
        """Match existing DealSpark merchant from database by name or domain."""
        from flask import has_app_context
        if not has_app_context():
            return None

        if merchant_name:
            m = Merchant.query.filter(Merchant.name.ilike(f"%{merchant_name}%")).first()
            if m:
                return m.id

        if domain:
            m = Merchant.query.filter(Merchant.domain.ilike(f"%{domain}%")).first()
            if m:
                return m.id

        first_m = Merchant.query.order_by(Merchant.id.asc()).first()
        return first_m.id if first_m else None

    @classmethod
    def import_from_url(cls, url: str) -> dict:
        """
        Validate URL, dispatch to authorized provider, retrieve product data,
        correlate with DealSpark database entities, and return structured result.
        """
        is_valid, sanitized_url_or_err, domain = validate_shopping_url(url)
        if not is_valid:
            return {
                "success": False,
                "error": sanitized_url_or_err
            }

        provider = cls.get_provider_for_domain(domain, sanitized_url_or_err)
        if not provider:
            return {
                "success": False,
                "error": (
                    f"No authorized provider configured for domain '{domain}'. "
                    "Automatic import is available for Amazon India (amazon.in) and Flipkart (flipkart.com)."
                )
            }

        result = provider.fetch_details(sanitized_url_or_err)
        if not result.get("success"):
            return result

        data = result.get("data", {})
        title_for_cat = f"{data.get('title', '')} {data.get('description', '')}"

        matched_category_id = cls.suggest_category_id(title_for_cat)
        matched_merchant_id = cls.suggest_merchant_id(provider.name, domain)

        data["category_id"] = matched_category_id
        data["merchant_id"] = matched_merchant_id

        return result
