from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='user_register'),
    path('login/', views.LoginView.as_view(), name='user_login'), 
    path('logout/', views.LogoutView.as_view(), name='user_logout'),
    path('me/', views.UserProfileView.as_view(), name='user_profile'),
    path('me/selected-attacks/', views.UserSelectedAttacksUpdateView.as_view(), name='user_update_selected_attacks'),
    path('me/stats/', views.UserStatsView.as_view(), name='user_stats'),
    path('me/generate-profile-picture', views.GenerateProfilePictureView.as_view(), name='user_generate_profile_picture'),
    path('', views.UserListView.as_view(), name='user_list'), # List users for potential battles
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('csrf-token/', views.CsrfTokenView.as_view(), name='csrf_token'),
]
