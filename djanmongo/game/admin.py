from django.contrib import admin
from django import forms
from .models import Attack, Battle
from unfold.admin import ModelAdmin
# Import the correct widget based on the user-provided library
from djangoeditorwidgets.widgets import MonacoEditorWidget 

# --- Custom Form for Attack Admin ---
class AttackAdminForm(forms.ModelForm):
    class Meta:
        model = Attack
        fields = '__all__' # Include all fields from the model
        widgets = {
            # Use MonacoEditorWidget and specify Lua language
            'lua_script_on_attack': MonacoEditorWidget(language="lua", wordwrap=True),
            'lua_script_before_opponent': MonacoEditorWidget(language="lua", wordwrap=True),
            'lua_script_after_opponent': MonacoEditorWidget(language="lua", wordwrap=True),
        }

# --- Attack Admin Definition ---
@admin.register(Attack) # Use decorator for cleaner registration
class AttackAdmin(ModelAdmin):
    form = AttackAdminForm # Use the custom form
    
    list_display = (
        'name', 
        'emoji', 
        'momentum_cost', 
        'register_before_opponent', 
        'register_after_opponent', 
        'has_on_attack_script', # Custom method to check script presence
    )
    search_fields = ('name', 'description')
    list_filter = ('register_before_opponent', 'register_after_opponent') # Only filter by booleans for now
    
    # Define fieldsets using current model fields
    fieldsets = (
        (None, {
            'fields': ('name', 'emoji', 'description', 'momentum_cost')
        }),
        ('Lua Scripts & Registration', {
            # 'classes': ('collapse',), # Optional
            'fields': (
                'lua_script_on_attack', 
                'lua_script_before_opponent', 
                'register_before_opponent', 
                'lua_script_after_opponent',
                'register_after_opponent',
            )
        }),
    )

    # Custom display method
    @admin.display(boolean=True, description='Has On Attack Script?')
    def has_on_attack_script(self, obj):
        return bool(obj.lua_script_on_attack)

    # --- Include Custom JavaScript for show/hide ---
    class Media:
        js = ('admin/js/attack_admin.js',) # Path relative to STATIC_URL

# --- Battle Admin Definition (Ensure it's also correct) ---
@admin.register(Battle)
class BattleAdmin(ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'status', 'whose_turn', 'turn_number', 'winner', 'updated_at')
    list_filter = ('status', 'whose_turn')
    search_fields = ('player1__username', 'player2__username')
    readonly_fields = ('created_at', 'updated_at')
