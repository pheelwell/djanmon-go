import requests
import json
import time
import random
import itertools
import logging
import sys
import os
from collections import defaultdict
import re # For parsing damage from logs
import multiprocessing # <-- Added
from functools import partial # <-- Added

# Need to ensure Django models are loaded correctly in child processes
import django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djanmongo.settings') # Adjust if needed
# django.setup() # Ensure Django is setup

from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import connections # <-- Added for connection handling

from users.models import User
from game.models import Attack, Battle, Script
from game.battle_logic import apply_attack

# --- Configuration ---
MAX_BATTLE_TURNS = 100
BASE_API_URL = "http://127.0.0.1:8000"
GENERATION_TEST_USERNAME = "q"
GENERATION_TEST_PASSWORD = "1"
LOG_FILE = "simulation_log.txt"
NUM_PROCESSES = multiprocessing.cpu_count() # Use available CPU cores
NUM_SETS_TO_SELECT = 5 # Number of attack sets to randomly select if not skipping generation

# --- Archetypes (Stats) ---
ARCHETYPES = {
    # ... (keep existing archetypes) ...
    "Balanced": {'attack': 100, 'defense': 100, 'speed': 100},
    "GlassCannon": {'attack': 150, 'defense': 50, 'speed': 100},
    "Tank": {'attack': 50, 'defense': 150, 'speed': 100},
    "Speedster": {'attack': 100, 'defense': 50, 'speed': 150},
    "Bruiser": {'attack': 150, 'defense': 100, 'speed': 50},
    "BulkySpeed": {'attack': 50, 'defense': 100, 'speed': 150},
    "Defensive": {'attack': 50, 'defense': 150, 'speed': 100},
    "DefensiveSpeed": {'attack': 50, 'defense': 100, 'speed': 150},
    "DefensiveTank": {'attack': 50, 'defense': 150, 'speed': 100},
    "DefensiveSpeedster": {'attack': 100, 'defense': 50, 'speed': 150},
    "DefensiveBruiser": {'attack': 150, 'defense': 50, 'speed': 100},
    "DefensiveBulkySpeed": {'attack': 100, 'defense': 100, 'speed': 50},
    "DefensiveBulkyTank": {'attack': 100, 'defense': 150, 'speed': 50},
    "DefensiveBulkySpeedster": {'attack': 150, 'defense': 50, 'speed': 150},
    "DefensiveBulkyBruiser": {'attack': 100, 'defense': 150, 'speed': 50},
}

# --- Attack Sets (Themes/Prompts) - EXPANDED ---
ALL_ATTACK_SETS = {
    "Standard": "A balanced, standard set of attacks.",
    "Burner": "Shoot fire guns",
    "Slugger": "slow and steady wins the race",
    "WashingMachine": "wash, rinse, repeat",
    "PowerOfTheTurtle": "turtling is fun",
    "TheBreaker": "break the other player",
    "TheBait": "lure the other player into a trap",
    # --- Adding more sets ---
    "Frostbite": "Freeze your foes with ice attacks.",
    "ToxicStall": "Poison and defensive tactics.",
    "WindSweeper": "Fast wind-based attacks, disrupts opponent.",
    "Earthquake": "Heavy ground attacks, good against defense.",
    "Thunderstorm": "Electric attacks, chance for paralysis.",
    "VampireDrain": "Life-stealing attacks.",
    "MindGames": "Psychic attacks, manipulate opponent stats.",
    "NinjaArts": "Quick strikes, evasion, smoke bombs.",
    "SamuraiCode": "Precise, powerful single strikes, honorable.",
    "PirateBooty": "Unpredictable attacks, treasure-themed, debuffs.",
    "RobotUprising": "Mechanical attacks, lasers, electric shocks.",
    "NatureWrath": "Plant and animal attacks, healing, entanglement.",
    "CosmicForce": "Space-themed attacks, gravity, meteors.",
    "ShadowDance": "Dark attacks, stealth, illusions.",
    "HolyLight": "Light-based attacks, healing, buffs.",
    "DragonBreath": "Powerful elemental breaths, draconic theme.",
    "UndeadPlague": "Summon undead, curses, life drain.",
    "BardSong": "Musical attacks, buffs, debuffs, charming.",
    "ChefSpecial": "Food-themed attacks, weird status effects.",
    "GamblerLuck": "High-risk, high-reward attacks, based on chance.",
    "TimeWarp": "Manipulate speed, slow/haste effects.",
    "JuggernautCharge": "Build momentum for powerful charges.",
    "GuardianAngel": "Protective abilities, shields, ally buffs.",
    "BerserkerRage": "Increase attack at the cost of defense.",
    "AlchemistConcoctions": "Throw potions, acid, explosions.",
    "SummonerPact": "Summon temporary allies or elemental spirits.",
    "GladiatorNet": "Trapping and restraining attacks.",
    "MonkFists": "Unarmed attacks, focus on combos and speed.",
    "GolemConstruct": "Slow, powerful, rock-based attacks.",
    "SpiritChanneler": "Commune with spirits, unpredictable effects.",
    "MirageMaster": "Create illusions, confuse the enemy.",
    "PlagueDoctor": "Debuffs, damage over time, minor healing.",
    "ArtificerGadgets": "Use traps, turrets, mechanical devices.",
    "OceanCurrents": "Water attacks, control enemy position.",
    "VolcanoEruption": "Fire and earth combo attacks, area damage.",
    "ArcticBlast": "Ice attacks, slow effects, brittle defense.",
    "DesertMirage": "Sand attacks, blindness, heat exhaustion effects.",
    "JungleVine": "Entangling attacks, poison darts, camouflage.",
    "MountainPeak": "Rock slides, altitude sickness, strong defense.",
    "SwampGas": "Poison clouds, confusion, sticky mud.",
    "CelestialBlessing": "Healing, stat boosts, divine intervention.",
    "InfernalPact": "Dark magic, sacrifices for power, fire.",
    "AbyssalDepths": "Water pressure, darkness, scary monsters.",
    "AetherFlow": "Manipulate raw energy, unpredictable results.",
    "ClockworkPrecision": "Attacks based on timing and order.",
    "DreamWeaver": "Put enemies to sleep, attack in dreams.",
    "MutationChaos": "Randomly change own stats or enemy stats.",
    "SoundWave": "Sonic attacks, disorientation, defense lowering.",
    "GravityWell": "Increase enemy momentum cost, slow speed.",
    # --- Add more to reach 50+ ---
    "QuicksandTrap": "Immobilize and deal damage over time.",
    "MirrorImage": "Create copies to confuse the target.",
    "BloodMagic": "Use own HP to power stronger attacks.",
    "RuneMaster": "Place magical runes with various effects.",
    "ForgeHeart": "Heat-based attacks, increase own attack.",
    "CrystalShard": "Sharp piercing attacks, defensive spikes."
}

# --- Logger Setup ---
# Keep logger setup as before, but note child processes might not log here easily
logger = logging.getLogger('simulate_battle_sets')
# ... (rest of logger setup) ...
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler = logging.FileHandler(LOG_FILE, mode='w')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)


# =========================================================
# --- Worker Function for Parallel Simulation ---
# =========================================================
# Define this function *outside* the Command class for easier pickling
def run_single_simulation(matchup_pair, static_data):
    """
    Runs a single battle simulation for a given matchup pair.
    Designed to be called by multiprocessing.Pool.

    Args:
        matchup_pair: A tuple (((set1_name, arch1_name), (set2_name, arch2_name))).
        static_data: A dictionary containing necessary static info:
            'archetypes': ARCHETYPES dict
            'attack_set_user_names': Dict mapping set_name to username
            'generated_attack_set_ids': Dict mapping set_name to list of attack IDs

    Returns:
        A dictionary containing results for this matchup, e.g.:
        {
            'profile1_key': 'Set1(Arch1)',
            'profile2_key': 'Set2(Arch2)',
            'winner_profile': 'Set1(Arch1)' or None,
            'damage_dealt_p1': 150,
            'damage_received_p1': 100,
            'damage_dealt_p2': 100,
            'damage_received_p2': 150,
            'error': None or "Error message"
        }
    """
    # Ensure Django is initialized in the child process (might be needed)
    # Needs to be configured based on your project structure if not automatic
    # try:
    #     django.setup()
    # except Exception as e:
    #     print(f"[Worker Setup ERROR] Failed to setup Django: {e}")
    #     # Decide how to handle this, maybe return error state

    (set1_name, arch1_name), (set2_name, arch2_name) = matchup_pair
    archetypes = static_data['archetypes']
    attack_set_user_names = static_data['attack_set_user_names']
    generated_attack_set_ids = static_data['generated_attack_set_ids']

    profile1_key = f"{set1_name}({arch1_name})"
    profile2_key = f"{set2_name}({arch2_name})"
    result = {
        'profile1_key': profile1_key,
        'profile2_key': profile2_key,
        'winner_profile': None,
        'damage_dealt_p1': 0, 'damage_received_p1': 0,
        'damage_dealt_p2': 0, 'damage_received_p2': 0,
        'error': None
    }

    battle = None # Initialize battle variable

    try:
        # Fetch users and attacks within the worker process
        user1_name = attack_set_user_names[set1_name]
        user2_name = attack_set_user_names[set2_name]
        user1 = User.objects.get(username=user1_name)
        user2 = User.objects.get(username=user2_name)

        attacks1_ids = generated_attack_set_ids[set1_name]
        attacks2_ids = generated_attack_set_ids[set2_name]
        # Fetch Attack objects - consider optimizing if this is slow
        attacks1 = list(Attack.objects.filter(id__in=attacks1_ids))
        attacks2 = list(Attack.objects.filter(id__in=attacks2_ids))
        if len(attacks1) != len(attacks1_ids) or len(attacks2) != len(attacks2_ids):
             # Log potential issue finding all attacks
             print(f"[Worker WARNING] Mismatch fetching attacks for {profile1_key} vs {profile2_key}")

        stats1 = archetypes[arch1_name]
        stats2 = archetypes[arch2_name]

        # Apply Archetype Stats Temporarily (modify user objects fetched in this process)
        user1.hp = 100; user1.attack = stats1['attack']; user1.defense = stats1['defense']; user1.speed = stats1['speed']
        user2.hp = 100; user2.attack = stats2['attack']; user2.defense = stats2['defense']; user2.speed = stats2['speed']
        # Note: No user.save() needed here as these are temporary for the sim

        # Set Selected Attacks for this battle
        # Simulate the M2M relationship locally if needed, or use IDs directly in logic
        # For simplicity, we'll assume apply_attack can work with the Battle object and user IDs/attack IDs
        # Re-check apply_attack signature and adapt if necessary.
        # Let's assume we still need to *conceptually* set them for the logic inside the loop below
        user1_selected_attacks = attacks1
        user2_selected_attacks = attacks2

        # --- Create Battle ---
        # Create a *new* battle instance for this simulation
        battle = Battle.objects.create(player1=user1, player2=user2, status='pending')
        battle.status = 'active'
        battle.initialize_battle_state() # Sets HP, momentum=10, turn etc.
        # print(f"  [Worker {os.getpid()}] Battle {battle.id} created for {profile1_key} vs {profile2_key}. Turn {battle.turn_number}. Starting: {battle.whose_turn}") # Optional worker log

        turn_count = 0
        battle_damage_dealt = {'player1': 0, 'player2': 0}
        battle_damage_received = {'player1': 0, 'player2': 0}

        # --- Simulation Loop (Copied & Adapted) ---
        while battle.status == 'active' and turn_count < MAX_BATTLE_TURNS:
            turn_count += 1
            current_player_role = battle.whose_turn

            if current_player_role == 'player1':
                current_player = user1
                selected_attacks_list = user1_selected_attacks
            else: # player2's turn
                current_player = user2
                selected_attacks_list = user2_selected_attacks

            if not selected_attacks_list:
                # print(f"  [Worker {os.getpid()}] {current_player_role} ({current_player.username}) has NO selected attacks! Skipping turn.")
                # This shouldn't happen if assignment worked, but handle defensively
                battle.save() # Save potential state changes before skipping?
                continue

            chosen_attack = random.choice(selected_attacks_list)
            # print(f"  [Worker {os.getpid()}] Turn {turn_count}: {current_player_role} uses {chosen_attack.name}")

            hp_before_p1 = battle.current_hp_player1
            hp_before_p2 = battle.current_hp_player2

            try:
                # Apply attack modifies battle object IN PLACE and saves it
                apply_attack(battle, current_player, chosen_attack)
                # No refresh needed here, work with the modified battle object

                hp_after_p1 = battle.current_hp_player1
                hp_after_p2 = battle.current_hp_player2
                hp_change_p1 = (hp_after_p1 or 0) - (hp_before_p1 or 0)
                hp_change_p2 = (hp_after_p2 or 0) - (hp_before_p2 or 0)

                if current_player_role == 'player1': # Player 1 attacked
                    if hp_change_p2 < 0: battle_damage_dealt['player1'] += -hp_change_p2
                    if hp_change_p1 < 0: battle_damage_received['player1'] += -hp_change_p1
                else: # Player 2 attacked
                    if hp_change_p1 < 0: battle_damage_dealt['player2'] += -hp_change_p1
                    if hp_change_p2 < 0: battle_damage_received['player2'] += -hp_change_p2

            except Exception as attack_err:
                 print(f"  [Worker {os.getpid()} ERROR] applying attack {chosen_attack.name} in battle {battle.id}: {attack_err}")
                 # Decide how to proceed - maybe stop this battle sim?
                 battle.status = 'finished' # Mark as finished on error?
                 battle.winner = None
                 # battle.save() # Don't save on attack error inside loop
                 result['error'] = f"AttackError: {attack_err}"
                 break # Exit the while loop for this battle

        # --- Battle End --- 
        # Save the final battle state *once* after the loop finishes
        try:
            if battle: # Ensure battle object exists
                 # print(f"[Worker {os.getpid()}] Saving final state for Battle {battle.id} (Status: {battle.status})")
                 battle.save() 
        except Exception as final_save_err:
            print(f"[Worker {os.getpid()} ERROR] Failed to save final state for Battle {battle.id}: {final_save_err}")
            if not result['error']: # Avoid overwriting existing error
                result['error'] = f"FinalSaveError: {final_save_err}"

        if turn_count >= MAX_BATTLE_TURNS and battle.status == 'active':
            # print(f"  [Worker {os.getpid()}] Battle {battle.id} reached max turns ({MAX_BATTLE_TURNS}).")
            # Status might have been set already, but ensure winner is None if timed out
            if battle: # Check again in case creation failed
                battle.status = 'finished'; battle.winner = None; 
                # Save again if timeout occurred after loop but before initial save
                try: 
                    battle.save()
                except Exception: pass # Ignore error if initial save failed

        if battle and battle.winner: # Check battle exists before accessing winner
            result['winner_profile'] = profile1_key if battle.winner_id == user1.id else profile2_key

        result['damage_dealt_p1'] = battle_damage_dealt['player1']
        result['damage_received_p1'] = battle_damage_received['player1']
        result['damage_dealt_p2'] = battle_damage_dealt['player2']
        result['damage_received_p2'] = battle_damage_received['player2']

    except Exception as sim_err:
        print(f"[Worker {os.getpid()} FATAL ERROR] Simulating {profile1_key} vs {profile2_key}: {sim_err}")
        result['error'] = f"SimulationError: {sim_err}"
    # finally:
        # Optional: Explicitly delete the battle object created by this worker?
        # if battle:
        #    battle.delete() # Keep DB clean if desired

    return result

# =========================================================
# --- Django Management Command ---
# =========================================================
class Command(BaseCommand):
    help = (
        'Generates attack sets (optionally), assigns them to users, '
        'and simulates battles between (User+Set) vs (User+Set) with different archetypes applied, '
        'using multiprocessing for simulation.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--skipgeneration',
            action='store_true',
            help='Skip the API attack generation step and use existing user attacks.',
        )

    def handle(self, *args, **options):
        skip_generation = options['skipgeneration']
        logger.info('--- Starting Full Battle Combination Simulation (Parallel) ---')
        if skip_generation:
            logger.info("*** --skipgeneration flag detected: Skipping user creation and API attack generation. ***")

        # Determine which sets to use
        if skip_generation:
            # Use all sets defined if skipping generation
            active_attack_sets = ALL_ATTACK_SETS
            logger.info(f"Simulating using ALL {len(active_attack_sets)} defined attack sets.")
        else:
            # Randomly select a subset if generating
            if len(ALL_ATTACK_SETS) <= NUM_SETS_TO_SELECT:
                selected_set_names = list(ALL_ATTACK_SETS.keys())
            else:
                selected_set_names = random.sample(list(ALL_ATTACK_SETS.keys()), NUM_SETS_TO_SELECT)
            active_attack_sets = {name: ALL_ATTACK_SETS[name] for name in selected_set_names}
            logger.info(f"Randomly selected {len(active_attack_sets)} attack sets for generation: {', '.join(active_attack_sets.keys())}")

        # --- 1. Define API Endpoint ---
        generate_url = f"{BASE_API_URL}{reverse('attack_generate')}"
        api_session = requests.Session() # Create session once, headers will be updated

        # --- 2 & 3: User Creation and Attack Generation (Conditional) ---
        attack_set_users = {} # {set_name: User object}
        attack_set_user_names = {} # {set_name: username}
        generated_attack_sets = {} # {set_name: [Attack objects]} - Populated only if generating
        generated_attack_set_ids = {} # {set_name: [attack IDs]} - Used by workers

        if not skip_generation:
            logger.info("Creating/Updating Users for selected Attack Sets...")
            default_stats = ARCHETYPES["Balanced"]
            for set_name in active_attack_sets.keys(): # Only loop through selected sets
                username = f"{set_name}_Sim"
                try:
                    user, created = User.objects.update_or_create(
                        username=username,
                        defaults={'email': f'{username}@example.com'.lower(), 'hp': 100, 'attack': default_stats['attack'], 'defense': default_stats['defense'], 'speed': default_stats['speed']}
                    )
                    if created: user.set_password('password'); user.save()
                    else: user.hp = 100; user.attack = default_stats['attack']; user.defense = default_stats['defense']; user.speed = default_stats['speed']; user.save()
                    logger.info(f"  {'Created' if created else 'Updated'} user: {username}")
                    attack_set_users[set_name] = user
                    attack_set_user_names[set_name] = username # Store username
                except Exception as e:
                    logger.error(f"Failed to create/update user {username}: {e}")
                    return

            logger.info("\nGenerating Attack Sets via API for selected sets...")
            generation_failures = []
            for set_name, prompt_text in active_attack_sets.items(): # Only loop through selected sets
                username_to_auth = attack_set_user_names.get(set_name)
                if not username_to_auth:
                    # This shouldn't happen if user creation succeeded, but check defensively
                    logger.error(f"    Could not find username for set '{set_name}'. Skipping generation.")
                    generation_failures.append(set_name)
                    continue

                logger.info(f"  Generating set '{set_name}' for user '{username_to_auth}'...")
                try:
                    # Authenticate as the specific user for this set
                    access_token = self.authenticate_user(username_to_auth, 'password') 
                    api_session.headers.update({'Authorization': f'Bearer {access_token}'})
                    
                    # Prepare API call - Use set_name (theme key) as concept
                    payload = {"concept": set_name} # Changed payload

                    # Make the API call
                    response = api_session.post(generate_url, json=payload, timeout=180)
                    response.raise_for_status()
                    result = response.json()
                    created_attack_data = result.get('attacks', [])
                    if not created_attack_data: raise ValueError("API success but no 'attacks' data returned.")
                    attack_ids = [a['id'] for a in created_attack_data if a and 'id' in a]
                    if not attack_ids: raise ValueError("API success but no attack IDs found in response.")
                    time.sleep(0.5)
                    fetched_attacks = list(Attack.objects.filter(id__in=attack_ids))
                    if len(fetched_attacks) != len(attack_ids): logger.warning(f"    Warning: Found {len(fetched_attacks)}/{len(attack_ids)} attacks in DB for {set_name}.")
                    if not fetched_attacks: raise ValueError("Could not retrieve any generated attacks from database.")

                    generated_attack_sets[set_name] = fetched_attacks
                    generated_attack_set_ids[set_name] = [a.id for a in fetched_attacks] # Store IDs
                    logger.info(f"    Successfully generated {len(fetched_attacks)} attacks for set '{set_name}'.")

                except CommandError as auth_err: 
                    logger.error(f"    Authentication failed for user '{username_to_auth}': {auth_err}")
                    generation_failures.append(set_name)
                except Exception as e:
                    logger.error(f"    Failed generating set '{set_name}' for user '{username_to_auth}': {e}", exc_info=True)
                    generation_failures.append(set_name)

                time.sleep(5) # Be nice to the API

            api_session.headers.pop('Authorization', None)

            if not generated_attack_sets:
                logger.error("Attack generation failed for all selected sets. Cannot proceed.")
                return
            if generation_failures:
                 logger.warning(f"\nNote: Attack generation failed for sets: {', '.join(generation_failures)}")

            # --- 3.5 Assign generated attacks --- 
            logger.info("\nAssigning generated attack sets to their respective users...")
            assignment_failures = False
            for set_name, user in attack_set_users.items():
                if set_name in generated_attack_sets:
                    attacks_to_assign = generated_attack_sets[set_name]
                    try:
                        user.attacks.clear(); user.attacks.add(*attacks_to_assign)
                        logger.info(f"  Assigned {len(attacks_to_assign)} attacks ({set_name}) to {user.username}")
                    except Exception as e:
                        logger.error(f"  Failed to assign {set_name} attacks to {user.username}: {e}"); assignment_failures = True
                else:
                    logger.warning(f"  Skipping assignment for {user.username}: Set '{set_name}' not generated or failed."); assignment_failures = True
            if assignment_failures:
                logger.error("Attack set assignment failed. Stopping."); 
                return

        else: # --- Handle --skipgeneration --- 
            logger.info("Fetching existing users and attack IDs for ALL defined sets...")
            fetch_failures = []
            for set_name in active_attack_sets.keys(): # Loop through ALL sets
                username = f"{set_name}_Sim"
                try:
                    user = User.objects.get(username=username)
                    # Fetch current attack IDs assigned to this user
                    # We need the IDs for the worker, not the full objects here
                    assigned_attack_ids = list(user.attacks.values_list('id', flat=True))
                    if not assigned_attack_ids:
                         logger.warning(f"  User {username} found, but has NO attacks assigned! Skipping participation for this set.")
                         fetch_failures.append(set_name)
                         continue
                         
                    attack_set_users[set_name] = user # Store user object for reference if needed
                    attack_set_user_names[set_name] = username
                    generated_attack_set_ids[set_name] = assigned_attack_ids # Use existing IDs
                    logger.info(f"  Found user {username} with {len(assigned_attack_ids)} attack IDs.")
                except User.DoesNotExist:
                    logger.error(f"  User {username} NOT found! Cannot simulate with this set. Ensure users exist when using --skipgeneration.")
                    fetch_failures.append(set_name)
                except Exception as e:
                    logger.error(f"  Error fetching data for user {username}: {e}")
                    fetch_failures.append(set_name)
            
            if fetch_failures:
                 logger.warning(f"\nNote: Failed to fetch data or attacks for sets: {', '.join(fetch_failures)}")
            # Remove sets with fetch failures from the list of sets to simulate
            active_set_names_for_sim = [name for name in active_attack_sets.keys() if name not in fetch_failures]
            if not active_set_names_for_sim:
                logger.error("Could not retrieve valid user/attack data for ANY sets when skipping generation. Stopping.")
                return
            active_attack_sets = {name: ALL_ATTACK_SETS[name] for name in active_set_names_for_sim}


        # --- 4. Prepare for Parallel Simulation --- 
        logger.info("\n--- Preparing for Parallel Simulation --- ")
        # Use the keys from the *final* active_attack_sets (either generated or fetched)
        valid_set_names = list(active_attack_sets.keys())
        if not valid_set_names:
             logger.error("No valid attack sets available for simulation. Stopping.")
             return
             
        valid_archetype_names = list(ARCHETYPES.keys())
        participant_profiles = list(itertools.product(valid_set_names, valid_archetype_names))
        unique_simulation_pairs = [p for p in itertools.combinations_with_replacement(participant_profiles, 2) if p[0] != p[1]]
        total_sims = len(unique_simulation_pairs)
        logger.info(f"Will simulate {total_sims} unique matchups using {NUM_PROCESSES} processes.")

        # Package static data for workers
        static_data_for_workers = {
            'archetypes': ARCHETYPES,
            'attack_set_user_names': attack_set_user_names,
            'generated_attack_set_ids': generated_attack_set_ids
        }

        # --- Close DB connection in parent before forking ---
        logger.info("Closing database connections in main process before starting pool...")
        connections.close_all()

        # --- 5. Run Simulations in Parallel ---
        print(f"Starting {total_sims} simulations using {NUM_PROCESSES} processes...", file=sys.stdout)
        pool_results = []
        sim_count = 0
        start_time = time.time()
        try:
            with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
                # Use partial to pass static data to the worker function
                worker_partial = partial(run_single_simulation, static_data=static_data_for_workers)
                # Use imap_unordered to get results as they finish for progress updates
                # Note: pool_results will be collected unordered now
                for result in pool.imap_unordered(worker_partial, unique_simulation_pairs):
                    pool_results.append(result) # Collect results
                    sim_count += 1
                    # Print progress update directly to stdout, overwriting previous line
                    print(f"  Progress: {sim_count}/{total_sims} simulations completed...", end='\r', file=sys.stdout)

        except Exception as pool_err:
             logger.error(f"FATAL ERROR during multiprocessing pool execution: {pool_err}", exc_info=True)
             print("\nSimulation failed due to a pool error. Check log file.", file=sys.stderr) # Ensure error message is visible
             return # Stop if pool fails critically
        finally:
             # Pool context manager handles close/join
             pass

        print(f"\n{total_sims} simulations finished.", file=sys.stdout) # Print final confirmation to stdout
        end_time = time.time()
        logger.info(f"\n--- Parallel Simulation Phase Completed in {end_time - start_time:.2f} seconds ---")
        if not pool_results or len(pool_results) != total_sims:
             logger.warning(f"Pool execution finished, but received {len(pool_results)} results (expected {total_sims}). Check worker logs/errors.")

        # --- 6. Aggregate Results ---
        logger.info("Aggregating results...")
        # { "Set(Arch)": { "wins": 0, "total_dealt": 0, "total_received": 0, "errors": 0 } }
        simulation_summary = defaultdict(lambda: {"wins": 0, "total_dealt": 0, "total_received": 0, "errors": 0})
        total_sim_errors = 0

        for result in pool_results:
            if not result: continue # Skip if worker returned None or empty

            p1_key = result['profile1_key']
            p2_key = result['profile2_key']

            # Accumulate damage/received stats
            simulation_summary[p1_key]["total_dealt"] += result['damage_dealt_p1']
            simulation_summary[p1_key]["total_received"] += result['damage_received_p1']
            simulation_summary[p2_key]["total_dealt"] += result['damage_dealt_p2']
            simulation_summary[p2_key]["total_received"] += result['damage_received_p2']

            # Increment wins
            if result['winner_profile'] == p1_key:
                simulation_summary[p1_key]["wins"] += 1
            elif result['winner_profile'] == p2_key:
                simulation_summary[p2_key]["wins"] += 1

            # Count errors
            if result['error']:
                total_sim_errors +=1
                simulation_summary[p1_key]["errors"] += 1
                simulation_summary[p2_key]["errors"] += 1
                # Log specific error here if needed, though worker might print it too
                # logger.warning(f"Error recorded for {p1_key} vs {p2_key}: {result['error']}")

        logger.info(f"Aggregation complete. Total simulation errors recorded: {total_sim_errors}")

        # --- 7. Log Simulation Summary ---
        logger.info("\n\n--- Simulation Summary ---")
        sorted_summary = sorted(simulation_summary.items(), key=lambda item: item[1]['wins'], reverse=True)

        header_profile = 'Profile (Set - Archetype)'
        header_wins = 'Wins'; header_errors = 'Errors'; header_dmg_dealt = 'Dmg Dealt'; header_dmg_recvd = "Dmg Recv'd"

        logger.info(f"{header_profile:<40} | {header_wins:>5} | {header_errors:>6} | {header_dmg_dealt:>10} | {header_dmg_recvd:>10}")
        logger.info("-" * 85)
        for profile_key, stats in sorted_summary:
             wins = stats['wins']; errors = stats['errors']; dealt = stats['total_dealt']; received = stats['total_received']
             log_line = "{:<40} | {:>5} | {:>6} | {:>10} | {:>10}".format(profile_key, wins, errors, dealt, received)
             logger.info(log_line)
        logger.info("="*85)

        # --- 8. Log Generated Attack Set Details ---
        logger.info("\n\n--- Generated Attack Sets Details ---")
        for set_name, attacks in generated_attack_sets.items():
            logger.info("\n----------------------------------------")
            logger.info(f"Attack Set: {set_name}")
            logger.info("----------------------------------------")
            if not attacks:
                logger.info("  (No attacks generated or retrieved for this set)")
                continue
            
            for attack in attacks:
                script_details = []
                # Prefetch related scripts for efficiency (can be done earlier if needed)
                attack_scripts = list(attack.scripts.all()) 
                if attack_scripts:
                    for script in attack_scripts:
                         trigger_info = []
                         if script.trigger_on_attack: trigger_info.append("On Use")
                         if script.trigger_before_attacker_turn: trigger_info.append("Before Attacker")
                         if script.trigger_after_attacker_turn: trigger_info.append("After Attacker")
                         if script.trigger_before_target_turn: trigger_info.append("Before Target")
                         if script.trigger_after_target_turn: trigger_info.append("After Target")
                         trigger_str = ", ".join(trigger_info) if trigger_info else "No Trigger?"
                         script_details.append(f"  - Script: {script.name} [{trigger_str}]")
                else:
                    script_details.append("  (No associated Lua scripts)")
                
                logger.info(f"- {attack.emoji or ''} {attack.name}:")
                logger.info(f"    Desc: {attack.description}")
                logger.info(f"    Cost: {attack.momentum_cost}") # Assuming cost is a direct field
                for detail_line in script_details:
                    logger.info(detail_line)
            
        logger.info("\n" + "="*85)
        logger.info(f"Full simulation log saved to: {LOG_FILE}")

    def authenticate_user(self, username, password):
        """Logs in a user via API and returns the access token."""
        login_url = f"{BASE_API_URL}/api/users/login/"
        try:
            response = requests.post(login_url, data={'username': username, 'password': password}, timeout=30)
            response.raise_for_status()
            tokens = response.json(); access_token = tokens.get('access')
            if not access_token: raise CommandError("Auth succeeded, but no access token received.")
            return access_token
        except requests.exceptions.RequestException as e:
            err_msg = f"Auth failed for '{username}': {e}. Response: {e.response.text if e.response else 'No Response'}"
            raise CommandError(err_msg)
        except Exception as e: raise CommandError(f"Unexpected error during auth: {e}")
