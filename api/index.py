import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

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
    WSGI middleware that parses the captured route parameter '__path'
    from Vercel's rewrite rule into Flask's PATH_INFO, and cleans the query string.
    """
    query_str = environ.get('QUERY_STRING', '')
    if '__path' in query_str:
        params = parse_qs(query_str, keep_blank_values=True)
        raw_path = params.pop('__path', [''])[0]
        if not raw_path or raw_path == '/':
            environ['PATH_INFO'] = '/'
        else:
            environ['PATH_INFO'] = f"/{raw_path}" if not raw_path.startswith('/') else raw_path
        environ['QUERY_STRING'] = urlencode(params, doseq=True)

    return original_wsgi_app(environ, start_response)


app.wsgi_app = vercel_path_fixer
