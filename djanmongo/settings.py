import os
import dj_database_url
from pathlib import Path
from datetime import timedelta # Import timedelta
from os.path import join # <-- Add this

# Import config helper from djangoeditorwidgets
from djangoeditorwidgets.config import init_web_editor_config # <-- Add this

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-development-secret-key') # ADD this line, replace the placeholder

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True' # MODIFY this line (or add if missing)

# Get allowed hosts from env var, fallback for local dev
ALLOWED_HOSTS_STRING = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,palmer-kentucky-geological-dc.trycloudflare.com, lexmark-specialists-leone-legislation.trycloudflare.com') # ADD or MODIFY this
ALLOWED_HOSTS = ALLOWED_HOSTS_STRING.split(',') if ALLOWED_HOSTS_STRING else [] # MODIFY this line

# Application definition

INSTALLED_APPS = [
    'unfold',  # Required
    'unfold.contrib.filters',  # Optional - Better filters
    'unfold.contrib.forms',  # Optional - Consistent forms
    # 'unfold.contrib.import_export',  # Optional - Requires django-import-export
    # 'unfold.contrib.guardian',  # Optional - Requires django-guardian
    # 'unfold.contrib.simple_history', # Optional - Requires django-simple-history

    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Ensure this is still here

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'djangoeditorwidgets', # <-- Add this

    # Your apps
    'users.apps.UsersConfig',
    'game.apps.GameConfig',
]
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'middleware.update_last_seen.UpdateLastSeenMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Environment with DATABASE_URL (like Docker Compose, Render)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600, 
            # Only require SSL if explicitly set in URL or production context
            # ssl_require= not DEBUG # Example: Require SSL if not in DEBUG mode
            # Render requires SSL, so keep it if deploying there
            ssl_require=True if os.environ.get('RENDER') else False 
        )
    }
else:
    # Local development fallback (WITHOUT Docker Compose or without DATABASE_URL set)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'djanmongo_dev',
            'USER': 'djanmongo_user',
            'PASSWORD': 'djanmongo_password',
            'HOST': 'localhost', # Keep localhost for direct connection
            'PORT': '5433',      # Keep the original local port
        }
    }

# --- Custom User Model ---
AUTH_USER_MODEL = 'users.User'

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # Add standard validators if needed
]

# --- Django REST Framework Settings ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', # Adjust as needed
    )
}

# --- Simple JWT Settings ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Uses Django's SECRET_KEY by default
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Use environment variable for Gemini API Key, default to None if not set
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)

# --- CORS Settings ---
# Allow requests from the Vue development server
if DEBUG:
    # Allow Vite dev server origin during development
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173', # Adjust port if your Vite uses a different one
        'http://127.0.0.1:5173',
    ]
else:
    # Production: Get allowed origins from environment variable
    CORS_ALLOWED_ORIGINS_STRING = os.environ.get('CORS_ALLOWED_ORIGINS')
    print(f"Allowed origins:{CORS_ALLOWED_ORIGINS}")
    if CORS_ALLOWED_ORIGINS_STRING:
        CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_STRING.split(',')
    else:
        CORS_ALLOWED_ORIGINS = [] # Or set specific defaults if needed


STATIC_URL = 'static/'
# Add this for WhiteNoise if serving static files from Django/Gunicorn
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
# Optional: Add directories searched by collectstatic
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static_cdn'), # <-- Add directory for downloaded editors
]

# Add this if using WhiteNoise for simplified static file serving on Render
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Increase max number of POST/GET parameters to prevent TooManyFieldsSent error in admin
# Default is 1000
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000 

# --- Django Editor Widgets Config --- 
# Use helper for DOWNLOAD path definition
WEB_EDITOR_DOWNLOAD, _ = init_web_editor_config(
    BASE_DIR / "static_cdn", 
    STATIC_URL
)

# Manually define WEB_EDITOR_CONFIG to avoid double static prefix
# Paths should be relative to the STATIC_URL root
WEB_EDITOR_CONFIG = {
    "tinymce": { # Keep definition even if not used, might be needed by package
        "js": [
            "tinymce/tinymce.min.js",
            "djangoeditorwidgets/tinymce/tinymce.config.js",
            "djangoeditorwidgets/tinymce/tinymce.init.js",
        ],
        "css": {
            "all": [
                "djangoeditorwidgets/tinymce/tinymce.custom.css",
            ]
        },
    },
    "monaco": {
        "js": [
            "monaco/vs/loader.js", # Path relative to static root
            "djangoeditorwidgets/monaco/monaco.config.js",
        ],
        "css": {
            "all": [
                "djangoeditorwidgets/monaco/monaco.custom.css",
            ]
        },
    },
}

# --- Game Specific Settings ---
BASE_STARTING_HP = 100 # Example value
BASE_MOMENTUM = 0      # Default starting momentum

# --- Lua Integration ---
LUA_SCRIPT_PATH = BASE_DIR / 'game' / 'lua_scripts'
