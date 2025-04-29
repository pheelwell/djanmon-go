import os
import dj_database_url
from pathlib import Path
from datetime import timedelta  # Import timedelta
from os.path import join # <-- Add this
from dotenv import load_dotenv
# Import config helper from djangoeditorwidgets
from djangoeditorwidgets.config import init_web_editor_config # <-- Add this

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

print(f"BASE_DIR: {BASE_DIR}")
# print .env file:
envfile = os.path.join(BASE_DIR, '.env')

#load .env file:
load_dotenv(envfile)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-development-secret-key') # ADD this line, replace the placeholder

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True' # MODIFY this line (or add if missing)

# Get allowed hosts from env var, fallback for local dev
ALLOWED_HOSTS_STRING = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost') # ADD or MODIFY this
ALLOWED_HOSTS = ALLOWED_HOSTS_STRING.split(',') if ALLOWED_HOSTS_STRING else [] # MODIFY this line

# --- Application definition ---

INSTALLED_APPS = [
    'unfold',  # Required
    'unfold.contrib.filters',  # Optional - Better filters
    'unfold.contrib.forms',  # Optional - Consistent forms

    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Ensure this is still here

    # Third-party apps
    'rest_framework',
    'corsheaders',
    'djangoeditorwidgets', # <-- Add this
    'whitenoise', # Add whitenoise here too if not already
    'cachalot', # <-- ADD django-cachalot

    # Your apps
    'users.apps.UsersConfig',
    'game.apps.GameConfig',
]

MIDDLEWARE = [
    # SecurityMiddleware should come first or very early
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoiseMiddleware should come right after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    # CORS Middleware should come relatively early, typically before CommonMiddleware
    'corsheaders.middleware.CorsMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Add the frontend build index.html directory if you need Django templates to see it
        # 'DIRS': [os.path.join(BASE_DIR, '..', 'frontend_dist')], 
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wsgi.application"

# --- Database Configuration ---

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
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT", "5432")  # Default to 5432
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_PORT: {DB_PORT}")
    print(f"DB_NAME: {DB_NAME}")
    print(f"DB_USER: {DB_USER}")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
        }}

AUTH_USER_MODEL = 'users.User'

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # Add standard validators if needed
]

# --- Django REST Framework Settings ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # Optionally keep BasicAuthentication for browsable API:
        # 'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', # Adjust as needed
    )
}

# Use environment variable for Gemini API Key, default to None if not set
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)

# --- Gemini Model Configuration ---
# Model used for generating game attacks
GEMINI_ATTACK_GENERATION_MODEL = os.environ.get('GEMINI_ATTACK_GENERATION_MODEL', 'gemini-2.5-flash')
# Model used for generating profile picture prompts
GEMINI_PROFILE_PROMPT_MODEL = os.environ.get('GEMINI_PROFILE_PROMPT_MODEL', 'gemini-2.5-flash')

# --- CORS Settings ---
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173', # Adjust port if your Vite uses a different one
    'http://127.0.0.1:5173',
    'https://djanmon-go-1.onrender.com',
    'https://idx-gengo-65703267-819606423379.europe-west6.run.app'
]

# Allow cookies to be sent with cross-origin requests
CORS_ALLOW_CREDENTIALS = True

# --- NEW: CSRF Trusted Origins ---
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173', # Add your frontend development origin
    'http://127.0.0.1:5173',
    'https://djanmon-go-1.onrender.com',
    'https://idx-gengo-65703267-819606423379.europe-west6.run.app'
]

# --- Cookie Settings for Cross-Site Production ---
# Set these based on whether DEBUG is True or False
SESSION_COOKIE_SECURE = True  # Must be True for SameSite=None
CSRF_COOKIE_SECURE = True     # Must be True for SameSite=None
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SAMESITE = 'None'

# Optional: Cookie Domain (only if FE/BE are subdomains of the same parent domain)
# If your FE is app.example.com and BE is api.example.com, you might use:
# SESSION_COOKIE_DOMAIN = ".example.com"
# CSRF_COOKIE_DOMAIN = ".example.com"
# Leave unset if they are completely different domains.

# --- Static files configuration --- 
STATIC_URL = 'static/'

# Directory where collectstatic will gather files for deployment
# Use an absolute path within the container
STATIC_ROOT = '/app/staticfiles' 

# Directories where Django looks for static files *in addition* to app static/ dirs
STATICFILES_DIRS = [
    # Use an absolute path within the container for the copied frontend build
    '/app/frontend_dist',
    # Keep existing static_cdn directory if needed, using absolute path
    '/app/djanmongo/static_cdn', 
]

# Use WhiteNoise storage with compression and caching support
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add this setting to tell WhiteNoise to serve the index.html file for unmatched URLs
# This allows the Vue Router to handle routing on the frontend.
WHITENOISE_INDEX_FILE = True

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

# --- NEW: Load Battle Reward Env Vars --- 
# Load environment variables (consider using python-dotenv if not already handled)
CREDITS_WIN_VS_HUMAN = int(os.environ.get('CREDITS_WIN_VS_HUMAN', '3'))
CREDITS_WIN_VS_BOT = int(os.environ.get('CREDITS_WIN_VS_BOT', '2'))
CREDITS_LOSS = int(os.environ.get('CREDITS_LOSS', '1'))
# --- END NEW ---
