"""
settings.py — Main configuration for the Quiz API project.

Django reads this file at startup to know how to run your project:
database, installed apps, middleware, authentication, etc.
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────────
# BASE DIRECTORY
# ─────────────────────────────────────────────
# Build paths inside the project like: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────
# Secret key used to sign cookies, tokens, etc.
# NEVER share this. Keep it in .env in production.
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")

# DEBUG=True shows detailed error pages. Set to False in production.
DEBUG = os.getenv("DEBUG", "True") == "True"

# Which hostnames are allowed to serve this app
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ─────────────────────────────────────────────
# INSTALLED APPS
# ─────────────────────────────────────────────
# All apps that Django should load
INSTALLED_APPS = [
    "django.contrib.admin",          # Built-in admin panel
    "django.contrib.auth",           # Built-in user authentication
    "django.contrib.contenttypes",   # Framework for content types
    "django.contrib.sessions",       # Session framework
    "django.contrib.messages",       # Messaging framework
    "django.contrib.staticfiles",    # Static file handling

    # Third-party packages
    "rest_framework",                # Django REST Framework (DRF) — builds our API
    "rest_framework_simplejwt",      # JWT token authentication
    "corsheaders",                   # Allow frontend (browser) to call our API

    # Our custom apps
    "apps.users",                    # User registration, login, profiles
    "apps.quiz",                     # Quiz, questions, attempts
    "apps.analytics",                # Quiz results and performance tracking
]

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────
# Middleware = functions that run on every request/response, in order
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # Must be first — handles CORS headers
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",      # Serves static files efficiently
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "quiz_project.urls"   # Where Django looks for URL patterns

# ─────────────────────────────────────────────
# TEMPLATES (for Django admin)
# ─────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quiz_project.wsgi.application"

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
# Uses DATABASE_URL env variable if set (for production/Railway/Heroku),
# otherwise falls back to local PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/quiz_db"
        ),
        conn_max_age=600,   # Keep DB connections open for 10 minutes (performance)
    )
}

# ─────────────────────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─────────────────────────────────────────────
# LOCALIZATION
# ─────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True   # Always store dates in UTC

# ─────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Where collectstatic puts files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─────────────────────────────────────────────
# CUSTOM USER MODEL
# ─────────────────────────────────────────────
# We use our own User model instead of Django's default
AUTH_USER_MODEL = "users.User"

# ─────────────────────────────────────────────
# DJANGO REST FRAMEWORK SETTINGS
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    # Default: all API endpoints require a logged-in user
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Pagination: return 10 items per page by default
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    # Throttling: rate limiting to prevent abuse
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",    # For unauthenticated users
        "rest_framework.throttling.UserRateThrottle",    # For authenticated users
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",    # Anonymous users: 20 requests per hour
        "user": "200/hour",   # Logged-in users: 200 requests per hour
    },
}

# ─────────────────────────────────────────────
# JWT TOKEN SETTINGS
# ─────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),     # Access token expires in 1 hour
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),     # Refresh token expires in 7 days
    "ROTATE_REFRESH_TOKENS": True,                   # Issue new refresh token on refresh
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),                # Authorization: Bearer <token>
}

# ─────────────────────────────────────────────
# CORS SETTINGS
# ─────────────────────────────────────────────
# Allow all origins in dev. Restrict in production.
CORS_ALLOW_ALL_ORIGINS = DEBUG
_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()] if not DEBUG else []
# ─────────────────────────────────────────────
# CACHE SETTINGS (simple in-memory cache)
# ─────────────────────────────────────────────
# For production, replace with Redis:
# CACHES = { "default": { "BACKEND": "django_redis.cache.RedisCache", ... } }
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "quiz-cache",
    }
}

# ─────────────────────────────────────────────
# AI SERVICE SETTINGS
# ─────────────────────────────────────────────
# We use Google Gemini (free tier). Get your key at: https://aistudio.google.com
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://api.groq.com/openai/v1/chat/completions"
AI_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
