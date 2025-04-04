from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='user_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.UserProfileView.as_view(), name='user_profile'),
    path('me/selected-attacks/', views.UserSelectedAttacksUpdateView.as_view(), name='user_update_selected_attacks'),
    path('', views.UserListView.as_view(), name='user_list'), # List users for potential battles
]
