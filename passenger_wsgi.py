"""
DealSpark - cPanel Phusion Passenger WSGI Entry Point
For GoDaddy Linux Hosting with cPanel 'Setup Python App'.
"""
import sys
import os

# Add application directory to sys.path
APP_DIR = os.path.dirname(__file__)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from wsgi import application  # Passenger automatically picks up 'application'
