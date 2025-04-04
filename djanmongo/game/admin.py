from django.contrib import admin
from .models import Attack, Battle
from unfold.admin import ModelAdmin

@admin.register(Attack) # Use decorator for cleaner registration
class AttackAdmin(ModelAdmin):
    list_display = ('name', 'emoji', 'power', 'target', 'hp_amount', 'target_stat', 'stat_mod', 'momentum_cost')
    search_fields = ('name', 'description')
    list_filter = ('target', 'target_stat')
    list_editable = ('emoji', 'power', 'target', 'hp_amount', 'target_stat', 'stat_mod', 'momentum_cost')

@admin.register(Battle)
class BattleAdmin(ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'status', 'winner', 'whose_turn', 'current_momentum_player1', 'current_momentum_player2', 'updated_at')
    list_filter = ('status', 'whose_turn')
    search_fields = ('player1__username', 'player2__username')
    readonly_fields = ('created_at', 'updated_at', 'current_hp_player1', 'current_hp_player2', 'stat_stages_player1', 'stat_stages_player2', 'last_turn_summary', 'current_momentum_player1', 'current_momentum_player2')
