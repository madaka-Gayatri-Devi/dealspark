import os
from datetime import datetime, timezone
import click
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

from config import config_by_name
from models import db, login_manager, User, Category, Merchant

csrf = CSRFProtect()
migrate = Migrate()


def create_app(config_name=None):
    """Flask Application Factory."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    cfg = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(cfg)
    if hasattr(cfg, 'init_app'):
        cfg.init_app(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    from routes import main_bp, auth_bp, admin_bp, affiliate_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(affiliate_bp)

    # Register error handlers
    register_error_handlers(app)

    # Context processors for templates
    @app.context_processor
    def inject_global_data():
        active_cats = []
        try:
            active_cats = Category.query.filter_by(is_active=True).order_by(
                Category.display_order.asc(), Category.name.asc()
            ).limit(10).all()
        except Exception:
            active_cats = []

        user_fav_ids = set()
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            try:
                from models import Favorite
                user_fav_ids = {f.product_id for f in Favorite.query.filter_by(user_id=current_user.id).all()}
            except Exception:
                pass

        return {
            'app_name': app.config.get('APP_NAME', 'DealSpark'),
            'current_year': datetime.now(timezone.utc).year,
            'nav_categories': active_cats,
            'user_fav_ids': user_fav_ids
        }

    # Template global helper to preserve query arguments across pagination and filters
    @app.template_global()
    def merge_query_args(**new_args):
        """Merges current request.args with new parameters, removing None or empty values."""
        from urllib.parse import urlencode
        from flask import request
        args = request.args.to_dict(flat=True)
        for k, v in new_args.items():
            if v is None or v == '':
                args.pop(k, None)
            else:
                args[k] = str(v)
        return urlencode(args)

    # Ensure database schema is up-to-date in non-testing environments
    if not app.config.get('TESTING'):
        with app.app_context():
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                if not tables or 'categories' not in tables:
                    db.create_all()
                    from scripts.init_db import run_seed
                    run_seed()
                    inspector = inspect(db.engine)
                    tables = inspector.get_table_names()
                if 'users' in tables:
                    u_cols = [col['name'] for col in inspector.get_columns('users')]
                    if 'full_name' not in u_cols:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) DEFAULT '' NOT NULL"))
                        db.session.commit()
                    if 'phone' not in u_cols:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT ''"))
                        db.session.commit()
                if 'products' in tables:
                    p_cols = [col['name'] for col in inspector.get_columns('products')]
                    if 'is_price_verified' not in p_cols:
                        db.session.execute(text("ALTER TABLE products ADD COLUMN is_price_verified BOOLEAN DEFAULT 0 NOT NULL"))
                        db.session.commit()
            except Exception:
                pass

    # Register CLI commands
    register_cli_commands(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        from flask import make_response, request
        resp = make_response(render_template('errors/404.html', error=error), 404)
        resp.headers['X-Debug-Path'] = request.path
        resp.headers['X-Debug-Url'] = request.url
        resp.headers['X-Debug-Script-Root'] = request.script_root
        return resp

    @app.errorhandler(500)
    def internal_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template('errors/500.html', error=error), 500


def register_cli_commands(app):
    @app.cli.command('init-db')
    def init_db():
        """Create database tables and seed baseline shopping categories and verified merchants."""
        from scripts.init_db import run_seed
        run_seed()
        click.echo("[OK] Database tables initialized and verified baseline categories and merchants seeded successfully.")

    @app.cli.command('create-admin')
    @click.option('--repair', is_flag=True, help='Synchronize password from ADMIN_INITIAL_PASSWORD')
    def create_admin(repair):
        """Create or verify the authorized administrator account."""
        from scripts.create_admin import initialize_admin
        initialize_admin(force_repair=repair)


# Application instance for flask run / gunicorn
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
