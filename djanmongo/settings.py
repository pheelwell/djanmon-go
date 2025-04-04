import os
from pathlib import Path
from datetime import timedelta # Import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here' # CHANGE THIS!

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

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

    # Your apps
    'users.apps.UsersConfig',
    'game.apps.GameConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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

STATIC_URL = 'static/'


DATABASES = {
    #'default': {
    #    'ENGINE': 'django.db.backends.postgresql', # Or your preferred DB
    #    'NAME': 'pokemon_game_db',
    #    'USER': 'your_db_user',
    #    'PASSWORD': 'your_db_password',
    #    'HOST': 'localhost', # Or your DB host
    #    'PORT': '5432',      # Or your DB port
    #}
    # Or use SQLite for simple setup:
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# --- CORS Settings ---
# Allow requests from the Vue development server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173", # Default Vite dev server port
    "http://127.0.0.1:5173",
    # Add other origins if needed (e.g., your production frontend URL)
]
# Allow cookies/auth headers to be sent
CORS_ALLOW_CREDENTIALS = True 

# Optional: Allow specific headers if needed (often default is fine)
# CORS_ALLOW_HEADERS = [ ... ]

# Optional: Allow specific methods (often default is fine)
# CORS_ALLOW_METHODS = [ ... ]


# Internationalization & Static files (default settings usually fine for API)
# ... (keep default LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ)
# ... (keep default STATIC_URL, STATIC_ROOT if needed)

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
