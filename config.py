import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


def get_database_uri():
    """
    Constructs the database URI.
    Prioritizes DATABASE_URL if explicitly set.
    Otherwise builds from MySQL connection parameters.
    Falls back to SQLite only in local dev when explicitly permitted and MySQL password is not configured.
    """
    database_url = os.getenv('DATABASE_URL', '').strip()
    if database_url:
        return database_url

    # Check for individual MySQL configuration variables
    db_user = os.getenv('DB_USER', 'root').strip()
    db_pass = os.getenv('DB_PASSWORD', '').strip()
    db_host = os.getenv('DB_HOST', 'localhost').strip()
    db_port = os.getenv('DB_PORT', '3306').strip()
    db_name = os.getenv('DB_NAME', 'dealspark').strip()

    # In serverless environments like Vercel, if DATABASE_URL is not set,
    # safely use temp SQLite to avoid fatal crashes trying to connect to localhost:3306
    if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        import tempfile
        tmp_db = Path(tempfile.gettempdir()) / 'dealspark.db'
        return f"sqlite:///{tmp_db}"

    flask_env = os.getenv('FLASK_ENV', 'development').strip().lower()
    default_fallback = 'false' if flask_env == 'production' else 'true'
    allow_fallback = os.getenv('DB_ALLOW_SQLITE_FALLBACK', default_fallback).lower() in ('true', '1', 'yes')

    # In local development, if fallback is permitted and MySQL password is not set
    if allow_fallback and flask_env != 'production' and not db_pass:
        instance_dir = BASE_DIR / 'instance'
        instance_dir.mkdir(exist_ok=True)
        return f"sqlite:///{instance_dir / 'dealspark.db'}"

    # Build MySQL connection URI
    auth = f"{db_user}:{db_pass}" if db_pass else db_user
    return f"mysql+pymysql://{auth}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dealspark-dev-insecure-key-replace-me')
    APP_NAME = os.getenv('APP_NAME', 'DealSpark')
    APP_URL = os.getenv('APP_URL', 'http://127.0.0.1:5000')

    # Single Authorized Administrator
    AUTHORIZED_ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com').strip().lower()

    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 1 day

    # Affiliate Tracking & Allowed Redirect Domains
    ALLOWED_REDIRECT_DOMAINS = [
        d.strip().lower() for d in os.getenv(
            'ALLOWED_REDIRECT_DOMAINS',
            'amazon.in,amzn.to,flipkart.com,fkrt.it,myntra.com,ajio.com,croma.com,reliancedigital.in,tatacliq.com'
        ).split(',') if d.strip()
    ]

    # Authorized Product Import Providers Configuration
    AMAZON_PAAPI_ACCESS_KEY = os.getenv('AMAZON_PAAPI_ACCESS_KEY', '').strip()
    AMAZON_PAAPI_SECRET_KEY = os.getenv('AMAZON_PAAPI_SECRET_KEY', '').strip()
    AMAZON_ASSOCIATE_TAG = os.getenv('AMAZON_ASSOCIATE_TAG', '').strip()
    AMAZON_REGION = os.getenv('AMAZON_REGION', 'eu-west-1').strip()

    FLIPKART_AFFILIATE_ID = os.getenv('FLIPKART_AFFILIATE_ID', '').strip()
    FLIPKART_AFFILIATE_TOKEN = os.getenv('FLIPKART_AFFILIATE_TOKEN', '').strip()

    # Pagination
    DEALS_PER_PAGE = 12


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False}
    }


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Enforce MySQL in production
    @classmethod
    def init_app(cls, app):
        Config.init_app(app) if hasattr(Config, 'init_app') else None
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri or not db_uri.startswith('mysql'):
            app.logger.warning("Production mode should use MySQL database! Found: %s", db_uri)


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
