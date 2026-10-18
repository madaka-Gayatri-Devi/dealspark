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
flask_app = create_app(env_name)


class VercelWSGIWrapper:
    """
    WSGI middleware that strips '/api/index' from PATH_INFO if Vercel's rewrite engine
    passes the serverless destination path instead of the user's browser URI.
    """
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/api/index'):
            stripped = path[len('/api/index'):]
            environ['PATH_INFO'] = stripped if stripped.startswith('/') else f"/{stripped}"
            if not environ['PATH_INFO']:
                environ['PATH_INFO'] = '/'
        return self.application(environ, start_response)


# Vercel entrypoint looks for 'app'
app = VercelWSGIWrapper(flask_app)
