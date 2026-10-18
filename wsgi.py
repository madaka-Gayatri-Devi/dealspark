"""
DealSpark - WSGI Production Entry Point
Suitable for deployment with:
- Phusion Passenger (cPanel CloudLinux)
- Gunicorn / uWSGI (Linux VPS / Nginx)
- Waitress / mod_wsgi
"""
import os
import sys
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

from app import create_app

# Use production config unless explicitly overridden
environment = os.getenv('FLASK_ENV', 'production')
application = create_app(environment)
app = application

if __name__ == '__main__':
    # Never use debug=True in production WSGI execution
    port = int(os.getenv('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)
