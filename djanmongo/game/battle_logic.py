import random
import math
import uuid
from .models import Battle, Attack, Script, AttackUsageStats
from users.models import User # Although we get users via battle object
from django.db import transaction # Import transaction for atomic updates
from django.core.exceptions import ObjectDoesNotExist # For attack lookup

# --- NEW: Function to Update Stats from Log ---
@transaction.atomic # Ensure atomicity for stat updates
def update_attack_stats_from_battle_log(battle: Battle):
    """
    Parses the battle log (last_turn_summary) of a finished battle
    and updates the AttackUsageStats accordingly.
    """
    if battle.status != 'finished':
        print(f"[Stats Update] Battle {battle.id} not finished. Skipping.")
        return

    print(f"[Stats Update] Processing finished Battle {battle.id}...")
    winner = battle.winner
    loser = battle.player1 if winner == battle.player2 else battle.player2
    winner_role = battle.get_player_role(winner) if winner else None
    loser_role = battle.get_player_role(loser) if loser else None
    is_vs_bot = battle.player2_is_ai_controlled # Check if p2 was the bot

    # --- Aggregated data from this battle's log ---
    damage_dealt_by_attack = {} # {attack_id: total_damage}
    healing_done_by_attack = {} # {attack_id: total_healing}
    attacks_used_by_player = {'player1': set(), 'player2': set()} # {role: set(attack_id)}
    # ---------------------------------------------

    if not isinstance(battle.last_turn_summary, list):
        print(f"  [Stats Update Warning] Invalid log format for Battle {battle.id}. Cannot update stats.")
        return

    # --- Parse the entire battle log ---
    for log_entry in battle.last_turn_summary:
        if not isinstance(log_entry, dict): continue

        effect_type = log_entry.get('effect_type')
        details = log_entry.get('effect_details')
        source_role = log_entry.get('source') # player1 or player2

        if not isinstance(details, dict): continue

        attack_id = details.get('source_attack_id')
        if not attack_id: continue # Need attack ID to attribute stats

        # Track which attacks were used by whom
        if effect_type == 'action' and source_role in ['player1', 'player2']:
            attacks_used_by_player[source_role].add(attack_id)

        # Aggregate damage (from logs created by apply_std_damage)
        if effect_type == 'damage':
            damage = details.get('damage_dealt')
            if isinstance(damage, int) and damage > 0:
                damage_dealt_by_attack[attack_id] = damage_dealt_by_attack.get(attack_id, 0) + damage

        # Aggregate healing (from logs created by apply_std_hp_change)
        if effect_type == 'heal':
            healing = details.get('hp_change')
            if isinstance(healing, int) and healing > 0:
                healing_done_by_attack[attack_id] = healing_done_by_attack.get(attack_id, 0) + healing

    # --- Update AttackUsageStats based on aggregated data ---
    all_used_attack_ids = attacks_used_by_player['player1'].union(attacks_used_by_player['player2'])

    # Fetch stats objects in bulk for efficiency if possible, or handle individually
    stats_objects = {stat.attack_id: stat for stat in AttackUsageStats.objects.filter(attack_id__in=all_used_attack_ids)}
    created_stats_count = 0
    updated_stats_count = 0

    for attack_id in all_used_attack_ids:
        try:
            # Get existing or create new stats object
            stats = stats_objects.get(attack_id)
            if not stats:
                # Ensure attack exists before creating stats for it
                attack_instance = Attack.objects.get(pk=attack_id)
                stats, created = AttackUsageStats.objects.get_or_create(attack=attack_instance)
                if created: created_stats_count += 1
                stats_objects[attack_id] = stats # Add to cache
            else:
                created = False # Already existed

            # Increment times used
            stats.times_used += 1

            # Add damage/healing totals
            stats.total_damage_dealt += damage_dealt_by_attack.get(attack_id, 0)
            stats.total_healing_done += healing_done_by_attack.get(attack_id, 0)

            # Increment win/loss counts
            is_winner_attack = winner_role and attack_id in attacks_used_by_player.get(winner_role, set())
            is_loser_attack = loser_role and attack_id in attacks_used_by_player.get(loser_role, set())

            if is_vs_bot:
                if is_winner_attack: stats.wins_vs_bot += 1
                if is_loser_attack: stats.losses_vs_bot += 1
            else: # vs Human
                if is_winner_attack: stats.wins_vs_human += 1
                if is_loser_attack: stats.losses_vs_human += 1

            # Update co-occurrence (simplified example - only counts pairs within this battle)
            # A more robust implementation might require a separate, more complex aggregation step
            player_role_using_attack = 'player1' if attack_id in attacks_used_by_player['player1'] else 'player2'
            co_used_attacks_in_battle = attacks_used_by_player[player_role_using_attack] - {attack_id} # Other attacks used by same player

            if not isinstance(stats.co_used_with_counts, dict): stats.co_used_with_counts = {} # Ensure it's a dict

            for other_attack_id in co_used_attacks_in_battle:
                other_attack_id_str = str(other_attack_id) # JSON keys must be strings
                stats.co_used_with_counts[other_attack_id_str] = stats.co_used_with_counts.get(other_attack_id_str, 0) + 1

            stats.save()
            updated_stats_count +=1

        except Attack.DoesNotExist:
             print(f"  [Stats Update Warning] Attack ID {attack_id} not found. Cannot update its stats.")
        except Exception as e:
             print(f"  [Stats Update Error] Failed processing Attack ID {attack_id}: {e}")

    print(f"  [Stats Update] Completed for Battle {battle.id}. Updated {updated_stats_count} stats records ({created_stats_count} created).")

# --- Main Action Logic --- 

def apply_attack(battle: Battle, attacker: User, attack: Attack):
    """
    Applies a single attack from the attacker in the battle.
    Modifies the battle object directly.
    Returns a list of log entries and whether the battle ended.
    Handles turn switching based on momentum SPENDING.
    Integrates Lua scripting for custom effects based on the new Script model.
    Updates AttackUsageStats when the battle ends.
    """
    # --- Imports from refactored modules ---
    from .logic import (
        calculate_momentum_cost_range, clamp,
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
         
    # =========================================================
    # --- PHASE 1: START OF CURRENT PLAYER'S TURN EFFECTS --- 
    # =========================================================
    print(f"--- Checking registered scripts for START of {attacker_role}'s turn ({battle.turn_number}) ---")
    current_registered_scripts = list(battle.registered_scripts)
    next_registered_scripts_phase1 = [] # Use separate list for this phase
    state_changed_by_start_scripts = False

    for script_instance in current_registered_scripts:
        run_this_script = False
        script_trigger_type = script_instance.get('trigger_type')
        script_target_role = script_instance.get('target_role')
        
        # --- MODIFIED TRIGGER CHECK --- 
        # Check triggers relevant to the START of the CURRENT player's turn
        if script_trigger_type == 'before_attacker_turn' and script_target_role == attacker_role:
            # Applies to the original attacker at the start of their turn
            run_this_script = True
        elif script_trigger_type == 'before_target_turn' and script_target_role == attacker_role: 
            # Applies to the original target at the start of THEIR turn (which is now)
            run_this_script = True 
        # --- END MODIFIED CHECK ---
        
        if run_this_script:
            script_id = script_instance.get('script_id')
            script_obj = Script.objects.filter(pk=script_id).first()
            source_attack_id = script_instance.get('source_attack_id')
            source_attack_obj = Attack.objects.filter(pk=source_attack_id).first() if source_attack_id else None
            
            if script_obj and script_obj.lua_code:
                print(f"  Running script ID {script_id} ({script_obj.name}) triggered by {script_trigger_type} on {script_target_role}")
                # TODO: Refine context for script execution based on trigger type
                start_logs, state_changed = execute_lua_script(
                    script_obj.lua_code, battle, 
                    attacker, # Who is acting this turn
                    target_player, # The other player
                    attacker_role, # Role of the actor 
                    target_role, # Role of the other player
                    source_attack_obj, # Attack that registered this script
                    script_instance # Pass the instance data
                )
                log_entries.extend(start_logs)
                if state_changed:
                    state_changed_by_start_scripts = True
                    state_changed_this_turn = True
            else:
                add_log_entry({"source": "system", "text": f"Could not find or execute registered script ID {script_id}", "effect_type": "error"})
             # Always keep the script registration unless explicitly unregistered later
             # next_registered_scripts.append(script_instance) <-- REMOVE FROM HERE

        # Keep the script instance for the next phase/turn unless unregistered by Lua
        next_registered_scripts_phase1.append(script_instance)
        # --- END MODIFICATION --- 

    battle.registered_scripts = next_registered_scripts_phase1 # Update list after phase 1 checks
    # Re-check faint conditions after running start-of-turn scripts
    if state_changed_by_start_scripts:
        if getattr(battle, f'current_hp_{attacker_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{attacker.username} fainted from start-of-turn effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = target_player
             battle_ended = True
        elif getattr(battle, f'current_hp_{target_role}') <= 0:
             add_log_entry({"source": "system", "text": f"{target_player.username} fainted from start-of-turn effects!", "effect_type": "faint"})
             battle.status = 'finished'
             battle.winner = attacker
             battle_ended = True

    # =========================================================
    # --- PHASE 2: ATTACK EXECUTION & REGISTRATION --- 
    # =========================================================
    if not battle_ended:
        # REMOVED Python-level action log:
        # action_details = {"attack_name": attack.name, "emoji": attack.emoji}
        # add_log_entry({"source": attacker_role, "text": f"{attacker.username} used {attack.name}!", "effect_type": "action", "effect_details": action_details})
        
        newly_registered_scripts = []
        state_changed_by_on_attack = False
        
        # Use the potentially updated list from phase 1
        scripts_to_process_phase2 = list(battle.registered_scripts)
        
        # Iterate through scripts associated with the ATTACK being used now
        for script in attack.scripts.all():
            if LUA_AVAILABLE and script.lua_code:
                # 1. Execute "On Attack Use" scripts
                if script.trigger_on_attack:
                    print(f"--- Running 'on_attack' script ID {script.id} ({script.name}) for {attack.name} ---")
                    on_attack_logs, state_changed = execute_lua_script(
                         script.lua_code, battle, attacker, target_player,
                         attacker_role, target_role, attack, 
                         # Context specific to this trigger
                         {"trigger_type": "on_attack", "script_id": script.id}
                    )
                    log_entries.extend(on_attack_logs)
                    if state_changed:
                        state_changed_by_on_attack = True
                        state_changed_this_turn = True
                
                # 2. Register PERSISTENT scripts for future turns
                trigger_map = {
                    'trigger_before_attacker_turn': 'before_attacker_turn',
                    'trigger_after_attacker_turn': 'after_attacker_turn',
                    'trigger_before_target_turn': 'before_target_turn',
                    'trigger_after_target_turn': 'after_target_turn',
                }
                for field_name, trigger_type in trigger_map.items():
                    if getattr(script, field_name):
                        # Determine target for registration
                        reg_target_role = attacker_role if 'attacker' in field_name else target_role
                        reg_player_name = attacker.username if reg_target_role == attacker_role else target_player.username
                        
                        script_instance_data = {
                            "registration_id": str(uuid.uuid4()),
                            "start_turn": battle.turn_number,
                            "script_id": script.id,
                            "trigger_type": trigger_type,
                            "target_role": reg_target_role, # Who the script instance targets
                            "source_attack_id": attack.id,
                            "original_attacker_role": attacker_role, # Who used the attack
                            "original_target_role": target_role, # Who was targeted by the attack
                        }
                        newly_registered_scripts.append(script_instance_data)
                        add_log_entry({"source": "debug", "text": f"'{attack.name}' registered script '{script.name}' ({trigger_type}) on {reg_player_name}.", "effect_type": "debug"})
            else:
                 if script.trigger_on_attack: # Log if an on-attack script couldn't run
                     add_log_entry({"source": "debug", "text": f"Script ID {script.id} ({script.name}) for {attack.name} has no code or Lua is unavailable.", "effect_type": "debug"})

        # Append new scripts to the list from phase 1
        if newly_registered_scripts:
            scripts_to_process_phase2.extend(newly_registered_scripts)
            battle.registered_scripts = scripts_to_process_phase2 # Update list after phase 2
            state_changed_this_turn = True 

        # --- Post "On Attack" Script Faint Checks --- (After ALL on-attack scripts run)
        if state_changed_by_on_attack: # Check only if on-attack scripts modified state
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

        # --- !!! ADD ATTACK TO USED LIST !!! ---
        # Add the attack after its initial effects/scripts are processed
        if attacker_role == 'player1':
            battle.player1_attacks_used.add(attack)
        else: # attacker_role == 'player2'
            battle.player2_attacks_used.add(attack)
        # ----------------------------------------

    # =========================================================
    # --- PHASE 3: END OF CURRENT PLAYER'S TURN EFFECTS --- 
    # =========================================================
    if not battle_ended:
        print(f"--- Checking registered scripts for END of {attacker_role}'s turn ({battle.turn_number}) ---")
        # Use the potentially updated list from phase 2
        current_registered_scripts_phase3 = list(battle.registered_scripts)
        next_registered_scripts_final = [] # Final list for this turn
        state_changed_by_end_scripts = False
        
        for script_instance in current_registered_scripts_phase3:
            run_this_script = False
            script_trigger_type = script_instance.get('trigger_type')
            script_target_role = script_instance.get('target_role')
            
            # --- MODIFIED TRIGGER CHECK --- 
            # Check triggers relevant to the END of the CURRENT player's turn
            if script_trigger_type == 'after_attacker_turn' and script_target_role == attacker_role:
                # Applies to the original attacker at the end of their turn
                run_this_script = True
            elif script_trigger_type == 'after_target_turn' and script_target_role == attacker_role:
                # Applies to the original target at the end of THEIR turn (which is now)
                run_this_script = True
            # --- END MODIFIED CHECK ---
            
            if run_this_script:
                script_id = script_instance.get('script_id')
                script_obj = Script.objects.filter(pk=script_id).first()
                source_attack_id = script_instance.get('source_attack_id')
                source_attack_obj = Attack.objects.filter(pk=source_attack_id).first() if source_attack_id else None
                
                if script_obj and script_obj.lua_code:
                    print(f"  Running script ID {script_id} ({script_obj.name}) triggered by {script_trigger_type} on {script_target_role}")
                    end_logs, state_changed = execute_lua_script(
                        script_obj.lua_code, battle, 
                        attacker, target_player, 
                        attacker_role, target_role,
                        source_attack_obj, 
                        script_instance
                    )
                    log_entries.extend(end_logs)
                    if state_changed:
                        state_changed_by_end_scripts = True
                        state_changed_this_turn = True
                else:
                    add_log_entry({"source": "system", "text": f"Could not find or execute registered script ID {script_id}", "effect_type": "error"})
                 # Always keep the script registration unless explicitly unregistered later
                 # next_registered_scripts.append(script_instance) <-- REMOVE FROM HERE

            # Keep the script instance for the next turn unless unregistered by Lua
            next_registered_scripts_final.append(script_instance)
            # --- END MODIFICATION --- 

        battle.registered_scripts = next_registered_scripts_final # Update list after phase 3
        # Re-check faint conditions after end-of-turn scripts
        if state_changed_by_end_scripts:
            if getattr(battle, f'current_hp_{attacker_role}') <= 0:
                if battle.status != 'finished':
                     add_log_entry({"source": "system", "text": f"{attacker.username} fainted from end-of-turn effects!", "effect_type": "faint"})
                     battle.status = 'finished'
                     battle.winner = target_player
                battle_ended = True
            elif getattr(battle, f'current_hp_{target_role}') <= 0:
                 if battle.status != 'finished':
                     add_log_entry({"source": "system", "text": f"{target_player.username} fainted from end-of-turn effects!", "effect_type": "faint"})
                     battle.status = 'finished'
                     battle.winner = attacker
                 battle_ended = True
             
    # =========================================================
    # --- PHASE 4: UPDATE MOMENTUM & TURN (REWORKED) --- 
    # =========================================================
    if not battle_ended:
        attacker_stages_now = battle.stat_stages_player1 if attacker_role == 'player1' else battle.stat_stages_player2
        
        # 1. Calculate Actual Momentum Cost
        # Construct base stats dict from the user object
        attacker_base_stats = {
            'hp': attacker.hp,
            'attack': attacker.attack,
            'defense': attacker.defense,
            'speed': attacker.speed
        }
        # Pass momentum cost (integer) and stats dict
        min_cost, max_cost = calculate_momentum_cost_range(attack.momentum_cost, attacker_base_stats, attacker_stages_now)
        actual_cost = random.randint(min_cost, max_cost) if max_cost >= min_cost else 0
        
        # add_log_entry({"source": "system", "text": f"({attack.name} cost: {actual_cost} momentum)", "effect_type": "debug"})

        # 2. Apply Cost and Check Turn Switch
        momentum_attr = f'current_momentum_{attacker_role}'
        current_momentum = getattr(battle, momentum_attr)
        opponent_momentum_attr = f'current_momentum_{target_role}'
        opponent_momentum = getattr(battle, opponent_momentum_attr)

        if current_momentum >= actual_cost:
            # Enough momentum, spend it and keep turn
            new_momentum = current_momentum - actual_cost
            setattr(battle, momentum_attr, new_momentum)
            add_log_entry({
                "source": "debug",
                "text": f"{attacker.username} has {new_momentum} momentum remaining.", 
                "effect_type": "momentum",
                "effect_details": {
                    "target_role": attacker_role,
                    "new_momentum": new_momentum
                }
                })
            # DO NOT increment turn number here
        else:
            # Not enough momentum, spend all, give overflow to opponent, switch turn
            overflow_cost = actual_cost - current_momentum
            setattr(battle, momentum_attr, 0) # Attacker momentum becomes 0
            
            new_opponent_momentum = opponent_momentum + overflow_cost
            setattr(battle, opponent_momentum_attr, new_opponent_momentum)
            
            # --- ADD MOMENTUM SWING LOG --- 
            add_log_entry({
                "source": "debug", 
                "text": f"Momentum swings to {target_player.username}!", 
                "effect_type": "momentum", 
                "effect_details": { # Optional details for potential frontend use
                    "target_role": target_role,
                    "new_momentum": new_opponent_momentum
                }
            })
            # --- END MOMENTUM SWING LOG --- 
            
            battle.whose_turn = target_role # Switch turn
            battle.turn_number += 1 # Increment turn number ONLY when turn passes
            
            add_log_entry({"source": "debug", "text": f"{attacker.username} uses remaining {current_momentum} momentum. {overflow_cost} overflow given to {target_player.username} ({new_opponent_momentum} total).", "effect_type": "debug"})
            add_log_entry({"source": "system", "text": f"Turn {battle.turn_number}: It is now {target_player.username}'s turn!", "effect_type": "turnchange"})
            
        state_changed_this_turn = True # Momentum change always counts

    # =========================================================
    # --- FINALIZE --- 
    # =========================================================
    if not isinstance(battle.last_turn_summary, list):
         battle.last_turn_summary = [] 
    battle.last_turn_summary.extend(log_entries) # Append logs from this turn
    
    # --- Save Battle State FIRST ---
    try:
        battle.save() # Save the final battle state (winner, status etc.)
        print(f"    [Battle {battle.id}] Saved final state for turn {battle.turn_number-1 if battle_ended else battle.turn_number}. Status: {battle.status}, Winner: {battle.winner}")
    except Exception as e:
        print(f"!!! ERROR saving battle state for Battle {battle.id}: {e}")
        # If save fails, we probably shouldn't update stats
        return log_entries, battle_ended # Return early?

    # --- CALL NEW STAT UPDATE FUNCTION *AFTER* SAVING BATTLE ---
    if battle.status == 'finished':
        try:
            # Call the function to process logs and update AttackUsageStats
            update_attack_stats_from_battle_log(battle)
        except Exception as stat_calc_error:
            # Log errors during stat calculation but don't fail the main request
            print(f"!!! ERROR during post-battle stat calculation for Battle {battle.id}: {stat_calc_error}")
            import traceback
            traceback.print_exc() # Log full traceback

    return log_entries, battle_ended 