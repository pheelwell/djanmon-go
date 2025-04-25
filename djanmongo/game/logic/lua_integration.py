import lupa
import math
import random # Need for damage variance
import logging # <-- Import logging
from typing import TYPE_CHECKING # <-- Import TYPE_CHECKING
from .constants import MIN_STAT_STAGE, MAX_STAT_STAGE, DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX
from .calculations import get_modified_stat, clamp

# --- Type Hinting --- 
if TYPE_CHECKING:
    from ..models import Attack # <-- Import Attack for type hinting
# --- End Type Hinting ---

# --- Setup Logger ---
logger = logging.getLogger(__name__) # <-- Get logger instance
# --- End Logger Setup ---

# Global check for Lupa availability
try:
    import lupa
    LUA_AVAILABLE = True
except ImportError:
    LUA_AVAILABLE = False
    print("WARNING: Lupa Lua runtime not found. Lua scripts will be disabled.")

# --- API Setup ---
LUA_API = {}

def register_lua_api_func(func):
    """Decorator to register Python functions for Lua API."""
    if LUA_AVAILABLE:
        LUA_API[func.__name__] = func
    return func

# --- Utility Functions (Used internally by API funcs) ---
@register_lua_api_func
def log(context, text, effect_type="info", source="script", details=None):
    """Helper to add entries to the script's log within the context."""
    log_entry = {"source": source, "text": text, "effect_type": effect_type}
    if details:
        # Convert Lua table details to Python dict if necessary!
        if lupa.lua_type(details) == 'table':
            log_entry["effect_details"] = dict(details)
        else:
            log_entry["effect_details"] = details # Assume primitive if not table
    context['log_entries'].append(log_entry)
    # print(f"    [Lua Log - {effect_type}] {text}") # Optional console log

# --- NEW API Function for Unregistering ---
@register_lua_api_func
def unregister_script(context, registration_id_to_remove):
    """Removes a script registration from the context's list by its unique ID."""
    if not registration_id_to_remove:
        logger.warning("Lua API: unregister_script called with nil ID.")
        return False # Indicate failure
        
    scripts = context.get('registered_scripts', [])
    initial_len = len(scripts)
    
    context['registered_scripts'] = [s for s in scripts if s.get('registration_id') != registration_id_to_remove]
    
    if len(context['registered_scripts']) < initial_len:
        context['_state_changed'] = True
        return True
    else:
        # Use logger for internal warning
        logger.warning(f"Lua API: Could not find script instance ID {registration_id_to_remove} to unregister.")
        return False
# --- End NEW API Function ---

# --- Standard Effect API Functions ---

@register_lua_api_func
def apply_std_damage(context, base_power, target_role=None):
    """Calculates and applies standard damage based on base_power, stats, and stages.
       Defaults target to TARGET_ROLE if target_role is nil.
       Uses standard Pokemon-like damage formula with random variance.
       Returns the actual damage dealt (integer), or 0 if no damage was dealt.
    """
    target = target_role if target_role else context['target_role']
    attacker_role = context['attacker_role']
    target_role = context['target_role']
    attacker_obj = context['objects'][attacker_role]
    target_obj = context['objects'][target]
    
    if target not in context['hp'] or target not in context['stat_stages']:
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid target role '{target}' in apply_std_damage.")
        return 0 # Return 0 damage
    if attacker_role not in context['stat_stages']:
        # Use logger for internal error
         logger.warning(f"Lua API Error: Invalid attacker role '{attacker_role}' in apply_std_damage.")
         return 0 # Return 0 damage
    
    base_power = int(base_power)
    if base_power <= 0:
        logger.warning(context, f"Base power must be positive in apply_std_damage (got {base_power})", "info")
        return 0 # Return 0 damage

    # Get effective stats based on stages
    attacker_stages = context['stat_stages'][attacker_role]
    target_stages = context['stat_stages'][target]
    effective_attacker_atk = get_modified_stat(attacker_obj.attack, attacker_stages.get('attack', 0))
    effective_target_def = get_modified_stat(target_obj.defense, target_stages.get('defense', 0))

    # Simplified Pokemon damage formula (Level 50 assumed)
    # (((2 * Level / 5 + 2) * BasePower * Attack / Defense) / 50) + 2
    # Assume level 50: ((2 * 50 / 5 + 2) = 22
    base_damage_calc = ((22 * base_power * effective_attacker_atk / effective_target_def) / 50) + 2
    
    # Apply random variance
    random_modifier = random.uniform(DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX)
    final_damage = int(base_damage_calc * random_modifier)
    final_damage = max(1, final_damage) # Ensure at least 1 damage
        
    # Apply damage to context HP
    current_hp = context['hp'][target]
    max_hp = context['max_hp'][target]
    new_hp = max(0, current_hp - final_damage)
    
    if new_hp != current_hp:
        context['hp'][target] = new_hp
        context['state_changed'] = True
        target_name = get_player_name(context, target) or target
        # --- ADD AUTOMATIC DAMAGE LOGGING --- 
        log(context, f"{target_name} took {final_damage} damage.", "damage", "script", {"damage_dealt": final_damage})
        # --- END LOGGING --- 
        return final_damage # Return damage dealt
    else:
        return 0 # Return 0 if HP didn't change

@register_lua_api_func
def apply_std_hp_change(context, hp_change, target_role=None):
    """Applies a direct HP change (positive for heal, negative for cost/loss) to a target.
       Defaults to ATTACKER_ROLE if target_role is nil.
       Returns the actual HP change applied (integer), or 0 if no change occurred.
    """
    target = target_role if target_role else context['attacker_role']
    attacker_role = context['attacker_role'] # For logging source

    if target not in context['hp']:
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid target role '{target}' in apply_std_hp_change.")
        return 0 # No change
        
    hp_change = int(hp_change) # Ensure integer
    if hp_change == 0:
        return 0 # No change

    current_hp = context['hp'][target]
    max_hp = context['max_hp'][target]
    new_hp = min(max_hp, max(0, current_hp + hp_change))
    
    actual_change = new_hp - current_hp
    if actual_change != 0:
        context['hp'][target] = new_hp
        context['state_changed'] = True
        target_name = get_player_name(context, target) or target
        effect = "heal" if actual_change > 0 else "damage" # Treat HP cost as damage type
        return actual_change # Return the actual change
    else:
        return 0 # Return 0 if no change

@register_lua_api_func
def apply_std_stat_change(context, stat, mod, target_role=None):
    """Applies a stat stage change (+1, -2, etc.) to a target.
       Defaults to ATTACKER_ROLE if target_role is nil.
       Stat should be 'attack', 'defense', or 'speed'.
    """
    target = target_role if target_role else context['attacker_role']
    attacker_role = context['attacker_role'] # For logging source
    
    if target not in context['stat_stages']:
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid target role '{target}' in apply_std_stat_change.")
        return
        
    stat = stat.lower() # Normalize
    if stat not in ['attack', 'defense', 'speed']:
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid stat '{stat}' in apply_std_stat_change.")
        return
        
    mod = int(mod)
    if mod == 0:
        return
        
    target_stages = context['stat_stages'][target]
    current_stage = target_stages.get(stat, 0)
    
    # Use imported constants
    min_stage = MIN_STAT_STAGE
    max_stage = MAX_STAT_STAGE
    
    new_stage = min(max_stage, max(min_stage, current_stage + mod))
    
    if new_stage != current_stage:
        target_stages[stat] = new_stage
        context['state_changed'] = True
        target_name = get_player_name(context, target) or target
        change_dir = "raised" if mod > 0 else "lowered"
    else:
        limit_dir = "highest" if mod > 0 else "lowest"
        target_name = get_player_name(context, target) or target
        log(context, f"{target_name}'s {stat.upper()} is already at the {limit_dir} limit.", "info", target_role)

# --- NEW: Add function to get current stage --- 
@register_lua_api_func
def get_stat_stage(context, role, stat_name):
    """Gets the current stage for a specific stat ('attack', 'defense', 'speed') for a given role.
       Returns the integer stage (e.g., -1, 0, 2) or 0 if role/stat is invalid.
    """
    stat_name = stat_name.lower()
    if role not in context.get('stat_stages', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in get_stat_stage.")
        return 0
    if stat_name not in ['attack', 'defense', 'speed']:
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid stat_name '{stat_name}' used in get_stat_stage.")
        return 0
    return context['stat_stages'][role].get(stat_name, 0)
# --- End NEW Function ---

# --- NEW General Query API Functions ---

@register_lua_api_func
def get_max_hp(context, role):
    """Returns the maximum HP for the specified player role ('attacker' or 'target')."""
    if role not in context.get('max_hp', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in get_max_hp.")
        return None
    return context['max_hp'].get(role)

@register_lua_api_func
def get_turn_number(context):
    """Returns the current battle turn number."""
    return context.get('turn_number')

@register_lua_api_func
def get_battle_status(context):
    """Returns the current battle status ('pending', 'active', 'finished', etc.)."""
    return context.get('battle_status')

@register_lua_api_func
def get_player_name(context, role):
    """Returns the username of the player ('attacker' or 'target')."""
    user_obj = context['objects'].get(role)
    # No internal log needed here, just returns None if role invalid
    return user_obj.username if user_obj else None

@register_lua_api_func
def get_player_id(context, role):
    """Returns the database ID of the player ('attacker' or 'target')."""
    user_obj = context['objects'].get(role)
    # No internal log needed here
    return user_obj.id if user_obj else None

@register_lua_api_func
def get_log_entries(context):
    """Returns a list (Lua table) of log entries generated *so far* within this script execution."""
    # Return a copy to prevent direct modification? For now, return direct reference.
    return context.get('log_entries', []) 

@register_lua_api_func
def find_log_entry(context, filters):
    """Searches log entries generated *so far* in this execution.
       Returns the first matching log entry (Lua table) or nil.
       Filters is a Lua table, e.g., {source='system', effect_type='damage'}
    """
    if not filters or lupa.lua_type(filters) != 'table':
        # Use logger for internal error
        logger.warning("Lua API Error: Invalid filters table passed to find_log_entry.")
        return None
        
    log_list = context.get('log_entries', [])
    filter_dict = dict(filters) # Convert Lua table to Python dict for easier comparison

    for entry in reversed(log_list): # Search newest first
        match = True
        for key, value in filter_dict.items():
            if entry.get(key) != value:
                match = False
                break
        if match:
            # Need to convert Python dict back to Lua table for return
            lua = lupa.lua_runtime # Get the runtime instance
            if lua:
                return lua.table_from(entry) 
            else: 
                logger.warning("Lua API Error: Could not get Lua runtime to return table from find_log_entry.")
                return None # Cannot convert back
    return None # No match found

@register_lua_api_func
def is_script_registered(context, filters):
    """Checks if a script matching the filters is currently registered on the battle.
       Returns true or false.
       Filters is a Lua table, e.g., {type='before', target_role=TARGET_ROLE, source_attack_id=123}
    """
    if not filters or lupa.lua_type(filters) != 'table':
        # Use logger for internal error
        logger.warning("Lua API Error: Invalid filters table passed to is_script_registered.")
        return False # Treat invalid filters as 'not found'

    registered_scripts_list = context.get('registered_scripts', [])
    filter_dict = dict(filters)

    for script_info in registered_scripts_list:
        match = True
        for key, value in filter_dict.items():
            # Special check for numeric types coming from Lua
            if isinstance(value, float) and value.is_integer():
                value = int(value)
                
            # Ensure comparison types match (e.g., id might be int)
            entry_value = script_info.get(key)
            if isinstance(entry_value, int) and isinstance(value, float) and value.is_integer():
                 entry_value = float(entry_value) # Or convert value to int
                 
            if entry_value != value:
                match = False
                break
        if match:
            return True # Found a matching registered script
            
    return False # No match found after checking all registered scripts

# --- NEW Custom Status API Functions ---

@register_lua_api_func
def get_custom_status(context, role, status_name):
    """Gets the value of a custom status (e.g., 'Burn' count) for a player ('attacker' or 'target').
       Returns the value (number or string) or nil if the status is not present.
    """
    if role not in context.get('custom_statuses', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in get_custom_status.")
        return None
    return context['custom_statuses'][role].get(status_name) # Returns None (nil in Lua) if key doesn't exist

@register_lua_api_func
def has_custom_status(context, role, status_name):
    """Checks if a player ('attacker' or 'target') has a specific custom status.
       Returns true or false.
    """
    if role not in context.get('custom_statuses', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in has_custom_status.")
        return False
    return status_name in context['custom_statuses'][role]

@register_lua_api_func
def set_custom_status(context, role, status_name, value):
    """Sets or updates a custom status for a player ('attacker' or 'target').
       Example: set_custom_status(TARGET_ROLE, 'Burn', 3)
    """
    if role not in context.get('custom_statuses', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in set_custom_status.")
        return
    
    player_statuses = context['custom_statuses'][role]
    old_value = player_statuses.get(status_name)
    
    if old_value == value:
        return # No change
        
    player_statuses[status_name] = value
    context['state_changed'] = True
    player_name = get_player_name(context, role) or role

@register_lua_api_func
def remove_custom_status(context, role, status_name):
    """Removes a custom status from a player ('attacker' or 'target')."""
    if role not in context.get('custom_statuses', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in remove_custom_status.")
        return
        
    player_statuses = context['custom_statuses'][role]
    if status_name in player_statuses:
        old_value = player_statuses.pop(status_name)
        context['state_changed'] = True
        player_name = get_player_name(context, role) or role

@register_lua_api_func
def modify_custom_status(context, role, status_name, change):
    """Adds 'change' to an existing numeric custom status value (e.g., duration, stack count).
       If the status doesn't exist, it sets it to 'change'.
       Example: modify_custom_status(TARGET_ROLE, 'Poison', -1) -- Decrement poison counter
       Example: modify_custom_status(ATTACKER_ROLE, 'Charge', 1) -- Increment charge counter
    """
    if role not in context.get('custom_statuses', {}):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid role '{role}' used in modify_custom_status.")
        return
    if not isinstance(change, (int, float)):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Invalid change value '{change}' (must be number) used in modify_custom_status for status '{status_name}'.")
        return
        
    player_statuses = context['custom_statuses'][role]
    current_value = player_statuses.get(status_name, 0) # Default to 0 if not present
    
    if not isinstance(current_value, (int, float)):
        # Use logger for internal error
        logger.warning(f"Lua API Error: Cannot modify non-numeric status '{status_name}' (value: {current_value}) with modify_custom_status.")
        return
        
    new_value = current_value + change
    player_statuses[status_name] = new_value
    context['state_changed'] = True
    player_name = get_player_name(context, role) or role
    
# --- NEW Momentum API Function ---

@register_lua_api_func
def get_momentum(context, role):
    """Returns the current momentum for the specified player role.
       Ensure roles are validated before calling or handle potential KeyError.
    """
    if role not in context.get('momentum', {}):
        logger.warning(f"Lua API Error: Invalid role '{{role}}' used in get_momentum.")
        return 0
    return context['momentum'][role]

# --- Update Lua Execution Function --- 

def execute_lua_script(script_content, battle, current_player, opponent, current_player_role, opponent_role, source_attack: 'Attack' = None, script_instance: dict = None):
    """
    Executes a Lua script within a prepared environment.

    Args:
        script_code (str): The Lua code to execute.
        battle (Battle): The current battle object.
        attacker (User): The player object for the current attacker.
        target (User): The player object for the current target.
        attacker_role (str): 'player1' or 'player2'.
        target_role (str): 'player1' or 'player2'.
        source_attack (Attack, optional): The attack that triggered this script.
        script_instance (dict, optional): Data for the specific registered script instance being run.

    Returns:
        tuple: (list of log entries, bool indicating if battle state changed)
    """
    script_log_entries = []
    state_changed_by_script = False

    # ... (LUA_AVAILABLE check unchanged) ...

    script_name = source_attack.name if source_attack else "RegisteredScript"
    print(f"--- Executing Lua script for {script_name} (Current Turn: {current_player_role}, Turn Num: {battle.turn_number}) ---")

    try:
        import lupa 
        lua = lupa.LuaRuntime(register_eval=False, unpack_returned_tuples=True)
        
        # Prepare context dictionary
        battle_context = {
            'log_entries': [],
            'hp': {
                current_player_role: getattr(battle, f'current_hp_{current_player_role}'),
                opponent_role: getattr(battle, f'current_hp_{opponent_role}')
            },
            'max_hp': {
                current_player_role: current_player.hp,
                opponent_role: opponent.hp
            },
            'stat_stages': {
                current_player_role: battle.stat_stages_player1.copy() if current_player_role == 'player1' else battle.stat_stages_player2.copy(),
                opponent_role: battle.stat_stages_player2.copy() if current_player_role == 'player1' else battle.stat_stages_player1.copy()
            },
            'momentum': {
                 current_player_role: getattr(battle, f'current_momentum_{current_player_role}'),
                 opponent_role: getattr(battle, f'current_momentum_{opponent_role}')
            },
            # --- NEW: Custom Statuses --- 
            'custom_statuses': {
                # Also make copies to prevent direct modification until script ends
                current_player_role: battle.custom_statuses_player1.copy() if current_player_role == 'player1' else battle.custom_statuses_player2.copy(),
                opponent_role: battle.custom_statuses_player2.copy() if current_player_role == 'player1' else battle.custom_statuses_player1.copy()
            },
            # --- End Custom Statuses ---
            'state_changed': False, 
            'objects': { 
                current_player_role: current_player, 
                opponent_role: opponent 
            },
            'attacker_role': current_player_role,
            'target_role': opponent_role,
            'source_attack': source_attack,
            'turn_number': battle.turn_number,
            'battle_status': battle.status,
            'registered_scripts': list(battle.registered_scripts),
        }
        
        # Prepare the Lua environment
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        lua_globals = lua.globals()

        # -- Inject API Functions ---
        # print(f"    DEBUG: LUA_API keys available: {list(LUA_API.keys())}") # REMOVE THIS
        
        # Define the wrapper factory outside the loop
        def create_api_wrapper(func_name, py_func):
            def wrapper(*args):
                try:
                    # Add the context as the first argument
                    result = py_func(battle_context, *args)
                    # print(f"      API Call Successful: {func_name}({args}) -> {result}")
                    return result
                except Exception as e:
                    error_message = f"Lua API Call Error in '{func_name}': {e}"
                    # print(error_message)
                    # Append error to context logs as well?
                    raise lupa.LuaError(error_message) # Raise LuaError to propagate
            return wrapper

        # Register API functions using the wrapper
        for name, func in LUA_API.items():
            # print(f"      DEBUG: Attempting to register API function: {name}") # REMOVE THIS
            lua_globals[name] = create_api_wrapper(name, func)

        # --- Global Variables ---
        # Inject context variables into Lua globals
        lua_globals.PLAYER1_ROLE = 'player1'
        lua_globals.PLAYER2_ROLE = 'player2'
        lua_globals.ATTACKER_ROLE = current_player_role
        lua_globals.TARGET_ROLE = opponent_role
        lua_globals.SCRIPT_TARGET_ROLE = script_instance.get('target_role') if script_instance else opponent_role
        lua_globals.CURRENT_TRIGGER = script_instance.get('trigger_type') if script_instance else 'on_attack'
        lua_globals.CURRENT_TURN = battle.turn_number
        lua_globals.CURRENT_REGISTRATION_ID = script_instance.get('registration_id') if script_instance else None
        lua_globals.SCRIPT_START_TURN = script_instance.get('start_turn') if script_instance else 0
        # NEW: Roles from the perspective of the original attack use
        lua_globals.ORIGINAL_ATTACKER_ROLE = script_instance.get('original_attacker_role') if script_instance else current_player_role
        lua_globals.ORIGINAL_TARGET_ROLE = script_instance.get('original_target_role') if script_instance else opponent_role

        # Simple HP globals might still be useful for quick checks
        lua_globals.P1_HP = battle_context['hp'].get('player1', 0)
        lua_globals.P2_HP = battle_context['hp'].get('player2', 0)

        # --- ADD Explicit Check for API --- 
        if not lua_globals.log:
            raise RuntimeError("FATAL: Lua 'log' API function failed to register in globals!")

        print(f"    Executing script content...")
        lua.execute(script_content)
        print(f"    Script execution finished.")

        # Retrieve state changes from the context dictionary
        state_changed_by_script = battle_context.get('state_changed', False)
        script_log_entries = battle_context.get('log_entries', [])

        # --- Apply changes back to the Battle object IF state changed ---
        if state_changed_by_script:
            print(f"    Script {script_name} reported state changes. Applying back to battle object.")
            # Apply HP changes
            setattr(battle, f'current_hp_{current_player_role}', battle_context['hp'][current_player_role])
            setattr(battle, f'current_hp_{opponent_role}', battle_context['hp'][opponent_role])
            # Apply Momentum changes
            setattr(battle, f'current_momentum_{current_player_role}', battle_context['momentum'][current_player_role])
            setattr(battle, f'current_momentum_{opponent_role}', battle_context['momentum'][opponent_role])
            # Apply Stat Stage changes (Convert back to dict)
            if current_player_role == 'player1':
                battle.stat_stages_player1 = dict(battle_context['stat_stages'][current_player_role])
                battle.stat_stages_player2 = dict(battle_context['stat_stages'][opponent_role])
                # --- Apply Custom Status Changes (Convert back to dict) ---
                battle.custom_statuses_player1 = dict(battle_context['custom_statuses'][current_player_role])
                battle.custom_statuses_player2 = dict(battle_context['custom_statuses'][opponent_role])
            else: # current_player_role == 'player2'
                battle.stat_stages_player2 = dict(battle_context['stat_stages'][current_player_role])
                battle.stat_stages_player1 = dict(battle_context['stat_stages'][opponent_role])
                 # --- Apply Custom Status Changes (Convert back to dict) ---
                battle.custom_statuses_player2 = dict(battle_context['custom_statuses'][current_player_role])
                battle.custom_statuses_player1 = dict(battle_context['custom_statuses'][opponent_role])
            
            # Apply registered script changes (ensure it's a Python list)
            # Ensure the list contains only JSON-serializable Python dicts
            battle.registered_scripts = list(battle_context['registered_scripts']) 
            
            print(f"    Applied changes: HP={{battle_context['hp']}}, Momentum={{battle_context['momentum']}}, Stages={{battle_context['stat_stages']}}, CustomStatuses={{battle_context['custom_statuses']}}") # Added statuses
        else:
            print(f"    Script {script_name} reported no state changes.")

    except (lupa.LuaError, Exception) as e: # RESTORED EXCEPTION BLOCK
        # Indentation should be correct from previous fix
        print(f"!!! LUA SCRIPT ERROR for Attack ID: {source_attack.id if source_attack else 'RegisteredScript'} !!!")
        print(f"    Error Type: {type(e).__name__}")
        print(f"    Error Details: {e}")
        # Add error to this script's log entries
        script_log_entries.append({"source": "system", "text": f"Script error occurred: {e}", "effect_type": "error"}) 
        state_changed_by_script = False # Ensure state is not saved if script errored

    print(f"--- Finished Lua script execution for {script_name} (State Changed: {state_changed_by_script}) ---")
    return script_log_entries, state_changed_by_script 