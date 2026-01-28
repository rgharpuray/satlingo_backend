"""
Django settings for satlingo project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
import sentry_sdk
import posthog

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Default to True for local development, False for production
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'nested_admin',
    'api',
    'web',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'api.middleware.DisableCSRFForAPI',  # Disable CSRF for API endpoints
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CSRF settings - exempt API endpoints
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS

ROOT_URLCONF = 'satlingo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'satlingo.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600
    )
}

# Improve SQLite concurrency settings
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS'] = {
        'timeout': 20,  # Wait up to 20 seconds for database to unlock
        'check_same_thread': False,  # Allow connections from different threads
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional locations of static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration for static files (only in production)
# Only add WhiteNoise middleware and storage in production
if not DEBUG:
    # Insert WhiteNoise middleware after SecurityMiddleware
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    # Use WhiteNoise storage for compressed static files in production
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    # In development, use default storage
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'api.User'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Most endpoints are public
    ],
}

# Disable CSRF for API views (DRF handles this, but ensure it's explicit)
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Stripe Settings
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', '')  # Monthly subscription price ID

# Premium Settings
PREMIUM_MONTHLY_PRICE = 5.00  # $5 per month

# OpenAI Settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# AWS S3 Settings for diagram storage (used when USE_GCS is False; keep during migration)
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')

# Google Cloud Storage (GCS) – used when USE_GCS is True
GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME', '')
GS_PROJECT_ID = os.environ.get('GS_PROJECT_ID', '')  # Optional if set in credentials JSON
# Heroku/non-file: set GOOGLE_APPLICATION_CREDENTIALS_JSON to the full JSON key (one line)
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '')
USE_GCS = bool(GS_BUCKET_NAME and GOOGLE_APPLICATION_CREDENTIALS_JSON)

# Google OAuth Settings
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get('GOOGLE_OAUTH_REDIRECT_URI', '')
# iOS Google Client ID (for token verification from iOS app)
GOOGLE_OAUTH_IOS_CLIENT_ID = os.environ.get(
    'GOOGLE_OAUTH_IOS_CLIENT_ID', 
    '412415832820-s8dqgts2es0mtbc7efkqjui5l5ed2sgk.apps.googleusercontent.com'
)
# Android Google Client ID (for token verification from Android app)
GOOGLE_OAUTH_ANDROID_CLIENT_ID = os.environ.get(
    'GOOGLE_OAUTH_ANDROID_CLIENT_ID', 
    '412415832820-kdps9c4s09r15fvp42rcbini75ptslu7.apps.googleusercontent.com'
)

# Apple App Store Settings (for iOS in-app purchases)
APPLE_BUNDLE_ID = os.environ.get('APPLE_BUNDLE_ID', 'com.keuvi.app')
# Audiences accepted for Apple Sign In: web (com.keuvi.app), iOS app (pro.argosventures.keuvi). Comma-separated if set via env.
_apple_audiences = os.environ.get('APPLE_ALLOWED_AUDIENCES', 'com.keuvi.app,pro.argosventures.keuvi')
APPLE_ALLOWED_AUDIENCES = [x.strip() for x in _apple_audiences.split(',') if x.strip()]
APPLE_SHARED_SECRET = os.environ.get('APPLE_SHARED_SECRET', '')  # For receipt verification
APPLE_APP_STORE_KEY_ID = os.environ.get('APPLE_APP_STORE_KEY_ID', '')  # For App Store Server API
APPLE_APP_STORE_ISSUER_ID = os.environ.get('APPLE_APP_STORE_ISSUER_ID', '')
APPLE_APP_STORE_PRIVATE_KEY = os.environ.get('APPLE_APP_STORE_PRIVATE_KEY', '')  # Base64 encoded .p8 key

# Sentry Settings (Error Tracking)
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
        traces_sample_rate=0.1 if not DEBUG else 1.0,
        # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions
        profiles_sample_rate=0.1 if not DEBUG else 1.0,
        # Send PII (user info) to Sentry
        send_default_pii=True,
        # Environment tag
        environment='development' if DEBUG else 'production',
    )

# PostHog Settings (Analytics)
POSTHOG_API_KEY = os.environ.get('POSTHOG_API_KEY', '')
POSTHOG_HOST = os.environ.get('POSTHOG_HOST', 'https://us.i.posthog.com')
if POSTHOG_API_KEY:
    posthog.project_api_key = POSTHOG_API_KEY
    posthog.host = POSTHOG_HOST
    posthog.debug = DEBUG

# Argos Control Settings (Monitoring)
ARGOS_TOKEN = os.environ.get('ARGOS_TOKEN', '')
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'satlingo-backend')
VERSION = os.environ.get('VERSION', '1.0.0')
