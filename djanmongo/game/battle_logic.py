import random
import math
from .models import Battle, Attack
from users.models import User # Although we get users via battle object

# --- Constants (optional, but good practice) ---
MAX_STAT_STAGE = 6
MIN_STAT_STAGE = -6
DAMAGE_RANDOM_FACTOR_MIN = 0.85
DAMAGE_RANDOM_FACTOR_MAX = 1.00

# --- Helper Functions ---

def calculate_stat_modifier(stage):
    """Calculates the multiplier based on Pokemon stat stage rules."""
    if stage > 0:
        return (2 + stage) / 2.0
    elif stage < 0:
        return 2.0 / (2 + abs(stage))
    else:
        return 1.0

def get_modified_stat(base_stat, stage):
    """Applies the stat stage modifier to a base stat."""
    modifier = calculate_stat_modifier(stage)
    # Ensure minimum stat value (e.g., 1) if needed, Pokemon usually doesn't go below 1 implicitly
    return max(1, int(base_stat * modifier))

def clamp(value, min_val, max_val):
    """Clamps a value between min_val and max_val."""
    return max(min_val, min(value, max_val))

def calculate_damage(attacker: User, target: User, attack: Attack, attacker_stages: dict, target_stages: dict) -> int:
    """Calculates damage based on a simplified formula."""
    if attack.power <= 0:
        return 0 # Non-damaging move

    # Get modified stats based on current stages
    attacker_atk = get_modified_stat(attacker.attack, attacker_stages.get('attack', 0))
    target_def = get_modified_stat(target.defense, target_stages.get('defense', 0))

    # Simplified Damage Formula (inspired by Pokemon)
    # Level is omitted for simplicity for now (using 50 as placeholder)
    base_damage = (((2 * 50 / 5 + 2) * attack.power * attacker_atk / target_def) / 50) + 2
    
    # Apply random factor (e.g., 0.85 to 1.00)
    random_modifier = random.uniform(DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX)
    final_damage = int(base_damage * random_modifier)

    # Ensure minimum damage (e.g., 1) if attack has power > 0
    return max(1, final_damage)

# --- NEW: Momentum Gain Calculation Helper ---
def calculate_momentum_gain_range(attack: Attack, attacker: User, attacker_stages: dict) -> tuple[int, int]:
    """Calculates the min and max actual momentum gain based on speed scaling the base cost."""
    base_cost = attack.momentum_cost
    if base_cost <= 0:
        return (0, 0)

    # --- Calculate Speed Influence --- 
    baseline_speed = 5 
    attacker_current_stage = attacker_stages.get('speed', 0)
    modified_attacker_speed = get_modified_stat(attacker.speed, attacker_current_stage)
    
    # Scale the effective base cost based on speed relative to baseline
    # Widened clamp range for greater impact
    speed_multiplier = clamp(modified_attacker_speed / baseline_speed, 0.33, 3.0) 
    speed_adjusted_cost = base_cost * speed_multiplier

    # --- Apply Uncertainty to Adjusted Cost ---
    uncertainty_min_factor = 0.25 
    # Lower bound is uncertainty_min_factor * adjusted_cost (min 1)
    lower_bound = max(1, int(math.ceil(speed_adjusted_cost * uncertainty_min_factor))) if speed_adjusted_cost > 0 else 0
    # Upper bound is 1.0 * adjusted_cost (min 1)
    upper_bound = max(1, int(math.floor(speed_adjusted_cost))) if speed_adjusted_cost > 0 else 0

    # Ensure lower bound doesn't exceed upper bound
    if lower_bound > upper_bound:
            lower_bound = upper_bound 
            
    return (lower_bound, upper_bound)

# --- NEW Main Action Logic --- 

def apply_attack(battle: Battle, attacker: User, attack: Attack):
    """
    Applies a single attack from the attacker in the battle.
    Modifies the battle object directly.
    Returns a list of log entries and whether the battle ended.
    Handles turn switching based on momentum.
    """
    log_entries = []
    battle_ended = False

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
        attacker_stages = battle.stat_stages_player1
        target_stages = battle.stat_stages_player2
    else: # attacker_role == 'player2'
        target_player = battle.player1
        target_role = 'player1'
        attacker_stages = battle.stat_stages_player2
        target_stages = battle.stat_stages_player1

    attacker_hp_attr = f'current_hp_{attacker_role}'
    target_hp_attr = f'current_hp_{target_role}'
    current_attacker_hp = getattr(battle, attacker_hp_attr)
    current_target_hp = getattr(battle, target_hp_attr)

    # Updated helper to add structured log entries
    def add_log(text, source="system", effect_type="info", effect_details=None):
        entry = {"source": source, "text": text, "effect_type": effect_type}
        if effect_details:
            entry["effect_details"] = effect_details
        log_entries.append(entry)

    # --- Apply Attack Effects --- 
    
    # Log the action
    action_details = {"attack_name": attack.name, "emoji": attack.emoji}
    add_log(f"{attacker.username} used {attack.name}!", source=attacker_role, effect_type="action", effect_details=action_details)
    
    damage_dealt = 0 # Track damage for logging/checks

    # 1. Damage Calculation (Enemy Target)
    if attack.power > 0 and attack.target == 'enemy':
        damage_dealt = calculate_damage(attacker, target_player, attack, attacker_stages, target_stages)
        current_target_hp = max(0, current_target_hp - damage_dealt)
        add_log(f"{target_player.username} took {damage_dealt} damage.", source=attacker_role, effect_type="damage")
        setattr(battle, target_hp_attr, current_target_hp)

    # 2. Direct HP Change (Healing, Recoil, Fixed Damage)
    if attack.hp_amount != 0:
        if attack.target == 'enemy':
            # Note: This adds/subtracts from potentially already reduced HP
            new_target_hp_direct = max(0, current_target_hp + attack.hp_amount) 
            hp_change_applied = new_target_hp_direct - current_target_hp # Calculate the actual change
            
            if hp_change_applied != 0:
                 if attack.hp_amount < 0:
                    add_log(f"{target_player.username} lost {abs(hp_change_applied)} HP directly.", source=attacker_role, effect_type="damage")
                 # Only update if damage wasn't already dealt by power calc
                 if damage_dealt == 0: 
                     setattr(battle, target_hp_attr, new_target_hp_direct)
                     current_target_hp = new_target_hp_direct # Update local variable

        elif attack.target == 'self':
            max_hp = attacker.hp 
            new_attacker_hp = clamp(current_attacker_hp + attack.hp_amount, 0, max_hp)
            hp_change_applied = new_attacker_hp - current_attacker_hp # Actual change

            if hp_change_applied != 0:
                setattr(battle, attacker_hp_attr, new_attacker_hp)
                current_attacker_hp = new_attacker_hp # Update local variable

                if attack.hp_amount > 0:
                    add_log(f"{attacker.username} recovered {abs(hp_change_applied)} HP.", source=attacker_role, effect_type="heal")
                elif attack.hp_amount < 0:
                    add_log(f"{attacker.username} lost {abs(hp_change_applied)} HP from the effort.", source=attacker_role, effect_type="damage")

                # Check if self-damage caused faint
                if new_attacker_hp <= 0:
                    add_log(f"{attacker.username} fainted!", source="system", effect_type="faint")
                    battle.status = 'finished'
                    battle.winner = target_player
                    battle_ended = True

    # 3. Check if TARGET fainted (after all damage/HP changes)
    if not battle_ended and getattr(battle, target_hp_attr) <= 0:
        add_log(f"{target_player.username} fainted!", source="system", effect_type="faint")
        battle.status = 'finished'
        battle.winner = attacker
        battle_ended = True

    # 4. Stat Stage Change (if battle hasn't ended)
    if not battle_ended and attack.target_stat != 'NONE' and attack.stat_mod != 0:
        db_stat = attack.target_stat
        stat_key_map = {'ATK': 'attack', 'DEF': 'defense', 'SPEED': 'speed'}
        stat_key = stat_key_map.get(db_stat, db_stat.lower())

        if stat_key in ['attack', 'defense', 'speed']:
            target_stages_ref = None
            target_username = ""
            if attack.target == 'enemy':
                target_stages_ref = target_stages
                target_username = target_player.username
            elif attack.target == 'self':
                target_stages_ref = attacker_stages
                target_username = attacker.username

            if target_stages_ref is not None:
                current_stage = target_stages_ref.get(stat_key, 0)
                new_stage = clamp(current_stage + attack.stat_mod, MIN_STAT_STAGE, MAX_STAT_STAGE)
                if new_stage != current_stage:
                    target_stages_ref[stat_key] = new_stage
                    change_dir = "raised" if attack.stat_mod > 0 else "lowered"
                    details = {"stat": stat_key, "mod": attack.stat_mod}
                    add_log(f"{target_username}'s {db_stat} was {change_dir}!", source=attacker_role, effect_type="stat_change", effect_details=details)
                else:
                    add_log(f"{target_username}'s {db_stat} won't go any {'higher' if attack.stat_mod > 0 else 'lower'}!", source=attacker_role, effect_type="info")
        else:
            add_log(f"(Attack targeted {stat_key}, which is not tracked for stages)", source="system", effect_type="info")

    # --- Update Momentum and Turn --- 
    if not battle_ended:
        # --- Calculate Actual Momentum Gain ---
        # Use the helper function to get the speed-influenced range
        min_gain, max_gain = calculate_momentum_gain_range(attack, attacker, attacker_stages)
        
        # Pick a random value within the calculated range
        actual_gain = random.randint(min_gain, max_gain) if max_gain >= min_gain else 0
        # --- End Momentum Calculation ---
        
        momentum_attr = f'current_momentum_{attacker_role}'
        new_momentum = getattr(battle, momentum_attr) + actual_gain
        setattr(battle, momentum_attr, new_momentum)
        # Update log message to show actual gain
        add_log(f"{attacker.username} built {actual_gain} momentum (Total: {new_momentum}).", source="system", effect_type="info") 
        
        # Check if turn switches (based on new total momentum)
        opponent_momentum_attr = f'current_momentum_{target_role}'
        opponent_momentum = getattr(battle, opponent_momentum_attr)
        
        if new_momentum > opponent_momentum:
            battle.whose_turn = target_role
            add_log(f"It is now {target_player.username}'s turn!", source="system", effect_type="info")

    # --- Finalize --- 
    # Append current action's log to the persistent battle log
    if not isinstance(battle.last_turn_summary, list):
         battle.last_turn_summary = [] 
    battle.last_turn_summary.extend(log_entries)
    
    # Save all changes to the battle object
    battle.save() 

    return log_entries, battle_ended