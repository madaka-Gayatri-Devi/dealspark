# DealSpark — Real-Time Deals and Affiliate Shopping Platform

DealSpark is a responsive full-stack web application inspired by DealsSpy.in that enables shoppers to discover verified online shopping deals, track price changes, inspect authentic discount calculations, and purchase through affiliate links.

---

## 🚀 Phase 1 Implementation Summary

Phase 1 establishes the foundational architecture and a responsive homepage:
1. **Flask Application Factory & Modular Architecture**:
   - `app.py`: Application factory with extension initialization, context processors, CLI commands, and centralized error handling (400, 403, 404, 500).
   - `config.py`: Environment-aware configurations (Development, Testing, Production) supporting MySQL and local development fallback.
   - Blueprints registered: `main` (public pages), `auth` (authentication), `admin` (management), and `affiliate` (secure outbound tracking).
2. **Database Models (MySQL & SQLAlchemy ORM)**:
   - `User`: Roles (`admin`, `user`), password hashing, and Flask-Login integration.
   - `Category`: Categories with auto-generated slugs and display ordering.
   - `Merchant`: Partner merchants (Amazon, Flipkart, Myntra, etc.) with domain mapping and color badges.
   - `Product`: Complete pricing model with automatic savings and discount percentage calculation:
     $$\text{Savings} = \text{Original Price} - \text{Discounted Price}$$
     $$\text{Discount \%} = \left(\frac{\text{Savings}}{\text{Original Price}}\right) \times 100$$
   - `ProductPriceHistory`: Historical price tracking.
   - `OutboundClick`: Outbound click analytics with IP hashing for privacy compliance.
   - `Favorite`: User deal bookmarks.
3. **Frontend UI/UX**:
   - Clean white and light-grey backgrounds (`#f8fafc`, `#ffffff`) with an orange primary brand accent (`#ff5722`) and green savings labels (`#16a34a`).
   - Sticky navbar with brand logo, search bar, category dropdown, and mobile menu.
   - Modern hero banner with value proposition and real-time trust metrics.
   - Verified merchant badge showcase (Amazon India, Flipkart, Myntra, Ajio, Croma, Tata CLiQ).
   - Reusable deal card component with discount badge, strikethrough original price, savings tag, and Buy Now redirect button.
   - Professional empty state (no fake mock deals generated).
   - Toast notification system and WhatsApp / deal link sharing.
4. **Testing**:
   - 15 automated pytest unit tests covering configuration, pricing math, edge cases (zero division, negative price protection), models, and homepage routes.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3.3, Bootstrap Icons
- **Backend**: Python Flask 3.0+
- **Database**: MySQL 8.0+ (with SQLite fallback for local test environments)
- **ORM**: Flask-SQLAlchemy 3.1+
- **Authentication**: Flask-Login, Werkzeug Security
- **Forms & Security**: Flask-WTF, CSRF protection, URL whitelist validation
- **Testing**: pytest

---

## 📁 Project Structure

```
DealSpark/
├── app.py                      # Application Factory (create_app) & CLI commands
├── config.py                   # Development, Testing, and Production Config
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .env                        # Local environment configuration
├── models/
│   ├── __init__.py             # db, login_manager, and model exports
│   ├── user.py                 # User & roles model
│   ├── category.py             # Category model
│   ├── merchant.py             # Merchant model
│   ├── product.py              # Product model with pricing arithmetic
│   ├── price_history.py        # Price history model
│   ├── click.py                # Outbound click analytics model
│   └── favorite.py             # User favorites model
├── routes/
│   ├── __init__.py             # Blueprints registration
│   ├── main.py                 # Homepage, categories, search, error handlers
│   ├── auth.py                 # Auth blueprint
│   ├── admin.py                # Admin blueprint
│   └── affiliate.py            # Secure outbound redirect & click tracking
├── services/
│   ├── __init__.py
│   ├── product_service.py      # Deal queries and homepage aggregation
│   └── click_service.py        # Outbound click recording and domain whitelist check
├── templates/
│   ├── base.html               # Base layout with Bootstrap 5
│   ├── index.html              # Homepage
│   ├── search.html             # Search page
│   ├── about.html              # About DealSpark page
│   ├── disclaimer.html         # Affiliate & pricing disclosure
│   ├── includes/
│   │   ├── navbar.html         # Navbar with search & categories
│   │   ├── hero.html           # Hero banner & trust badges
│   │   ├── deal_card.html      # Reusable deal card component
│   │   └── footer.html         # Footer with legal disclaimers
│   ├── auth/
│   │   ├── login.html          # Login view
│   │   └── register.html       # Register view
│   ├── admin/
│   │   └── dashboard.html      # Admin dashboard view
│   └── errors/
│       ├── 400.html
│       ├── 403.html
│       ├── 404.html
│       └── 500.html
├── static/
│   ├── css/
│   │   └── styles.css          # DealSpark custom styling
│   ├── js/
│   │   └── main.js             # Share deals, copy link, toasts
│   └── images/
│       └── logo.svg            # DealSpark logo
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_config.py          # Configuration tests
│   ├── test_home.py            # Route & UI tests
│   └── test_models.py          # Arithmetic & model tests
└── scripts/
    ├── __init__.py
    ├── init_db.py              # Database seeding script
    └── create_admin.py         # Admin user creation utility
```

---

## 💻 Exact Commands to Run

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Initialize the Database and Seed Categories
```powershell
flask init-db
```

### 3. Initialize the Single Authorized Administrator Account
Configure your environment variables in `.env`:
```powershell
ADMIN_EMAIL=nagarajuchaintala2002@gmail.com
ADMIN_INITIAL_PASSWORD=YourSecureAdminPassword2026!
```
Then run the secure initialization script:
```powershell
python scripts/create_admin.py
```
*(Or via CLI: `flask create-admin`)*
- If the authorized administrator already exists, it will NOT reset the password.
- No public user registration can create an admin account.

### 4. Run the Automated Tests (26 Tests)
```powershell
pytest -v
```

### 5. Verify Full Auth Flow with End-to-End Verification
```powershell
python scripts/verify_auth_flow.py
```

### 6. Start the Development Server
```powershell
python app.py
```
Open your browser at `http://127.0.0.1:5000`.
