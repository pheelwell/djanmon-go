from django.urls import path
# Remove JWT imports
# from rest_framework_simplejwt.views import (
#     TokenObtainPairView,
#     TokenRefreshView,
# )
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='user_register'),
    # Replace JWT login with session login view
    path('login/', views.LoginView.as_view(), name='user_login'), 
    # Remove JWT refresh
    # path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='user_logout'),
    path('me/', views.UserProfileView.as_view(), name='user_profile'),
    path('me/selected-attacks/', views.UserSelectedAttacksUpdateView.as_view(), name='user_update_selected_attacks'),
    path('me/stats/', views.UserStatsView.as_view(), name='user_stats'),
    path('', views.UserListView.as_view(), name='user_list'), # List users for potential battles
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]
