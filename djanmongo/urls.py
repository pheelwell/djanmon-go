from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse, Http404
import os

def serve_index(request):
    index_html_path = os.path.join(settings.STATIC_ROOT, 'index.html')
    try:
        with open(index_html_path, 'rb') as f:
            content_type = 'text/html'
            return HttpResponse(f.read(), content_type=content_type)
    except FileNotFoundError:
        raise Http404(f"index.html not found in STATIC_ROOT ({settings.STATIC_ROOT})")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/game/', include('game.urls')),
    re_path(r'^.*$', serve_index, name='frontend_catchall'),
]
