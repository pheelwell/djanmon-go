"""
WSGI config for pokemon_like_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Make sure this matches the path used in your manage.py and settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pokemon_like_project.settings')

application = get_wsgi_application()
