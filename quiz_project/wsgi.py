"""
wsgi.py — Entry point for WSGI-compatible web servers (Gunicorn, uWSGI).
Used when deploying to production (Heroku, Railway, etc.).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quiz_project.settings")

application = get_wsgi_application()
