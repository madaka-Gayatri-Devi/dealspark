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

# Attach WSGI middleware to app.wsgi_app to normalize PATH_INFO for Vercel rewrites
original_wsgi_app = app.wsgi_app


def vercel_wsgi_middleware(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path.startswith('/api/index'):
        stripped = path[len('/api/index'):]
        if not stripped or stripped == '/':
            environ['PATH_INFO'] = '/'
        else:
            environ['PATH_INFO'] = stripped if stripped.startswith('/') else f"/{stripped}"
        environ['REQUEST_URI'] = environ['PATH_INFO']
        environ['RAW_URI'] = environ['PATH_INFO']
    return original_wsgi_app(environ, start_response)


app.wsgi_app = vercel_wsgi_middleware
