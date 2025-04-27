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
    Also calculates damage dealt per player for updating UserProfile stats.
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
    # --- NEW: Track damage per player ---
    damage_dealt_by_player = {'player1': 0, 'player2': 0}
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
        # --- Track which attacks were used by whom (Requires source_role) ---
        if effect_type == 'action' and source_role in ['player1', 'player2'] and attack_id:
            attacks_used_by_player[source_role].add(attack_id)

        # Aggregate damage (from logs created by apply_std_damage)
        if effect_type == 'damage':
            damage = details.get('damage_dealt')
            if isinstance(damage, int) and damage > 0:
                # Attribute damage to attack if source attack ID exists
                if attack_id:
                    damage_dealt_by_attack[attack_id] = damage_dealt_by_attack.get(attack_id, 0) + damage
                # --- NEW: Attribute damage to player if source role exists ---
                if source_role in ['player1', 'player2']:
                    damage_dealt_by_player[source_role] += damage
                # --- END NEW ---

        # Aggregate healing (from logs created by apply_std_hp_change)
        if effect_type == 'heal':
            healing = details.get('hp_change')
            if isinstance(healing, int) and healing > 0:
                 # Attribute healing to attack if source attack ID exists
                if attack_id:
                    healing_done_by_attack[attack_id] = healing_done_by_attack.get(attack_id, 0) + healing
                # Consider adding healing_done_by_player if needed later

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
            player_role_using_attack = None
            if attack_id in attacks_used_by_player['player1']:
                 player_role_using_attack = 'player1'
            elif attack_id in attacks_used_by_player['player2']:
                 player_role_using_attack = 'player2'
            
            if player_role_using_attack:
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
             # Optionally re-raise or log more details traceback.print_exc()

    print(f"  [Stats Update] Attack stats processed for Battle {battle.id}. Updated {updated_stats_count} stats records ({created_stats_count} created).")

    # --- NEW: Update Player Stats (Integration Point) ---
    # You need a function, likely on your User or UserProfile model,
    # that takes the battle result and updates the user's stats.
    # Example (assuming UserProfile has a method `update_stats_on_battle_end`):
    
    p1_damage = damage_dealt_by_player['player1']
    p2_damage = damage_dealt_by_player['player2']

    try:
        if battle.player1:
            # Example call - assuming User model has update_stats_on_battle_end
            battle.player1.update_stats_on_battle_end(
                is_winner=(winner == battle.player1),
                is_vs_bot=is_vs_bot,
                damage_dealt=p1_damage
            )
            print(f"  [Stats Update] Updated Player 1 ({battle.player1.username}) stats. Dmg dealt: {p1_damage}")
        else:
            print(f"  [Stats Update Warning] Could not update stats for Player 1 ({battle.player1.username if battle.player1 else 'N/A'})")

        if battle.player2:
            # Example call - assuming User model has update_stats_on_battle_end
            battle.player2.update_stats_on_battle_end(
                is_winner=(winner == battle.player2),
                is_vs_bot=is_vs_bot, # This assumes p2 is the only possible bot
                damage_dealt=p2_damage
            )
            print(f"  [Stats Update] Updated Player 2 ({battle.player2.username}) stats. Dmg dealt: {p2_damage}")
        else:
            print(f"  [Stats Update Warning] Could not update stats for Player 2 ({battle.player2.username if battle.player2 else 'N/A'})")
    except Exception as user_stat_error:
        print(f"  [Stats Update Error] Failed updating user profile stats: {user_stat_error}")
        import traceback # Optional: Log full traceback for debugging
        traceback.print_exc() # Optional: Log full traceback for debugging
        # Consider how to handle this - log, maybe retry?
        # Ensure atomicity is handled correctly if this happens within the outer transaction.

    print(f"  [Stats Update] Completed Processing for Battle {battle.id}.")
    # --- END NEW ---

# --- Main Action Logic --- 

def apply_attack(battle: Battle, attacker: User, attack: Attack):
    """
    Applies a single attack from the attacker in the battle.
    Modifies the battle object directly.
    Returns a list of log entries and whether the battle ended.
    Handles turn switching based on momentum SPENDING.
    Integrates Lua scripting for custom effects using the new trigger system.
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
    state_changed_this_turn = False # Track if any state changed overall

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

    def add_log_entry(entry):
         log_entries.append(entry)

    # =========================================================
    # --- BATTLE EXECUTION FLOW --- 
    # =========================================================

    current_registered_scripts = list(battle.registered_scripts) # Start with current list
    executed_once_scripts_this_action = set() # Track ONCE scripts executed

    def run_scripts_for_phase(phase_when: str, phase_actor: str):
        nonlocal battle_ended, state_changed_this_turn, current_registered_scripts
        if battle_ended: return

        print(f"--- Running Scripts: Phase='{phase_when}', Actor='{phase_actor}' ---")
        print(f"    [run_scripts_for_phase] START - current_registered_scripts: {current_registered_scripts}") # DEBUG START
        scripts_to_keep = []
        scripts_to_run_now = []
        phase_state_changed = False

        # Identify scripts to run in this phase
        for script_instance in current_registered_scripts:
            script_id = script_instance.get('script_id')
            reg_id = script_instance.get('registration_id')
            trigger_who = script_instance.get('trigger_who')
            trigger_when = script_instance.get('trigger_when')
            trigger_duration = script_instance.get('trigger_duration')
            orig_attacker = script_instance.get('original_attacker_role')
            orig_target = script_instance.get('original_target_role')

            if reg_id in executed_once_scripts_this_action:
                scripts_to_keep.append(script_instance) # Already ran this action, keep persistent
                continue

            # --- REVISED: Trigger Matching Logic --- 
            run_this_script = False
            # Always check trigger_when first
            if trigger_when == phase_when:
                # Determine if the trigger's 'who' matches the current phase actor
                if trigger_who == 'ME' and phase_actor == orig_attacker:
                    run_this_script = True
                elif trigger_who == 'ENEMY' and phase_actor == orig_target:
                    run_this_script = True
                elif trigger_who == 'ANY' and phase_actor in ['player1', 'player2']:
                    # 'ANY' means it runs if the current actor matches the phase, regardless of original attacker/target
                    run_this_script = True
            # --- END REVISED --- 

            if run_this_script:
                scripts_to_run_now.append(script_instance)
            else:
                scripts_to_keep.append(script_instance) # Doesn't run this phase, keep it

        # Execute the identified scripts
        scripts_that_ran_or_didnt_run = scripts_to_keep[:] # Start with scripts not running this phase
        for script_instance in scripts_to_run_now:
            script_id = script_instance.get('script_id')
            reg_id = script_instance.get('registration_id')
            trigger_duration = script_instance.get('trigger_duration')

            script_obj = Script.objects.filter(pk=script_id).first()
            source_attack_id = script_instance.get('source_attack_id')
            source_attack_obj = Attack.objects.filter(pk=source_attack_id).first() if source_attack_id else None

            if script_obj and script_obj.lua_code:
                print(f"  Running Script ID {script_id} (RegID: {reg_id[:8]}) - Who: {script_instance['trigger_who']}, When: {script_instance['trigger_when']}, Dur: {trigger_duration}")
                # Execute and get potentially updated script list
                script_logs, state_changed, updated_script_list_from_lua = execute_lua_script(
                    script_obj.lua_code, battle,
                    attacker, target_player,
                    attacker_role, target_role,
                    source_attack_obj,
                    script_instance
                )
                log_entries.extend(script_logs)
                if state_changed:
                    phase_state_changed = True
                    state_changed_this_turn = True
                    # IMPORTANT: Update the main list immediately if Lua changed it (e.g., unregister_script)
                    current_registered_scripts = updated_script_list_from_lua
                    print(f"    [run_scripts_for_phase] AFTER Lua Execution (RegID: {reg_id[:8]}) - current_registered_scripts: {current_registered_scripts}") # DEBUG AFTER LUA

                # Handle ONCE duration - mark for removal AFTER successful execution
                # This removal happens from the `current_registered_scripts` list now
                if trigger_duration == 'ONCE' and reg_id: # Check reg_id exists
                    executed_once_scripts_this_action.add(reg_id)
                    add_log_entry({"source": "debug", "text": f"Script instance {reg_id[:8]} (ONCE) executed and will be removed.", "effect_type": "debug"})
                    # Removal happens later by filtering current_registered_scripts
                # No explicit keeping needed here, the list is updated if Lua changed it
            else:
                add_log_entry({"source": "system", "text": f"Could not find or execute registered script ID {script_id} (RegID: {reg_id[:8]})", "effect_type": "error"})
                # If script failed to load/run, it remains in current_registered_scripts unless Lua removed it

        # Filter out executed ONCE scripts AFTER the loop
        # Use the potentially updated list from Lua modifications
        final_scripts_for_next_phase = [
            s for s in current_registered_scripts 
            if s.get('registration_id') not in executed_once_scripts_this_action
        ]
        current_registered_scripts = final_scripts_for_next_phase
        print(f"    [run_scripts_for_phase] AFTER ONCE Filtering - current_registered_scripts: {current_registered_scripts}") # DEBUG AFTER ONCE FILTER

        # --- Faint Checks after phase --- 
        if phase_state_changed:
            check_faint_conditions()

    def check_faint_conditions():
        nonlocal battle_ended
        if battle_ended: return
        if getattr(battle, f'current_hp_{attacker_role}') <= 0:
            add_log_entry({"source": "system", "text": f"{attacker.username} fainted!", "effect_type": "faint"})
            battle.status = 'finished'
            battle.winner = target_player
            battle_ended = True
        elif getattr(battle, f'current_hp_{target_role}') <= 0:
            add_log_entry({"source": "system", "text": f"{target_player.username} fainted!", "effect_type": "faint"})
            battle.status = 'finished'
            battle.winner = attacker
            battle_ended = True

    # ==================================
    # === 1. START OF TURN PHASE ===
    # ==================================
    run_scripts_for_phase('BEFORE_TURN', attacker_role)
    if battle_ended: # Check end after phase
        # Finalize and return immediately if battle ended here
        if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
        battle.last_turn_summary.extend(log_entries)
        battle.save()
        if battle.status == 'finished': update_attack_stats_from_battle_log(battle)
        return log_entries, battle_ended

    # ==================================
    # === 2. BEFORE ATTACK PHASE ===
    # ==================================
    run_scripts_for_phase('BEFORE_ATTACK', attacker_role)
    if battle_ended: # Check end after phase
        if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
        battle.last_turn_summary.extend(log_entries)
        battle.save()
        if battle.status == 'finished': update_attack_stats_from_battle_log(battle)
        return log_entries, battle_ended

    # ==================================
    # === 3. ON ATTACK USE PHASE ===
    # ==================================
    print(f"--- Running Scripts: Phase='ON_USE', Actor='{attacker_role}' ---")
    newly_registered_scripts_this_turn = []
    on_use_state_changed = False
    for script in attack.scripts.all():
        # Only run ON_USE scripts here
        if script.trigger_when == 'ON_USE':
            if LUA_AVAILABLE and script.lua_code:
                print(f"  Running ON_USE Script ID {script.id} ({script.name}) for {attack.name}")
                phase_info = {'when': 'ON_USE', 'actor': attacker_role}
                # For ON_USE, script_instance is None initially
                script_logs, state_changed, _ = execute_lua_script(
                    script.lua_code, battle, attacker, target_player,
                    attacker_role, target_role, attack, None
                )
                log_entries.extend(script_logs)
                if state_changed:
                    on_use_state_changed = True
                    state_changed_this_turn = True
            else:
                add_log_entry({"source": "debug", "text": f"ON_USE Script ID {script.id} ({script.name}) for {attack.name} has no code or Lua is unavailable.", "effect_type": "debug"})

        # --- Register PERSISTENT/ONCE scripts for the FUTURE --- 
        # Check if the script is NOT an ON_USE trigger, meaning it should be registered
        if script.trigger_when != 'ON_USE':
            script_instance_data = {
                "registration_id": str(uuid.uuid4()),
                "start_turn": battle.turn_number,
                "script_id": script.id,
                "trigger_who": script.trigger_who,
                "trigger_when": script.trigger_when,
                "trigger_duration": script.trigger_duration,
                "source_attack_id": attack.id,
                "original_attacker_role": attacker_role, # Who used the attack
                "original_target_role": target_role,   # Who was targeted by the attack
            }
            newly_registered_scripts_this_turn.append(script_instance_data)
            target_desc = script.get_trigger_who_display() # Get friendly name
            add_log_entry({"source": "debug", "text": f"'{attack.name}' registered script '{script.name}' (Who: {target_desc}, When: {script.get_trigger_when_display()}, Dur: {script.get_trigger_duration_display()}). RegID: {script_instance_data['registration_id'][:8]}", "effect_type": "debug"})

    # Add newly registered scripts to the list for subsequent phases
    if newly_registered_scripts_this_turn:
        current_registered_scripts.extend(newly_registered_scripts_this_turn)
        state_changed_this_turn = True # Registration is a state change

    # --- Faint Check after ON_USE --- 
    if on_use_state_changed:
        check_faint_conditions()

    print(f"--- DEBUG: After ON_USE scripts ---")
    print(f"  Battle Ended Flag: {battle_ended}")
    print(f"  HP P1: {getattr(battle, f'current_hp_player1')}, HP P2: {getattr(battle, f'current_hp_player2')}")
    print(f"  Current Registered Scripts: {current_registered_scripts}")
    # --- ADDED Debug Save --- 
    battle.registered_scripts = current_registered_scripts # Assign current list to model field
    battle.save(update_fields=['registered_scripts']) # Save ONLY this field
    print(f"    [DEBUG SAVE] Saved registered_scripts: {battle.registered_scripts}")
    # --- End Debug Save ---

    # --- Add Attack to Used List (AFTER ON_USE effects) --- 
    if not battle_ended:
        if attacker_role == 'player1':
            battle.player1_attacks_used.add(attack)
        else:
            battle.player2_attacks_used.add(attack)
        # Note: Saving happens later
    # --- End Add Attack --- 

    if battle_ended: # Check end after phase
        if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
        battle.last_turn_summary.extend(log_entries)
        battle.registered_scripts = current_registered_scripts # Save potentially updated list
        battle.save()
        if battle.status == 'finished': 
            # Move stat update call here, AFTER final save
            try:
                update_attack_stats_from_battle_log(battle)
            except Exception as stat_calc_error:
                print(f"!!! ERROR during post-battle stat calculation for Battle {battle.id}: {stat_calc_error}")
                import traceback
                traceback.print_exc()
        return log_entries, battle_ended

    print(f"--- DEBUG: Before AFTER_ATTACK scripts ---")
    # ==================================
    # === 4. AFTER ATTACK PHASE ===
    # ==================================
    # Run for both attacker and target context if relevant scripts exist
    run_scripts_for_phase('AFTER_ATTACK', attacker_role)
    if not battle_ended: # Don't run target's if attacker fainted
        run_scripts_for_phase('AFTER_ATTACK', target_role)

    if battle_ended: # Check end after phase
        if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
        battle.last_turn_summary.extend(log_entries)
        battle.registered_scripts = current_registered_scripts # Save potentially updated list
        battle.save()
        if battle.status == 'finished': 
            # Move stat update call here, AFTER final save
            try:
                update_attack_stats_from_battle_log(battle)
            except Exception as stat_calc_error:
                print(f"!!! ERROR during post-battle stat calculation for Battle {battle.id}: {stat_calc_error}")
                import traceback
                traceback.print_exc()
        return log_entries, battle_ended

    print(f"--- DEBUG: Before MOMENTUM phase ---")
    print(f"  Momentum P1: {getattr(battle, f'current_momentum_player1')}, Momentum P2: {getattr(battle, f'current_momentum_player2')}")
    print(f"  Attack Base Cost: {attack.momentum_cost}")
    # ==================================
    # === 5. MOMENTUM & TURN SWITCH PHASE ===
    # ==================================
    next_turn_role = attacker_role # Assume turn doesn't switch
    turn_incremented = False

    attacker_stages_now = battle.stat_stages_player1 if attacker_role == 'player1' else battle.stat_stages_player2
    attacker_base_stats = {
        'hp': attacker.hp, 'attack': attacker.attack,
        'defense': attacker.defense, 'speed': attacker.speed
    }
    min_cost, max_cost = calculate_momentum_cost_range(attack.momentum_cost, attacker_base_stats, attacker_stages_now)
    actual_cost = random.randint(min_cost, max_cost) if max_cost >= min_cost else 0

    momentum_attr = f'current_momentum_{attacker_role}'
    current_momentum = getattr(battle, momentum_attr)
    opponent_momentum_attr = f'current_momentum_{target_role}'
    opponent_momentum = getattr(battle, opponent_momentum_attr)

    if current_momentum >= actual_cost:
        new_momentum = current_momentum - actual_cost
        setattr(battle, momentum_attr, new_momentum)
        add_log_entry({
            "source": "debug", "text": f"{attacker.username} spent {actual_cost} momentum ({new_momentum} left).",
            "effect_type": "momentum", "effect_details": {"target_role": attacker_role, "new_momentum": new_momentum, "cost": actual_cost}
        })
        # Turn does NOT switch, next_turn_role remains attacker_role
    else:
        overflow_cost = actual_cost - current_momentum
        setattr(battle, momentum_attr, 0)
        new_opponent_momentum = opponent_momentum + overflow_cost
        setattr(battle, opponent_momentum_attr, new_opponent_momentum)
        battle.whose_turn = target_role # Switch turn
        battle.turn_number += 1
        turn_incremented = True
        next_turn_role = target_role # Update who acts next
        add_log_entry({
            "source": "debug",
            "text": f"{attacker.username} lacked momentum ({current_momentum}/{actual_cost}). Overflow {overflow_cost} given to {target_player.username}.",
            "effect_type": "momentum", "effect_details": {"target_role": target_role, "new_momentum": new_opponent_momentum, "overflow": overflow_cost}
        })
        add_log_entry({"source": "system", "text": f"Turn {battle.turn_number}: It is now {target_player.username}'s turn!", "effect_type": "turnchange"})

    state_changed_this_turn = True # Momentum change always counts

    # ==================================
    # === 6. END OF TURN PHASE ===
    # ==================================
    # Run AFTER_TURN scripts based on who acted THIS turn (attacker_role)
    run_scripts_for_phase('AFTER_TURN', attacker_role)
    if not battle_ended: # Check if target has AFTER_TURN effects relevant now
         run_scripts_for_phase('AFTER_TURN', target_role)

    # Final faint check after all effects for the turn
    check_faint_conditions()

    # ==================================
    # === 7. FINALIZE & SAVE ===
    # ==================================
    if not isinstance(battle.last_turn_summary, list):
         battle.last_turn_summary = []
    battle.last_turn_summary.extend(log_entries) # Append logs from this turn

    # Save the final registered script list (after ONCE removals)
    print(f"--- DEBUG: Finalizing Turn {battle.turn_number}. Assigning registered scripts before save: {current_registered_scripts} ---")
    battle.registered_scripts = current_registered_scripts

    # --- Save Battle State FIRST ---
    try:
        battle.save()
        print(f"    [Battle {battle.id}] Saved state. Turn: {battle.turn_number}, Whose Turn: {battle.whose_turn}, Status: {battle.status}")
    except Exception as e:
        print(f"!!! ERROR saving battle state for Battle {battle.id}: {e}")
        return log_entries, battle_ended # Return early?

    # --- CALL NEW STAT UPDATE FUNCTION *AFTER* SAVING BATTLE ---
    # --- MOVED THIS CALL TO EARLIER IN THE FLOW, AFTER SAVING THE FINAL STATE ---
    # if battle.status == 'finished':
    #     try:
    #         update_attack_stats_from_battle_log(battle)
    #     except Exception as stat_calc_error:
    #         print(f"!!! ERROR during post-battle stat calculation for Battle {battle.id}: {stat_calc_error}")
    #         import traceback
    #         traceback.print_exc()

    return log_entries, battle_ended 