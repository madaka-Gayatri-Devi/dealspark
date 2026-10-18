from config import config_by_name, DevelopmentConfig, TestingConfig, ProductionConfig


def test_development_config():
    config = config_by_name['development']
    assert config.DEBUG is True
    assert config.TESTING is False
    assert config.WTF_CSRF_ENABLED is True


def test_testing_config():
    config = config_by_name['testing']
    assert config.TESTING is True
    assert config.DEBUG is False
    assert config.WTF_CSRF_ENABLED is False
    assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'


def test_allowed_redirect_domains():
    config = config_by_name['development']
    assert 'amazon.in' in config.ALLOWED_REDIRECT_DOMAINS
    assert 'flipkart.com' in config.ALLOWED_REDIRECT_DOMAINS
