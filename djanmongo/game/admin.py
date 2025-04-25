from django.contrib import admin
from django import forms
from django.utils.html import format_html
import json # Added for formatting
from .models import Attack, Battle, Script, GameConfiguration
from django.db.models import Count, Case, When, Value, IntegerField # Added for annotation
from unfold.admin import ModelAdmin
from django.contrib.admin import SimpleListFilter # Added for custom filter
# Import the correct widget based on the user-provided library
from djangoeditorwidgets.widgets import MonacoEditorWidget 
from django.utils.safestring import mark_safe

# --- Game Configuration Admin ---
@admin.register(GameConfiguration)
class GameConfigurationAdmin(ModelAdmin):
    list_display = ('id', 'attack_generation_cost')
    # No actions needed, only one instance
    actions = None 

    def has_add_permission(self, request):
        # Prevent adding more instances if one already exists
        return not GameConfiguration.objects.exists()
        
    def has_delete_permission(self, request, obj=None):
        # Optionally prevent deletion
        return False # Prevent deletion of the singleton config
# --- END Game Configuration Admin ---

# --- Inline Admin for Scripts ---
class ScriptInlineForm(forms.ModelForm): # Form specifically for the inline
    class Meta:
        model = Script
        fields = '__all__'
        widgets = {
            'lua_code': MonacoEditorWidget(language="lua", wordwrap=True), # REMOVED height=200
        }

class ScriptInline(admin.StackedInline): # Keep StackedInline
    model = Script
    form = ScriptInlineForm
    extra = 1 
    ordering = ('created_at',)
    ordering_field = 'created_at'
    
    # Define fieldsets for the INLINE form
    fieldsets = (
        # Make the entire inline collapsible by default
        (None, { 
            'classes': ('collapse',), # ADD collapse class here
            'fields': ( 
                 # Add name/desc back if needed, or keep excluded
                 # 'name', 'description',
                 # --- Triggers --- 
                'trigger_on_attack', 
                'trigger_before_attacker_turn',
                'trigger_after_attacker_turn',
                'trigger_before_target_turn',
                'trigger_after_target_turn',
                # --- Code --- 
                'lua_code',
            )
        }),
        # Removed specific Trigger/Code fieldsets if collapsing the whole thing
    )
    # exclude = ('name', 'description') # Remove exclude if fields added above

# --- Attack Admin Definition ---
@admin.register(Attack) # Use decorator for cleaner registration
class AttackAdmin(ModelAdmin):
    
    list_display = (
        'name', 
        'emoji', 
        'momentum_cost', 
        'has_associated_scripts', 
    )
    search_fields = ('name', 'description')
    list_filter = () 
    
    # Define fieldsets using current model fields
    fieldsets = (
        (None, {
            'fields': ('name', 'emoji', 'description', 'momentum_cost')
        }),
        # Fieldset for M2M removed
        # ('Associated Scripts', {
        #     'fields': ('scripts',)
        # }),
    )

    inlines = [ScriptInline] # ADDED back the inline

    # Custom display method (Updated)
    @admin.display(boolean=True, description='Has Scripts?')
    def has_associated_scripts(self, obj):
        return obj.scripts.exists()

# --- Custom Filter for Battle Log Errors ---
class BattleLogErrorFilter(SimpleListFilter):
    title = 'Log Errors' # Title for the filter section
    parameter_name = 'log_errors' # URL parameter

    def lookups(self, request, model_admin):
        """Returns filter options."""
        return (
            ('yes', 'With Errors'),
            ('no', 'Without Errors'),
        )

    def queryset(self, request, queryset):
        """Filters the queryset based on the selected option."""
        error_pattern = '"effect_type": "error"' # Simple string pattern
        if self.value() == 'yes':
            # Filter for battles where the log contains the error pattern
            return queryset.filter(last_turn_summary__icontains=error_pattern)
        if self.value() == 'no':
            # Exclude battles where the log contains the error pattern
            return queryset.exclude(last_turn_summary__icontains=error_pattern)
        # Return the full queryset if no filter is selected
        return queryset

# --- Battle Admin Definition (Ensure it's also correct) ---
@admin.register(Battle)
class BattleAdmin(ModelAdmin):
    list_display = (
        'id', 
        'player1', 
        'player2', 
        'status', 
        'whose_turn', 
        'turn_number', 
        'winner', 
        'error_count', # Added error count
        'updated_at'
    )
    list_filter = ('status', 'whose_turn', BattleLogErrorFilter) # Added custom filter
    search_fields = ('player1__username', 'player2__username')
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'display_log_formatted', # Added formatted log display
        'display_player1_battle_attacks_with_scripts', # ADD Player 1 display method
        'display_player2_battle_attacks_with_scripts', # ADD Player 2 display method
    )
    
    # Add fieldsets if you want to group fields in the detail view
    # fieldsets = (
    #     (None, {'fields': ('player1', 'player2', 'status', 'winner')}),
    #     ('Current State', {'fields': ('current_hp_player1', 'current_hp_player2', 'stat_stages_player1', 'stat_stages_player2', 'current_momentum_player1', 'current_momentum_player2', 'whose_turn', 'turn_number')}),
    #     ('Advanced', {'fields': ('custom_statuses_player1', 'custom_statuses_player2', 'registered_scripts')}),
    #     ('Battle Attacks & Scripts', { # Add section for our new fields
    #         'fields': ('display_player1_battle_attacks_with_scripts', 'display_player2_battle_attacks_with_scripts')
    #     }),
    #     ('Last Turn Log', {'fields': ('display_log_formatted',)}),
    #     ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    # )

    def get_queryset(self, request):
        """Annotate the queryset to allow sorting by error presence."""
        queryset = super().get_queryset(request)
        error_pattern = '"effect_type": "error"'
        # Annotate with 1 if errors are present (using string search), 0 otherwise
        queryset = queryset.annotate(
            _has_errors=Case(
                When(last_turn_summary__icontains=error_pattern, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        )
        return queryset

    # Make error_count sortable by the annotated field
    @admin.display(description='Error Count', ordering='_has_errors')
    def error_count(self, obj):
        """Counts log entries with effect_type 'error' in last_turn_summary."""
        if isinstance(obj.last_turn_summary, list):
            count = sum(1 for entry in obj.last_turn_summary if isinstance(entry, dict) and entry.get('effect_type') == 'error')
            return count
        return 0

    @admin.display(description='Last Turn Log (Formatted)')
    def display_log_formatted(self, obj):
        """Formats the last_turn_summary JSON field for display."""
        try:
            # Format the JSON with indentation for readability
            formatted_json = json.dumps(obj.last_turn_summary, indent=2)
            # Use format_html to wrap in <pre> tags for preserving whitespace and formatting
            return format_html("<pre>{}</pre>", formatted_json)
        except (TypeError, json.JSONDecodeError):
            # Fallback if the field doesn't contain valid JSON list
            return format_html("<pre>{}</pre>", str(obj.last_turn_summary))

    # --- NEW Display Methods for Battle Attacks & Scripts ---
    @admin.display(description='Player 1 Battle Attacks & Scripts')
    def display_player1_battle_attacks_with_scripts(self, obj):
        html_output = "<div style=\"margin-bottom: 15px;\";>"
        if not obj.player1: return "(No Player 1)"
        for attack in obj.battle_attacks_player1.all().prefetch_related("scripts"):
            html_output += f"<div style=\"margin-bottom: 10px; padding-left: 10px; border-left: 2px solid #ccc;\";><b>{attack.name} ({attack.momentum_cost} M)</b>"
            # Add description
            if attack.description:
                html_output += f"<div style=\"font-size: 0.9em; color: #555; margin-left: 5px; margin-top: 2px;\";>{attack.description}</div>"
            scripts = attack.scripts.all()
            if scripts:
                for script in scripts:
                    triggers = []
                    if script.trigger_on_attack: triggers.append("On Attack")
                    if script.trigger_before_attacker_turn: triggers.append("Before Atk Turn")
                    if script.trigger_after_attacker_turn: triggers.append("After Atk Turn")
                    if script.trigger_before_target_turn: triggers.append("Before Tgt Turn")
                    if script.trigger_after_target_turn: triggers.append("After Tgt Turn")
                    trigger_str = ", ".join(triggers) if triggers else "None"
                    
                    html_output += f"<div style=\"margin-left: 15px; margin-top: 5px;\";><i>Script: {script.name} (Triggers: {trigger_str})</i>"
                    # Use format_html, add !important to background-color
                    formatted_code = format_html("<pre style=\"padding: 8px; border: 1px solid #ddd; margin-top: 5px; white-space: pre-wrap; word-wrap: break-word;\";>{}</pre>", script.lua_code)
                    html_output += formatted_code
                    html_output += "</div>"
            else:
                html_output += " <i style=\"color: #777;\";>(No scripts)</i>"
            html_output += "</div>" # Close attack div
        html_output += "</div>" # Close main container div
        # Mark the fully constructed string as safe
        return mark_safe(html_output)

    @admin.display(description='Player 2 Battle Attacks & Scripts')
    def display_player2_battle_attacks_with_scripts(self, obj):
        html_output = "<div style=\"margin-bottom: 15px;\";>"
        if not obj.player2: return "(No Player 2)"
        for attack in obj.battle_attacks_player2.all().prefetch_related("scripts"):
            html_output += f"<div style=\"margin-bottom: 10px; padding-left: 10px; border-left: 2px solid #ccc;\";><b>{attack.name} ({attack.momentum_cost} M)</b>"
            # Add description
            if attack.description:
                html_output += f"<div style=\"font-size: 0.9em; color: #555; margin-left: 5px; margin-top: 2px;\";>{attack.description}</div>"
            scripts = attack.scripts.all()
            if scripts:
                for script in scripts:
                    triggers = []
                    if script.trigger_on_attack: triggers.append("On Attack")
                    if script.trigger_before_attacker_turn: triggers.append("Before Atk Turn")
                    if script.trigger_after_attacker_turn: triggers.append("After Atk Turn")
                    if script.trigger_before_target_turn: triggers.append("Before Tgt Turn")
                    if script.trigger_after_target_turn: triggers.append("After Tgt Turn")
                    trigger_str = ", ".join(triggers) if triggers else "None"
                    
                    html_output += f"<div style=\"margin-left: 15px; margin-top: 5px;\";><i>Script: {script.name} (Triggers: {trigger_str})</i>"
                    # Use format_html for the code part ONLY
                    formatted_code = format_html("<pre style=\"padding: 8px; border: 1px solid #ddd; margin-top: 5px; white-space: pre-wrap; word-wrap: break-word;\";>{}</pre>", script.lua_code)
                    html_output += formatted_code # Append the safe HTML part
                    html_output += "</div>"
            else:
                html_output += " <i style=\"color: #777;\";>(No scripts)</i>"
            html_output += "</div>" # Close attack div
        html_output += "</div>" # Close main container div
        # Mark the fully constructed string as safe
        return mark_safe(html_output)
    # --- END NEW --- 

# Register Script model if not already managed elsewhere or via inline
# admin.site.register(Script) # Can be commented out if only managed via Attack inline
