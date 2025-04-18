from django.urls import path
from . import views

urlpatterns = [
    # Attack listing (maybe admin only later?)
    path('attacks/', views.AttackListView.as_view(), name='attack_list'),

    # Battle endpoints
    path('battles/initiate/', views.InitiateBattleView.as_view(), name='battle_initiate'),
    path('battles/requests/', views.PendingBattlesView.as_view(), name='battle_requests'),
    path('battles/<int:pk>/respond/', views.RespondBattleView.as_view(), name='battle_respond'),
    path('battles/<int:pk>/', views.BattleDetailView.as_view(), name='battle_detail'),
    path('battles/<int:pk>/action/', views.BattleActionView.as_view(), name='battle_action'),
    path('battles/<int:pk>/concede/', views.ConcedeBattleView.as_view(), name='battle_concede'),
    path('battles/active/', views.ActiveBattleView.as_view(), name='active_battle'), # Get user's current active battle
    # NEW: Attack Generation Endpoint
    path('attacks/generate/', views.GenerateAttacksView.as_view(), name='attack_generate'),
    path('attacks/my-attacks/', views.MyAttacksListView.as_view(), name='my_attacks_list'),
]