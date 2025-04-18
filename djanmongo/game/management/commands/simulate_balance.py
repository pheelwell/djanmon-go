# Need imports at the top
import random
import math
import statistics # For calculating averages
from django.core.management.base import BaseCommand
from game.logic.calculations import calculate_damage, calculate_momentum_gain_range, get_modified_stat

# Lightweight simulation objects (add methods for stage setting)
class SimPlayer:
    def __init__(self, name, attack, defense, speed):
        self.name = name
        self.attack = int(attack)
        self.defense = int(defense)
        self.speed = int(speed)
        self.reset() # Initialize trackers

    def set_stage(self, stat, level):
        """Sets a specific stat stage."""
        if stat in self.stat_stages:
            # Clamp stage level just in case
            level = max(-6, min(6, int(level)))
            self.stat_stages[stat] = level
        else:
            print(f"Warning: Invalid stat '{stat}' for set_stage")

    def reset(self, base_stages=None):
        """Resets trackers and optionally sets initial stages."""
        if base_stages:
             # Ensure base_stages is a valid dict
             if isinstance(base_stages, dict) and all(k in ['attack', 'defense', 'speed'] for k in base_stages):
                 self.stat_stages = base_stages.copy()
             else:
                  print("Warning: Invalid base_stages provided to reset. Using neutral.")
                  self.stat_stages = {'attack': 0, 'defense': 0, 'speed': 0}
        else:
             self.stat_stages = {'attack': 0, 'defense': 0, 'speed': 0} # Start neutral

        self.current_momentum = 0
        self.total_damage_dealt = 0
        self.total_damage_received = 0
        self.total_hits = 0

    def get_results(self):
        """Returns a dictionary of the player's final stats."""
        return {
            'hits': self.total_hits,
            'dealt': self.total_damage_dealt,
            'received': self.total_damage_received,
            # Could add momentum if needed, but less critical for summary
        }

    def __str__(self):
        return f"{self.name} (A:{self.attack}/D:{self.defense}/S:{self.speed})"

class SimAttack:
    # ... (remains the same)
    def __init__(self, name="Punch", power=10, momentum_cost=20):
        self.name = name
        self.power = int(power)
        self.momentum_cost = int(momentum_cost)

# Helper function to run one simulation
def run_single_simulation(player_a: SimPlayer, player_b: SimPlayer, attack: SimAttack, total_turns: int):
    """Runs a single matchup simulation and returns results for both players."""
    # Ensure players are reset before sim (caller responsibility is better)
    # player_a.reset() # Assuming reset is handled before calling
    # player_b.reset()

    turns_elapsed = 0
    while turns_elapsed < total_turns:
        attacker = None
        defender = None

        if player_a.current_momentum <= player_b.current_momentum:
            attacker = player_a
            defender = player_b
        else:
            attacker = player_b
            defender = player_a

        attacker.total_hits += 1
        damage_dealt = calculate_damage(
            attacker=attacker,
            target=defender,
            attack=attack,
            attacker_stages=attacker.stat_stages,
            target_stages=defender.stat_stages
        )
        attacker.total_damage_dealt += damage_dealt
        defender.total_damage_received += damage_dealt

        min_gain, max_gain = calculate_momentum_gain_range(attack, attacker, attacker.stat_stages)
        actual_gain = random.randint(min_gain, max_gain) if max_gain >= min_gain else 0
        attacker.current_momentum += actual_gain

        turns_elapsed += 1

    return {
        player_a.name: player_a.get_results(),
        player_b.name: player_b.get_results()
    }


class Command(BaseCommand):
    help = 'Simulates battle rounds to check damage/turn balance, including stat stage effects.'

    # ... (add_arguments remains the same)
    def add_arguments(self, parser):
        parser.add_argument(
            '--rounds', type=int, default=10000, # Increased default for better averages
            help='Number of total turns/attacks in each simulation matchup.'
        )
        parser.add_argument(
            '--attack_power', type=int, default=15,
            help='Base power of the attack used in the simulation.'
        )
        parser.add_argument(
            '--attack_momentum', type=int, default=30,
            help='Base momentum cost/gain of the attack used in the simulation.'
        )

    def handle(self, *args, **options):
        num_turns = options['rounds']
        attack_power = options['attack_power']
        attack_momentum = options['attack_momentum']

        self.stdout.write(self.style.SUCCESS(
            f'Starting Battle Balance Simulation ({num_turns} turns per matchup)'
        ))
        self.stdout.write(f"Using Test Attack: Power={attack_power}, Momentum Cost={attack_momentum}")

        # Define player archetypes (total 300 points)
        players = [
            SimPlayer("Balanced", 100, 100, 100),
            SimPlayer("GlassCannon", 150, 50, 100),
            SimPlayer("Tank", 50, 150, 100),
            SimPlayer("Speedster", 100, 50, 150),
            SimPlayer("Bruiser", 150, 100, 50),
            SimPlayer("BulkySpeed", 50, 100, 150),
            SimPlayer("HyperOffense", 200, 50, 50),
            SimPlayer("HyperDefense", 50, 200, 50),
            SimPlayer("HyperSpeed", 50, 50, 200),
        ]
        player_map = {p.name: p for p in players} # For easy lookup

        test_attack = SimAttack(power=attack_power, momentum_cost=attack_momentum)

        # --- Phase 1: Run Baseline Neutral vs Neutral Simulations ---
        self.stdout.write(self.style.SUCCESS("\n--- Running Baseline Simulations (Neutral Stages) ---"))
        baseline_results = {} # Stores detailed results {matchup_key: {p1_name: results, p2_name: results}}

        for i in range(len(players)):
            for j in range(len(players)): # Use i to len(players) to include self-play
                player_a = players[i]
                player_b = players[j]

                # Reset players to neutral state
                player_a.reset()
                player_b.reset()

                matchup_key = f"{player_a.name}_vs_{player_b.name}"
                # self.stdout.write(f"--- Simulating Baseline: {matchup_key} ---") # Can be verbose

                # Run the simulation
                sim_result = run_single_simulation(player_a, player_b, test_attack, num_turns)
                baseline_results[matchup_key] = sim_result

                # Optional: Print per-matchup baseline results if needed
                # self.stdout.write(f"  {player_a.name}: Hits={sim_result[player_a.name]['hits']}, Dealt={sim_result[player_a.name]['dealt']}, Received={sim_result[player_a.name]['received']}")
                # self.stdout.write(f"  {player_b.name}: Hits={sim_result[player_b.name]['hits']}, Dealt={sim_result[player_b.name]['dealt']}, Received={sim_result[player_b.name]['received']}")

        # --- Phase 1.5: Calculate and Print Overall Archetype Summary (from Baseline) ---
        self.stdout.write(self.style.SUCCESS("\n--- Overall Archetype Summary (Baseline) ---"))
        overall_baseline_stats = {p.name: {'total_dealt': 0, 'total_received': 0, 'total_hits': 0, 'matchups': 0} for p in players}

        for matchup_key, matchup_results in baseline_results.items():
            p1_name, p2_name = matchup_key.split('_vs_')

            if p1_name in overall_baseline_stats:
                 p1_res = matchup_results[p1_name]
                 overall_baseline_stats[p1_name]['total_dealt'] += p1_res['dealt']
                 overall_baseline_stats[p1_name]['total_received'] += p1_res['received']
                 overall_baseline_stats[p1_name]['total_hits'] += p1_res['hits']
                 overall_baseline_stats[p1_name]['matchups'] += 1

            # Add Player B's stats ONLY if it's not self-play (handled Player A already)
            if p2_name in overall_baseline_stats and p1_name != p2_name:
                 p2_res = matchup_results[p2_name]
                 overall_baseline_stats[p2_name]['total_dealt'] += p2_res['dealt']
                 overall_baseline_stats[p2_name]['total_received'] += p2_res['received']
                 overall_baseline_stats[p2_name]['total_hits'] += p2_res['hits']
                 overall_baseline_stats[p2_name]['matchups'] += 1

        sorted_baseline_stats = sorted(overall_baseline_stats.items(), key=lambda item: item[1]['total_dealt'], reverse=True)

        for name, stats in sorted_baseline_stats:
            player_obj = player_map[name]
            stats_str = f"(A:{player_obj.attack}/D:{player_obj.defense}/S:{player_obj.speed})"
            hits = stats['total_hits']
            dealt = stats['total_dealt']
            received = stats['total_received']
            matchups = stats['matchups']
            self.stdout.write(
                f"  {name:<15} {stats_str:<20} | Hits: {hits:<6} | Total Dealt: {dealt:<8} | Total Received: {received:<8} (across {matchups} matchups)"
            )

        # --- Phase 2: Simulate Stage Effects ---
        self.stdout.write(self.style.SUCCESS("\n--- Running Stat Stage Simulations ---"))
        # {stat: {stage: {metric: [list_of_perc_changes]}}}
        stage_impact_data = {
            stat: {
                stage: {'hits': [], 'dealt': [], 'received': []}
                for stage in range(-6, 7) if stage != 0
            } for stat in ['attack', 'defense', 'speed']
        }

        stats_to_modify = ['attack', 'defense', 'speed']
        stages_to_test = list(range(-6, 0)) + list(range(1, 7))

        total_stage_sims = len(players) * len(players) * len(stats_to_modify) * len(stages_to_test)
        self.stdout.write(f"Performing approx {total_stage_sims} stage simulations...")
        sim_count = 0

        # Iterate through each player *receiving* the stage modification
        for modified_player in players:
            # Get this player's baseline results against all opponents (including self)
            modified_player_baseline_agg = {'hits': 0, 'dealt': 0, 'received': 0}
            for matchup_key, matchup_results in baseline_results.items():
                 p1_name, p2_name = matchup_key.split('_vs_')
                 res_to_add = None
                 if p1_name == modified_player.name:
                      res_to_add = matchup_results[p1_name]
                 elif p2_name == modified_player.name:
                      res_to_add = matchup_results[p2_name]
                 
                 if res_to_add:
                    modified_player_baseline_agg['hits'] += res_to_add['hits']
                    modified_player_baseline_agg['dealt'] += res_to_add['dealt']
                    modified_player_baseline_agg['received'] += res_to_add['received']


            # Now test applying stages to this player
            for stat in stats_to_modify:
                for stage in stages_to_test:
                    # Store results for this player with this specific stage vs all opponents
                    modified_stage_results_agg = {'hits': 0, 'dealt': 0, 'received': 0}
                    
                    # Simulate against all players (including self) as neutral opponents
                    for neutral_opponent in players:
                        sim_count += 1
                        if sim_count % 500 == 0: # Progress indicator
                            self.stdout.write(f"  ... completed {sim_count}/{total_stage_sims} stage simulations")

                        # --- CRITICAL: Create COPIES for the simulation --- 
                        # Create a fresh copy of the modified player for this specific sim run
                        current_modified_player = SimPlayer(modified_player.name, modified_player.attack, modified_player.defense, modified_player.speed)
                        current_modified_player.set_stage(stat, stage) # Apply stage to the copy
                        
                        # Create a fresh copy of the neutral opponent
                        current_neutral_opponent = SimPlayer(neutral_opponent.name, neutral_opponent.attack, neutral_opponent.defense, neutral_opponent.speed)
                        # Ensure opponent is neutral (reset does this)
                        current_neutral_opponent.reset() 
                        # --- End Copies --- 

                        # Run simulation with the copies
                        # Determine who is player_a/player_b based on names for consistency if needed, 
                        # but run_single_simulation handles internal logic.
                        sim_result = run_single_simulation(current_modified_player, current_neutral_opponent, test_attack, num_turns)

                        # Aggregate the modified player's results from this specific matchup
                        if current_modified_player.name in sim_result:
                             current_matchup_res = sim_result[current_modified_player.name]
                             modified_stage_results_agg['hits'] += current_matchup_res['hits']
                             modified_stage_results_agg['dealt'] += current_matchup_res['dealt']
                             modified_stage_results_agg['received'] += current_matchup_res['received']
                        else: 
                             print(f"ERROR: Could not find {current_modified_player.name} in results for {current_modified_player.name} vs {current_neutral_opponent.name}")
                             continue

                    # Now compare aggregated stage results vs aggregated baseline results for this player
                    baseline_agg = modified_player_baseline_agg # Use the pre-calculated baseline aggregate

                    # Calculate percentage changes
                    for metric in ['hits', 'dealt', 'received']:
                        base_val = baseline_agg[metric]
                        stage_val = modified_stage_results_agg[metric]
                        if base_val != 0:
                            perc_change = ((stage_val - base_val) / base_val) * 100.0
                        elif stage_val != 0:
                             perc_change = float('inf') # Or some large number/indicator
                        else:
                             perc_change = 0.0 # No change from zero

                        # Store the percentage change for this archetype/stat/stage/metric
                        stage_impact_data[stat][stage][metric].append(perc_change)


        self.stdout.write(f"  ... completed {sim_count}/{total_stage_sims} stage simulations")
        # --- Phase 3: Calculate and Print Stat Stage Impact Summary ---
        self.stdout.write(self.style.SUCCESS("\n--- Stat Stage Impact Summary (Average %) ---"))
        self.stdout.write(f"{'Stat':<8} {'Stage':<6} | {'Avg % Hits':<12} | {'Avg % Dealt':<12} | {'Avg % Received':<12}")
        self.stdout.write("-" * 70)

        for stat in stats_to_modify:
            # Sort stages for printing consistency
            sorted_stages = sorted(stages_to_test)
            for stage in sorted_stages:
                # Check if data exists for this stage (it should, but safety check)
                if stage in stage_impact_data[stat]:
                    hits_list = stage_impact_data[stat][stage]['hits']
                    dealt_list = stage_impact_data[stat][stage]['dealt']
                    received_list = stage_impact_data[stat][stage]['received']

                    avg_hits_change = statistics.mean(hits_list) if hits_list else 0.0
                    avg_dealt_change = statistics.mean(dealt_list) if dealt_list else 0.0
                    avg_received_change = statistics.mean(received_list) if received_list else 0.0

                    stage_str = f"+{stage}" if stage > 0 else str(stage)
                    self.stdout.write(
                        f"{stat:<8} {stage_str:<6} | {avg_hits_change:>+11.2f}% | {avg_dealt_change:>+11.2f}% | {avg_received_change:>+11.2f}%"
                    )
                else:
                     self.stdout.write(f"{stat:<8} {stage_str:<6} | No data collected.") 