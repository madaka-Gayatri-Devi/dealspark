import re
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import or_, and_, func
from models import db, Product, Category, Merchant


class ProductService:
    @staticmethod
    def get_active_deal_base_query():
        """
        Base query for active, published, available, and non-expired deals.
        Timezone-aware comparison ensures accurate expiry handling across SQLite and MySQL.
        """
        now = datetime.now(timezone.utc)
        return Product.query.filter(
            Product.is_published.is_(True),
            Product.is_available.is_(True),
            Product.is_expired.is_(False),
            or_(Product.expiry_date.is_(None), Product.expiry_date > now)
        )

    @staticmethod
    def get_active_categories():
        """Retrieve active categories ordered by display_order and name."""
        return Category.query.filter_by(is_active=True).order_by(
            Category.display_order.asc(), Category.name.asc()
        ).all()

    @staticmethod
    def get_active_merchants():
        """Retrieve active partner merchants ordered by name."""
        return Merchant.query.filter_by(is_active=True).order_by(Merchant.name.asc()).all()

    @staticmethod
    def get_category_product_counts():
        """
        Returns a dict mapping category_id to count of available active deals.
        Only counts active deals.
        """
        now = datetime.now(timezone.utc)
        counts = db.session.query(
            Product.category_id,
            func.count(Product.id)
        ).filter(
            Product.is_published.is_(True),
            Product.is_available.is_(True),
            Product.is_expired.is_(False),
            or_(Product.expiry_date.is_(None), Product.expiry_date > now)
        ).group_by(Product.category_id).all()

        return {cat_id: count for cat_id, count in counts}

    @staticmethod
    def filter_and_paginate_deals(
        query_str=None,
        category_slug=None,
        merchant_slug=None,
        min_price=None,
        max_price=None,
        min_discount=None,
        is_featured=None,
        sort_by='newest',
        page=1,
        per_page=12
    ):
        """
        Unified filtering, sorting, and pagination engine for deals.
        Ensures stable secondary ordering and safe type conversions.
        """
        query = ProductService.get_active_deal_base_query()

        # Keyword search across title and description
        if query_str and query_str.strip():
            term = f"%{query_str.strip()}%"
            query = query.filter(
                or_(
                    Product.title.ilike(term),
                    Product.description.ilike(term)
                )
            )

        # Category filter by slug
        if category_slug and category_slug.strip():
            query = query.join(Product.category).filter(Category.slug == category_slug.strip().lower())

        # Merchant filter by slug
        if merchant_slug and merchant_slug.strip():
            query = query.join(Product.merchant).filter(Merchant.slug == merchant_slug.strip().lower())

        # Price range filters (with validation)
        try:
            if min_price is not None and str(min_price).strip() != '':
                min_p = float(min_price)
                if min_p >= 0:
                    query = query.filter(Product.discounted_price >= min_p)
        except (ValueError, TypeError):
            pass

        try:
            if max_price is not None and str(max_price).strip() != '':
                max_p = float(max_price)
                if max_p >= 0:
                    query = query.filter(Product.discounted_price <= max_p)
        except (ValueError, TypeError):
            pass

        # Minimum discount filter (e.g. 10%, 20%, 50%)
        try:
            if min_discount is not None and str(min_discount).strip() != '':
                min_d = float(min_discount)
                if min_d >= 0:
                    query = query.filter(Product.discount_percentage >= min_d)
        except (ValueError, TypeError):
            pass

        # Featured filter
        if is_featured:
            query = query.filter(Product.is_featured.is_(True))

        # Sorting with stable secondary sort (Product.id.desc())
        sort_map = {
            'newest': (Product.created_at.desc(), Product.id.desc()),
            'price_asc': (Product.discounted_price.asc(), Product.id.desc()),
            'price_desc': (Product.discounted_price.desc(), Product.id.desc()),
            'discount_desc': (Product.discount_percentage.desc(), Product.id.desc()),
            'popular': (Product.click_count.desc(), Product.created_at.desc(), Product.id.desc()),
        }
        order_clauses = sort_map.get(sort_by, sort_map['newest'])
        query = query.order_by(*order_clauses)

        # Validate page number
        try:
            page_num = int(page)
            if page_num < 1:
                page_num = 1
        except (ValueError, TypeError):
            page_num = 1

        try:
            per_page_num = int(per_page)
            if per_page_num < 1 or per_page_num > 100:
                per_page_num = 12
        except (ValueError, TypeError):
            per_page_num = 12

        return query.paginate(page=page_num, per_page=per_page_num, error_out=False)

    @staticmethod
    def _stem_word(word):
        """Helper to get root stem for robust matching (e.g., kurtas/kurti -> kurt)."""
        w = word.lower().strip()
        if w in ('kurti', 'kurtis', 'kurta', 'kurtas', 'kurti-set', 'kurta-set'):
            return 'kurt'
        if w in ('headphones', 'headphone', 'earbuds', 'earphone', 'earphones'):
            return 'headphon'
        if w in ('shoes', 'shoe', 'sneakers', 'sneaker'):
            return 'shoe'
        if w in ('watches', 'watch', 'smartwatch', 'smartwatches'):
            return 'watch'
        if w in ('laptops', 'laptop'):
            return 'laptop'
        if w in ('mobiles', 'mobile', 'smartphones', 'smartphone', 'phones', 'phone'):
            return 'mobil'
        if w in ('sarees', 'saree', 'saris', 'sari'):
            return 'saree'
        if w.endswith('es') and len(w) > 4:
            return w[:-2]
        if w.endswith('s') and len(w) > 3:
            return w[:-1]
        return w

    @staticmethod
    def get_search_suggestions(query_str, limit=6):
        """
        Fast autocomplete suggestions for the header and hero search bar.
        Matches product title, description, merchant name, or category name.
        Uses intelligent root-term expansion (e.g. kurti matches kurta and kurtas).
        Returns a lightweight list of matching deal dictionaries.
        """
        if not query_str or not query_str.strip() or len(query_str.strip()) < 2:
            return []

        raw_query = query_str.strip().lower()
        search_terms = {raw_query}

        # Expand search terms with root stem if applicable
        stemmed = ProductService._stem_word(raw_query)
        if stemmed and len(stemmed) >= 3:
            search_terms.add(stemmed)
            if stemmed == 'kurt':
                search_terms.update(['kurta', 'kurti', 'kurtas'])
            elif stemmed == 'headphon':
                search_terms.update(['headphone', 'headphones', 'earbuds'])

        # Build OR filters across terms
        filters = []
        for term in search_terms:
            t = f"%{term}%"
            filters.extend([
                Product.title.ilike(t),
                Product.description.ilike(t),
                Merchant.name.ilike(t),
                Category.name.ilike(t)
            ])

        deals = ProductService.get_active_deal_base_query().outerjoin(
            Category, Product.category_id == Category.id
        ).outerjoin(
            Merchant, Product.merchant_id == Merchant.id
        ).filter(
            or_(*filters)
        ).order_by(Product.click_count.desc(), Product.created_at.desc()).limit(limit).all()

        return [
            {
                'id': d.id,
                'title': d.title,
                'slug': d.slug,
                'image_url': d.image_url,
                'discounted_price': d.formatted_discounted_price,
                'original_price': d.formatted_original_price,
                'discount_percentage': float(d.discount_percentage),
                'merchant_name': d.merchant.name if d.merchant else '',
                'category_name': d.category.name if d.category else '',
            }
            for d in deals
        ]

    @staticmethod
    def get_category_suggestions(query_str, limit=3):
        """
        Fast autocomplete category suggestions for the search bar.
        Returns matching active category objects with deal counts.
        Also maps common product query keywords to relevant categories.
        """
        if not query_str or not query_str.strip() or len(query_str.strip()) < 2:
            return []

        raw_query = query_str.strip().lower()
        cat_search_terms = {raw_query}

        # Keyword to category hints
        keyword_category_map = {
            'kurt': ['Fashion', 'Ethnic', 'Clothing'],
            'kurti': ['Fashion', 'Ethnic', 'Clothing'],
            'kurta': ['Fashion', 'Ethnic', 'Clothing'],
            'saree': ['Fashion', 'Ethnic', 'Clothing'],
            'dress': ['Fashion', 'Clothing'],
            'jeans': ['Fashion', 'Clothing'],
            'headphon': ['Audio', 'Electronics'],
            'headphone': ['Audio', 'Electronics'],
            'earbuds': ['Audio', 'Electronics'],
            'laptop': ['Electronics', 'Computers'],
            'mobil': ['Mobiles', 'Phones'],
            'mobile': ['Mobiles', 'Phones'],
            'phone': ['Mobiles', 'Phones'],
            'watch': ['Watch', 'Wearables']
        }

        stem = ProductService._stem_word(raw_query)
        if stem in keyword_category_map:
            cat_search_terms.update(keyword_category_map[stem])
        elif raw_query in keyword_category_map:
            cat_search_terms.update(keyword_category_map[raw_query])

        cat_filters = [Category.name.ilike(f"%{t}%") for t in cat_search_terms]

        categories = Category.query.filter(
            Category.is_active.is_(True),
            or_(*cat_filters)
        ).order_by(Category.display_order.asc(), Category.name.asc()).limit(limit).all()

        counts = ProductService.get_category_product_counts()
        return [
            {
                'id': c.id,
                'name': c.name,
                'slug': c.slug,
                'icon': c.icon or 'bi-tag',
                'deals_count': counts.get(c.id, 0)
            }
            for c in categories
        ]

    @staticmethod
    def get_featured_deals(limit=8, exclude_ids=None):
        """Retrieve active featured deals, with optional deduplication."""
        query = ProductService.get_active_deal_base_query().filter(Product.is_featured.is_(True))
        if exclude_ids:
            filtered = query.filter(Product.id.notin_(exclude_ids)).order_by(Product.created_at.desc(), Product.id.desc()).limit(limit).all()
            if len(filtered) >= min(limit, 3):
                return filtered
        return query.order_by(Product.created_at.desc(), Product.id.desc()).limit(limit).all()

    @staticmethod
    def get_trending_deals(limit=8, exclude_ids=None):
        """Retrieve active trending deals ordered by click count and date, with optional deduplication."""
        query = ProductService.get_active_deal_base_query().filter(
            or_(Product.is_trending.is_(True), Product.click_count > 0)
        )
        if exclude_ids:
            filtered = query.filter(Product.id.notin_(exclude_ids)).order_by(Product.click_count.desc(), Product.created_at.desc(), Product.id.desc()).limit(limit).all()
            if len(filtered) >= min(limit, 3):
                return filtered
        return query.order_by(Product.click_count.desc(), Product.created_at.desc(), Product.id.desc()).limit(limit).all()

    @staticmethod
    def get_latest_deals(limit=12, exclude_ids=None):
        """Retrieve the latest active deals, with optional deduplication."""
        query = ProductService.get_active_deal_base_query()
        if exclude_ids:
            filtered = query.filter(Product.id.notin_(exclude_ids)).order_by(Product.created_at.desc(), Product.id.desc()).limit(limit).all()
            if len(filtered) >= min(limit, 3):
                return filtered
        return query.order_by(Product.created_at.desc(), Product.id.desc()).limit(limit).all()

    @staticmethod
    def get_best_discount_deals(limit=8, exclude_ids=None):
        """Retrieve active deals with the highest authentic discounts, with optional deduplication."""
        query = ProductService.get_active_deal_base_query()
        if exclude_ids:
            filtered = query.filter(Product.id.notin_(exclude_ids)).order_by(Product.discount_percentage.desc(), Product.created_at.desc(), Product.id.desc()).limit(limit).all()
            if len(filtered) >= min(limit, 3):
                return filtered
        return query.order_by(Product.discount_percentage.desc(), Product.created_at.desc(), Product.id.desc()).limit(limit).all()

    @staticmethod
    def get_popular_deals(limit=8):
        """
        Retrieve popular deals only if genuine click tracking data exists (> 0).
        Returns empty list if no genuine clicks are recorded.
        """
        return ProductService.get_active_deal_base_query().filter(
            Product.click_count > 0
        ).order_by(Product.click_count.desc(), Product.created_at.desc(), Product.id.desc()).limit(limit).all()

    @staticmethod
    def get_related_deals(product, limit=4):
        """
        Relevance-based related deals discovery algorithm:
        1. Base pool: Active, published, non-expired deals excluding current product.
        2. Relevance scoring:
           - Same category: +10 pts
           - Matching root stems and title keywords: +6 pts per matching term
           - Same merchant: +3 pts
           - Price proximity (within 35%): +3 pts, (within 60%): +1 pt
           - High discount rate: +2 pts
        3. Ordered by relevance score descending, clicks desc, discount desc.
        4. Guaranteed fallback: If fewer than limit items match, populates from top active deals.
        """
        if not product or not product.id:
            return []

        base_query = ProductService.get_active_deal_base_query().filter(Product.id != product.id)

        # Extract significant title keywords & root stems
        stop_words = {
            'with', 'and', 'for', 'the', 'in', 'of', 'to', 'a', 'an', 'at', 'by', 'from',
            'off', 'pro', 'max', 'plus', 'edition', 'black', 'white', 'grey', 'new', 'latest',
            'pack', 'size', 'color', 'brand', 'combo', 'free', 'online', 'special', 'best'
        }
        title_words = set()
        title_stems = set()
        if product.title:
            raw_tokens = re.findall(r'[a-zA-Z0-9]+', product.title.lower())
            for t in raw_tokens:
                if len(t) >= 3 and t not in stop_words:
                    title_words.add(t)
                    title_stems.add(ProductService._stem_word(t))

        # 1. Fetch candidate pool
        same_cat_candidates = []
        if product.category_id:
            same_cat_candidates = base_query.filter(Product.category_id == product.category_id).all()

        other_candidates = []
        other_query = base_query
        if product.category_id:
            other_query = other_query.filter(Product.category_id != product.category_id)
        other_candidates = other_query.order_by(Product.click_count.desc(), Product.discount_percentage.desc()).limit(20).all()

        candidates = list({c.id: c for c in (same_cat_candidates + other_candidates)}.values())
        if not candidates:
            return []

        ref_price = float(product.discounted_price) if product.discounted_price else 0.0

        def score_candidate(cand):
            score = 0
            # Same Category Match
            if product.category_id and cand.category_id == product.category_id:
                score += 10

            # Title Keyword and Root Stem Matches
            if cand.title and (title_words or title_stems):
                cand_raw = re.findall(r'[a-zA-Z0-9]+', cand.title.lower())
                cand_words = set(cand_raw)
                cand_stems = {ProductService._stem_word(w) for w in cand_raw}

                word_matches = title_words.intersection(cand_words)
                stem_matches = title_stems.intersection(cand_stems)
                total_matches = len(word_matches.union(stem_matches))
                score += total_matches * 6

            # Same Merchant
            if product.merchant_id and cand.merchant_id == product.merchant_id:
                score += 3

            # Price Proximity
            cand_price = float(cand.discounted_price) if cand.discounted_price else 0.0
            if ref_price > 0 and cand_price > 0:
                diff_ratio = abs(cand_price - ref_price) / ref_price
                if diff_ratio <= 0.35:
                    score += 3
                elif diff_ratio <= 0.60:
                    score += 1

            # Discount percentage tie-breaker
            discount = float(cand.discount_percentage or 0)
            if discount >= 40:
                score += 2

            clicks = cand.click_count or 0
            return (score, clicks, discount, cand.created_at or datetime.min)

        ranked = sorted(candidates, key=score_candidate, reverse=True)
        top_picks = [c for c in ranked if score_candidate(c)[0] > 0]

        # If not enough scored items, fallback to top deals to ensure full recommendations
        if len(top_picks) < limit:
            picked_ids = {c.id for c in top_picks}
            for c in ranked:
                if c.id not in picked_ids:
                    top_picks.append(c)
                    picked_ids.add(c.id)
                if len(top_picks) >= limit:
                    break

        return top_picks[:limit]

    @staticmethod
    def get_related_deals_heading(product):
        """
        Generates a contextual dynamic heading for related products below the detail page.
        e.g., 'More Kurtis & Ethnic Wear You May Love', 'More Headphones & Audio Gear You May Love'
        """
        if not product:
            return "Handpicked Similar Deals You May Love"

        title_lower = (product.title or '').lower()

        # Specific recognized fashion & consumer categories
        if any(w in title_lower for w in ['kurti', 'kurtis', 'kurta', 'kurtas', 'anarkali']):
            return "More Kurtis & Ethnic Wear You May Love"
        if any(w in title_lower for w in ['saree', 'sarees', 'sari', 'saris']):
            return "More Sarees & Traditional Wear You May Love"
        if any(w in title_lower for w in ['headphone', 'headphones', 'earbud', 'earbuds', 'audio', 'earphone', 'rockerz']):
            return "More Headphones & Audio Gear You May Love"
        if any(w in title_lower for w in ['watch', 'watches', 'smartwatch', 'smartwatches']):
            return "More Watches & Wearables You May Love"
        if any(w in title_lower for w in ['shoe', 'shoes', 'sneaker', 'sneakers', 'sandals']):
            return "More Footwear & Shoes Deals You May Love"
        if any(w in title_lower for w in ['laptop', 'laptops', 'macbook', 'notebook']):
            return "More Laptops & Computing Deals You May Love"
        if any(w in title_lower for w in ['mobile', 'smartphone', 'phone', 'oneplus', 'iphone', 'samsung']):
            return "More Smartphones & Mobile Deals You May Love"

        if product.category and product.category.name:
            return f"More {product.category.name} Deals You May Love"

        return "Handpicked Similar Deals You May Love"

    @staticmethod
    def get_deal_by_slug(slug):
        """Retrieve a product by its unique slug."""
        if not slug:
            return None
        return Product.query.filter_by(slug=slug).first()

    @staticmethod
    def get_deal_by_id_or_slug(identifier):
        """Retrieve a product by slug or numeric ID."""
        if not identifier:
            return None
        if str(identifier).isdigit():
            prod = db.session.get(Product, int(identifier))
            if prod:
                return prod
        return Product.query.filter_by(slug=str(identifier)).first()

    @staticmethod
    def get_homepage_stats():
        """Get live statistics for homepage counter/trust badges."""
        now = datetime.now(timezone.utc)
        total_deals = Product.query.filter(
            Product.is_published.is_(True),
            Product.is_available.is_(True),
            Product.is_expired.is_(False),
            or_(Product.expiry_date.is_(None), Product.expiry_date > now)
        ).count()
        total_categories = Category.query.filter_by(is_active=True).count()
        total_merchants = Merchant.query.filter_by(is_active=True).count()

        return {
            'total_deals': total_deals,
            'total_categories': total_categories,
            'total_merchants': total_merchants,
        }

    @staticmethod
    def get_admin_dashboard_stats():
        """
        Calculates live database statistics for the Administrator Control Panel:
        - Total products
        - Published products
        - Draft or unpublished products
        - Expired deals
        - Number of categories
        - Number of merchants
        - Outbound product clicks
        """
        now = datetime.now(timezone.utc)
        total_products = Product.query.count()
        published_products = Product.query.filter_by(is_published=True).count()
        unpublished_products = Product.query.filter_by(is_published=False).count()
        expired_deals = Product.query.filter(
            or_(
                Product.is_expired.is_(True),
                and_(Product.expiry_date.isnot(None), Product.expiry_date <= now)
            )
        ).count()
        total_categories = Category.query.count()
        total_merchants = Merchant.query.count()

        from models import OutboundClick
        outbound_clicks_count = OutboundClick.query.count()
        sum_product_clicks = db.session.query(func.sum(Product.click_count)).scalar() or 0
        total_clicks = max(outbound_clicks_count, int(sum_product_clicks))

        return {
            'total_products': total_products,
            'published_products': published_products,
            'unpublished_products': unpublished_products,
            'expired_deals': expired_deals,
            'total_categories': total_categories,
            'total_merchants': total_merchants,
            'total_clicks': total_clicks,
            'total_deals': published_products,
        }
