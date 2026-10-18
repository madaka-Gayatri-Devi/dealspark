import pytest
from app import create_app
from models import db, Category, Merchant


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Seed minimal baseline categories and merchants for testing
        cat = Category(name='Electronics', icon='bi-laptop', description='Gadgets & Tech', display_order=1)
        merch = Merchant(name='Amazon India', domain='amazon.in', badge_color='#ff9900')
        db.session.add_all([cat, merch])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
