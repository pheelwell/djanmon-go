import random
import math
from .models import Battle, Attack
from users.models import User # Although we get users via battle object

# --- Main Action Logic --- 

def apply_attack(battle: Battle, attacker: User, attack: Attack):
    """
    Applies a single attack from the attacker in the battle.
    Modifies the battle object directly.
    Returns a list of log entries and whether the battle ended.
    Handles turn switching based on momentum.
    Integrates Lua scripting for custom effects.
    """
    # --- Imports from refactored modules ---
    from .logic import (
        calculate_momentum_gain_range, clamp,
        execute_lua_script, LUA_AVAILABLE,
        MIN_STAT_STAGE, MAX_STAT_STAGE 
    )
    # --- End Imports ---

    log_entries = []
    battle_ended = False
    state_changed_this_turn = False # Track if any state changed

    # --- Validation ---
    attacker_role = battle.get_player_role(attacker)
    if not attacker_role:
        raise ValueError("Attacker not part of this battle.")
    if battle.status != 'active':
        raise ValueError("Battle is not active.")
    if battle.whose_turn != attacker_role:
        raise ValueError(f"It is not {attacker_role}'s turn.")

    # --- Determine Target ---
    if attacker_role == 'player1':
        target_player = battle.player2
        target_role = 'player2'
    else: # attacker_role == 'player2'
        target_player = battle.player1
        target_role = 'player1'
        
    # Store current state for potential post-script checks
    # (These might be less critical now if scripts handle their own faint checks)
    # initial_attacker_hp = getattr(battle, f'current_hp_{attacker_role}')
    # initial_target_hp = getattr(battle, f'current_hp_{target_role}')
    
    def add_log_entry(entry):
         log_entries.append(entry)
         
    # --- 1. Execute Registered "Before" Scripts ---
    # Run scripts registered *against* the current attacker
    print(f"--- Checking registered 'before' scripts for {attacker_role} ---")
    # Create a mutable list to allow removing scripts as they run (if desired)
    current_registered_scripts = list(battle.registered_scripts)
    temp_registered_scripts = []
    state_changed_by_before_scripts = False
    last_damage_dealt_in_turn = 0 # Track damage for context
    
    for script_info in current_registered_scripts:
        if script_info.get('type') == 'before' and script_info.get('target_role') == attacker_role:
            print(f"  Running 'before' script from Attack ID: {script_info.get('source_attack_id')}...")
            script_content = script_info.get('script')
            source_attack_obj = Attack.objects.filter(pk=script_info.get('source_attack_id')).first()
            
            if script_content:
                before_logs, state_changed = execute_lua_script(
                    script_content, battle, attacker, target_player, 
                    attacker_role, target_role, source_attack_obj, last_damage_dealt_in_turn
                )
                log_entries.extend(before_logs)
                if state_changed:
                    state_changed_by_before_scripts = True
                    state_changed_this_turn = True
                    # Update last damage dealt if script caused damage
                    # TODO: Need a better way for lua scripts to report damage dealt for context
                    # last_damage_dealt_in_turn = ... 
            # Optionally remove the script after running, or keep it for duration/multiple turns
            # temp_registered_scripts.append(script_info) # Keep script if not removing
        else:
            temp_registered_scripts.append(script_info) # Keep other scripts
            
    battle.registered_scripts = temp_registered_scripts # Update the list
    # Re-check faint conditions after running all "before" scripts if state changed
    if state_changed_by_before_scripts:
        if getattr(battle, f'current_hp_{attacker_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{attacker.username} fainted from prior effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = target_player
             battle_ended = True
        elif getattr(battle, f'current_hp_{target_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{target_player.username} fainted from prior effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = attacker
             battle_ended = True
             
    # --- 2. Execute "On Attack" Script --- 
    if not battle_ended:
        action_details = {"attack_name": attack.name, "emoji": attack.emoji}
        add_log_entry({"source": attacker_role, "text": f"{attacker.username} used {attack.name}!", "effect_type": "action", "effect_details": action_details})
        
        if LUA_AVAILABLE and attack.lua_script_on_attack:
             print(f"--- Running 'on_attack' script for {attack.name} ---")
             on_attack_logs, state_changed = execute_lua_script(
                 attack.lua_script_on_attack, battle, attacker, target_player,
                 attacker_role, target_role, attack, last_damage_dealt_in_turn # Pass the attack itself as source
             )
             log_entries.extend(on_attack_logs)
             if state_changed:
                 state_changed_this_turn = True
                 # Update last damage dealt if script caused damage
                 # last_damage_dealt_in_turn = ...
        else:
             add_log_entry({"source": "system", "text": f"{attack.name} had no script or Lua is unavailable.", "effect_type": "info"})

        # --- Post "On Attack" Script Checks ---
        if state_changed_this_turn:
            if getattr(battle, f'current_hp_{attacker_role}') <= 0:
                 if battle.status != 'finished': 
                     add_log_entry({"source": "system", "text": f"{attacker.username} fainted!", "effect_type": "faint"})
                     battle.status = 'finished'
                     battle.winner = target_player 
                 battle_ended = True
            elif getattr(battle, f'current_hp_{target_role}') <= 0:
                 if battle.status != 'finished':
                     add_log_entry({"source": "system", "text": f"{target_player.username} fainted!", "effect_type": "faint"})
                     battle.status = 'finished'
                     battle.winner = attacker 
                 battle_ended = True

    # --- 3. Register "Before/After" Scripts for Opponent --- 
    if not battle_ended:
        newly_registered_scripts = []
        if LUA_AVAILABLE and attack.register_before_opponent and attack.lua_script_before_opponent:
            script_info = {
                "type": "before",
                "script": attack.lua_script_before_opponent,
                "source_attack_id": attack.id,
                "target_role": target_role # Register against the opponent
            }
            newly_registered_scripts.append(script_info)
            add_log_entry({"source": "system", "text": f"'{attack.name}' registered a 'before' effect on {target_player.username}.", "effect_type": "info"})
            
        if LUA_AVAILABLE and attack.register_after_opponent and attack.lua_script_after_opponent:
            script_info = {
                "type": "after",
                "script": attack.lua_script_after_opponent,
                "source_attack_id": attack.id,
                "target_role": target_role # Register against the opponent
            }
            newly_registered_scripts.append(script_info)
            add_log_entry({"source": "system", "text": f"'{attack.name}' registered an 'after' effect on {target_player.username}.", "effect_type": "info"})
        
        if newly_registered_scripts:
            # Append new scripts to the existing list
            current_registered = battle.registered_scripts
            current_registered.extend(newly_registered_scripts)
            battle.registered_scripts = current_registered # Assign back to trigger save
            state_changed_this_turn = True # Registering scripts counts as state change for saving

    # --- 4. Execute Registered "After" Scripts ---
    # Run scripts registered *against* the current attacker
    print(f"--- Checking registered 'after' scripts for {attacker_role} ---")
    # Use a temporary list to rebuild the registered scripts after processing
    current_registered_scripts = list(battle.registered_scripts)
    next_registered_scripts = [] 
    state_changed_by_after_scripts = False
    
    for script_info in current_registered_scripts:
        if script_info.get('type') == 'after' and script_info.get('target_role') == attacker_role:
            print(f"  Running 'after' script from Attack ID: {script_info.get('source_attack_id')}...")
            script_content = script_info.get('script')
            source_attack_obj = Attack.objects.filter(pk=script_info.get('source_attack_id')).first()
            
            if script_content:
                after_logs, state_changed = execute_lua_script(
                    script_content, battle, attacker, target_player, 
                    attacker_role, target_role, source_attack_obj, last_damage_dealt_in_turn
                )
                log_entries.extend(after_logs)
                if state_changed:
                    state_changed_by_after_scripts = True
                    state_changed_this_turn = True
                    # Update last damage dealt if script caused damage
                    # last_damage_dealt_in_turn = ... 
            # Optionally remove the script after running, or keep it
            # next_registered_scripts.append(script_info) # Keep script if not removing
        else:
            next_registered_scripts.append(script_info) # Keep other scripts
            
    battle.registered_scripts = next_registered_scripts # Update the list
    # Re-check faint conditions after running all "after" scripts
    if not battle_ended and state_changed_by_after_scripts:
        if getattr(battle, f'current_hp_{attacker_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{attacker.username} fainted from end-of-turn effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = target_player
             battle_ended = True
        elif getattr(battle, f'current_hp_{target_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{target_player.username} fainted from end-of-turn effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = attacker
             battle_ended = True
             
    # --- 5. Update Momentum and Turn --- 
    if not battle_ended:
        # Standard momentum gain from the attack used (scripts can modify momentum too)
        attacker_stages_now = battle.stat_stages_player1 if attacker_role == 'player1' else battle.stat_stages_player2
        min_gain, max_gain = calculate_momentum_gain_range(attack, attacker, attacker_stages_now)
        actual_gain = random.randint(min_gain, max_gain) if max_gain >= min_gain else 0
        momentum_attr = f'current_momentum_{attacker_role}'
        current_momentum = getattr(battle, momentum_attr) 
        new_momentum = current_momentum + actual_gain
        setattr(battle, momentum_attr, new_momentum)
        if actual_gain > 0:
            add_log_entry({"source": "system", "text": f"{attacker.username} built {actual_gain} momentum (Total: {new_momentum}).", "effect_type": "info"}) 
        
        # Turn switching logic
        opponent_momentum_attr = f'current_momentum_{target_role}'
        opponent_momentum = getattr(battle, opponent_momentum_attr)
        if new_momentum > opponent_momentum:
            battle.whose_turn = target_role
            add_log_entry({"source": "system", "text": f"It is now {target_player.username}'s turn!", "effect_type": "info"})
        # else: attacker keeps turn

    # --- Finalize --- 
    if not isinstance(battle.last_turn_summary, list):
         battle.last_turn_summary = [] 
    battle.last_turn_summary.extend(log_entries) # Append logs from this turn
    
    # Save battle state if anything changed (including script registration)
    if state_changed_this_turn or newly_registered_scripts: # Check if scripts were added
        print("--- Saving Battle State --- ")
        battle.save() 
    else:
        print("--- No state changes detected, skipping save --- ")

    return log_entries, battle_ended 