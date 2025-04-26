from django.contrib import admin, messages
from django import forms
from django.utils.html import format_html
import json # Added for formatting
from .models import Attack, Battle, Script, GameConfiguration, AttackUsageStats
from django.db import transaction # <-- Import transaction
from django.db.models import Count, Case, When, Value, IntegerField # Added for annotation
from unfold.admin import ModelAdmin
from django.contrib.admin import SimpleListFilter # Added for custom filter
# Import the correct widget based on the user-provided library
from djangoeditorwidgets.widgets import MonacoEditorWidget 
from django.utils.safestring import mark_safe
import traceback # For detailed error logging

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

# --- NEW: Attack Usage Stats Admin --- 
@admin.register(AttackUsageStats)
class AttackUsageStatsAdmin(ModelAdmin):
    list_display = ('attack_name', 'times_used', 'wins_vs_human', 'losses_vs_human', 'wins_vs_bot', 'losses_vs_bot', 'total_damage_dealt')
    search_fields = ('attack__name',) # Search by related attack name
    readonly_fields = () # Make attack read-only in detail view <-- REMOVED 'attack'
    list_filter = ()
    ordering = ('-times_used', 'attack__name')

    actions = ['recalculate_all_stats'] # Add the custom action

    @admin.display(description='Attack Name', ordering='attack__name') # Allow ordering by name
    def attack_name(self, obj):
        # Handle potential case where attack might be deleted but stats remain
        return obj.attack.name if obj.attack else "[Deleted Attack]"

    @admin.action(description='(SLOW) Recalculate ALL usage stats from LOGS')
    def recalculate_all_stats(self, request, queryset):
        # Note: queryset is ignored here as we recalculate ALL stats globally
        try:
            with transaction.atomic():
                # 0. Ensure stats objects exist for all attacks BEFORE resetting
                all_attacks = Attack.objects.all()
                existing_stat_attack_ids = set(AttackUsageStats.objects.values_list('attack_id', flat=True))
                missing_stats_to_create = []
                for attack in all_attacks:
                    if attack.id not in existing_stat_attack_ids:
                        # Use default= parameter for get_or_create if you have defaults in model
                        # Otherwise, create manually or ensure defaults are handled by model's save()
                        missing_stats_to_create.append(AttackUsageStats(attack=attack)) 
                
                if missing_stats_to_create:
                    AttackUsageStats.objects.bulk_create(missing_stats_to_create, ignore_conflicts=True) # Use ignore_conflicts just in case
                    print(f"[Admin Action] Created {len(missing_stats_to_create)} missing AttackUsageStats records.")


                # 1. Reset existing stats - CORRECTED FIELDS
                num_reset = AttackUsageStats.objects.update(
                    times_used=0, 
                    wins_vs_human=0,
                    losses_vs_human=0,
                    wins_vs_bot=0,
                    losses_vs_bot=0,
                    total_damage_dealt=0,
                    total_healing_done=0, # Make sure this field exists on the model
                    co_used_with_counts={} # Ensure this uses default={} in the model field
                )
                print(f"[Admin Action] Reset {num_reset} AttackUsageStats records to zero.")

                # 2. Iterate through finished battles and recalculate from logs
                processed_battles = 0
                attacks_found_total = 0
                wins_contributed_total = 0

                # Prepare a cache for Attack objects to reduce DB lookups by name
                attack_cache = {attack.name: attack for attack in Attack.objects.all()}
                print(f"[Admin Action] Cached {len(attack_cache)} Attack objects.")

                # Use iterator for memory efficiency
                for battle in Battle.objects.filter(status='finished').iterator(chunk_size=500): # Smaller chunk size might be better for log processing
                    processed_battles += 1
                    winner_role = battle.get_player_role(battle.winner) if battle.winner else None
                    is_vs_bot = battle.player2_is_ai_controlled # Determine if it was a bot battle
                    unique_attacks_used_in_battle = set() # Store Attack objects

                    if not isinstance(battle.last_turn_summary, list):
                        print(f"[Admin Action Warning] Battle {battle.id} has invalid log format. Skipping.")
                        continue

                    # Parse logs for this battle
                    for log_entry in battle.last_turn_summary:
                        if isinstance(log_entry, dict) and \
                           log_entry.get('effect_type') == 'action' and \
                           isinstance(log_entry.get('effect_details'), dict) and \
                           'attack_name' in log_entry['effect_details']:

                            attack_name = log_entry['effect_details']['attack_name']
                            log_source_role = log_entry.get('source') # 'player1' or 'player2'

                            # Find attack using cache first, then DB fallback (case-sensitive)
                            attack_obj = attack_cache.get(attack_name)
                            if not attack_obj:
                                # Fallback DB lookup if not in cache (less efficient)
                                try:
                                     # Consider if case-insensitivity is needed: attack_obj = Attack.objects.get(name__iexact=attack_name)
                                     attack_obj = Attack.objects.get(name=attack_name)
                                     attack_cache[attack_name] = attack_obj # Add to cache if found
                                except Attack.DoesNotExist:
                                    print(f"[Admin Action Warning] Attack '{attack_name}' mentioned in Battle {battle.id} log not found in DB. Skipping.")
                                    continue

                            # If attack found, process it
                            if attack_obj:
                                stats, created = AttackUsageStats.objects.get_or_create(attack=attack_obj)
                                
                                # Increment times_used (only once per attack per battle)
                                if attack_obj not in unique_attacks_used_in_battle:
                                    stats.times_used += 1
                                    # REMOVED save here - save once at the end of processing this attack
                                    unique_attacks_used_in_battle.add(attack_obj)
                                    attacks_found_total += 1

                                # Check if this winner used this attack in this battle log
                                if winner_role and log_source_role == winner_role:
                                    if not hasattr(battle, f'_counted_win_{attack_obj.id}'):
                                        # --- CORRECTED WIN INCREMENT --- 
                                        if is_vs_bot:
                                            stats.wins_vs_bot += 1
                                        else:
                                            stats.wins_vs_human += 1
                                        # stats.wins_contributed += 1 # <- REMOVED OLD LINE
                                        # REMOVED save here - save once at the end
                                        setattr(battle, f'_counted_win_{attack_obj.id}', True)
                                        wins_contributed_total += 1
                                        
                                stats.save() # Save the stat object ONCE after all updates for this attack in this battle

                    # Optional: Clean up temporary attributes if needed, though they are instance-specific
                    # for attack_obj in unique_attacks_used_in_battle:
                    #    if hasattr(battle, f'_counted_win_{attack_obj.id}'):
                    #        delattr(battle, f'_counted_win_{attack_obj.id}')


            # 3. Optional Cleanup of orphan stats (stats for deleted attacks)
            # Note: This permanently deletes stats. Only uncomment if intended.
            # deleted_stats_count = 0
            # try:
            #     orphan_stats = AttackUsageStats.objects.filter(attack__isnull=True)
            #     deleted_stats_count = orphan_stats.count()
            #     if deleted_stats_count > 0:
            #         orphan_stats.delete()
            #         print(f"[Admin Action] Cleaned up {deleted_stats_count} AttackUsageStats records for deleted attacks.")
            # except Exception as cleanup_e:
            #     print(f"[Admin Action Warning] Error during orphan stats cleanup: {cleanup_e}")


            self.message_user(request, f"Successfully recalculated stats from logs. Processed {processed_battles} finished battles. Incremented 'times_used' {attacks_found_total} times and 'wins_contributed' {wins_contributed_total} times across relevant attacks. Note: This process can be slow.", messages.SUCCESS)
            print(f"[Admin Action] Log-based recalculation complete. Processed {processed_battles} battles.")

        except Exception as e:
            traceback.print_exc() # Print full traceback to server logs
            self.message_user(request, f"ERROR during log-based recalculation: {e}", messages.ERROR)
            print(f"[Admin Action Error] Log-based recalculation failed: {e}")
# --- END Attack Usage Stats Admin ---

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
