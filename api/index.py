import os
import sys
from pathlib import Path

# Add project root directory to sys.path so models, routes, and services resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app

# Instantiate Flask application for Vercel Serverless execution
env_name = os.getenv('FLASK_ENV', 'production')
app = create_app(env_name)

original_wsgi_app = app.wsgi_app


def vercel_path_fixer(environ, start_response):
    """
    WSGI middleware that inspects Vercel's incoming request headers
    (HTTP_X_VERCEL_URI, HTTP_X_MATCHED_PATH, REQUEST_URI)
    to restore the true browser route and query parameters on Flask.
    """
    raw_uri = (
        environ.get('HTTP_X_VERCEL_URI') or
        environ.get('HTTP_X_MATCHED_PATH') or
        environ.get('REQUEST_URI') or
        environ.get('PATH_INFO', '')
    )

    if raw_uri and not raw_uri.startswith('/api/index'):
        path_only = raw_uri.split('?')[0]
        environ['PATH_INFO'] = path_only if path_only.startswith('/') else f"/{path_only}"
        if '?' in raw_uri:
            environ['QUERY_STRING'] = raw_uri.split('?', 1)[1]
    elif raw_uri.startswith('/api/index'):
        stripped = raw_uri[len('/api/index'):].split('?')[0]
        environ['PATH_INFO'] = stripped if stripped.startswith('/') else (f"/{stripped}" if stripped else '/')
        if '?' in raw_uri:
            environ['QUERY_STRING'] = raw_uri.split('?', 1)[1]

    return original_wsgi_app(environ, start_response)


app.wsgi_app = vercel_path_fixer
