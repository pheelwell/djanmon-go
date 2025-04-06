import random
import math

# Import constants from the same directory
from .constants import (
    MAX_STAT_STAGE, MIN_STAT_STAGE, 
    DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX,
    BASELINE_SPEED_FOR_MOMENTUM, MOMENTUM_UNCERTAINTY_MIN_FACTOR # Added momentum constants
)

# Removed commented-out type hints

def clamp(value, min_val, max_val):
    """Clamps a value between min_val and max_val."""
    return max(min_val, min(value, max_val))

def calculate_stat_modifier(stage):
    """Calculates the multiplier based on Pokemon stat stage rules."""
    stage = clamp(stage, MIN_STAT_STAGE, MAX_STAT_STAGE)
    if stage > 0:
        return (2 + stage) / 2.0
    elif stage < 0:
        return 2.0 / (2 + abs(stage))
    else:
        return 1.0

def get_modified_stat(base_stat, stage):
    """Applies the stat stage modifier to a base stat."""
    modifier = calculate_stat_modifier(stage)
    return max(1, int(base_stat * modifier))

def calculate_damage(attacker, target, attack, attacker_stages: dict, target_stages: dict) -> int:
    """Calculates damage based on a simplified formula."""
    if attack.power <= 0:
        return 0
    attacker_atk = get_modified_stat(attacker.attack, attacker_stages.get('attack', 0))
    target_def = get_modified_stat(target.defense, target_stages.get('defense', 0))
    base_damage = (((2 * 50 / 5 + 2) * attack.power * attacker_atk / target_def) / 50) + 2
    random_modifier = random.uniform(DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX)
    final_damage = int(base_damage * random_modifier)
    return max(1, final_damage)

def calculate_momentum_gain_range(attack, attacker, attacker_stages: dict) -> tuple[int, int]:
    """Calculates the min and max actual momentum gain based on speed scaling the base cost."""
    base_cost = attack.momentum_cost
    if base_cost <= 0:
        return (0, 0)

    attacker_current_stage = attacker_stages.get('speed', 0)
    modified_attacker_speed = get_modified_stat(attacker.speed, attacker_current_stage)
    
    # Use constants
    speed_multiplier = clamp(modified_attacker_speed / BASELINE_SPEED_FOR_MOMENTUM, 0.33, 3.0) 
    speed_adjusted_cost = base_cost * speed_multiplier

    # Use constant
    lower_bound = max(1, int(math.ceil(speed_adjusted_cost * MOMENTUM_UNCERTAINTY_MIN_FACTOR))) if speed_adjusted_cost > 0 else 0
    upper_bound = max(1, int(math.floor(speed_adjusted_cost))) if speed_adjusted_cost > 0 else 0

    if lower_bound > upper_bound:
            lower_bound = upper_bound 
            
    return (lower_bound, upper_bound) 