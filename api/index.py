import json
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
    WSGI middleware that normalizes PATH_INFO and SCRIPT_NAME for Vercel Serverless.
    """
    query_str = environ.get('QUERY_STRING', '')
    if 'inspect_wsgi=1' in query_str:
        start_response('200 OK', [('Content-Type', 'application/json')])
        env_debug = {
            'PATH_INFO': environ.get('PATH_INFO'),
            'SCRIPT_NAME': environ.get('SCRIPT_NAME'),
            'QUERY_STRING': environ.get('QUERY_STRING'),
            'RAW_URI': environ.get('RAW_URI'),
            'REQUEST_URI': environ.get('REQUEST_URI'),
            'HTTP_X_FORWARDED_PATH': environ.get('HTTP_X_FORWARDED_PATH'),
            'HTTP_X_MATCHED_PATH': environ.get('HTTP_X_MATCHED_PATH'),
        }
        return [json.dumps(env_debug, indent=2).encode('utf-8')]

    # Reset SCRIPT_NAME so Flask treats root path correctly
    environ['SCRIPT_NAME'] = ''

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
