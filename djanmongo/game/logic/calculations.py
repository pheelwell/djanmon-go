import random
import math

from .constants import (
    MAX_STAT_STAGE, MIN_STAT_STAGE, 
    DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX,
    BASELINE_SPEED_FOR_MOMENTUM, MOMENTUM_UNCERTAINTY_MIN_FACTOR,
    MOMENTUM_COST_SPEED_MULTIPLIER_MIN, MOMENTUM_COST_SPEED_MULTIPLIER_MAX # Added cost constants
)


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

def calculate_damage(attacker_base_stats: dict, target_base_stats: dict, attack_power: int, attacker_stages: dict, target_stages: dict) -> int:
    """Calculates damage based on a simplified formula, using base stats and current stages."""
    if attack_power <= 0:
        return 0
    
    # Use base stats passed in the dictionaries
    attacker_base_atk = attacker_base_stats.get('attack', 1) # Default to 1 if missing
    target_base_def = target_base_stats.get('defense', 1) # Default to 1 if missing
    
    attacker_atk = get_modified_stat(attacker_base_atk, attacker_stages.get('attack', 0))
    target_def = get_modified_stat(target_base_def, target_stages.get('defense', 0))
    base_damage = (((2 * 50 / 5 + 2) * attack_power * attacker_atk / target_def) / 50) + 2
    random_modifier = random.uniform(DAMAGE_RANDOM_FACTOR_MIN, DAMAGE_RANDOM_FACTOR_MAX)
    final_damage = int(base_damage * random_modifier)
    return max(1, final_damage)

def calculate_momentum_cost_range(attack_base_cost: int, attacker_base_stats: dict, attacker_stages: dict) -> tuple[int, int]:
    """Calculates the min and max actual momentum COST based on speed scaling the base cost,
       using base stats and current stages.
    """
    if attack_base_cost <= 0:
        return (0, 0) # Cost cannot be zero or negative

    attacker_current_stage = attacker_stages.get('speed', 0)
    attacker_base_speed = attacker_base_stats.get('speed', BASELINE_SPEED_FOR_MOMENTUM) # Default to baseline if missing
    modified_attacker_speed = get_modified_stat(attacker_base_speed, attacker_current_stage)

    # Speed multiplier: Higher speed -> higher value
    speed_ratio = modified_attacker_speed / BASELINE_SPEED_FOR_MOMENTUM

    # Cost modifier: Higher speed ratio -> LOWER cost modifier (inverse relationship)
    # Clamp the modifier to prevent extreme costs (e.g., 0.5x to 1.5x cost)
    cost_modifier = clamp(1 / speed_ratio, MOMENTUM_COST_SPEED_MULTIPLIER_MIN, MOMENTUM_COST_SPEED_MULTIPLIER_MAX)

    # Calculate the speed-adjusted base cost
    speed_adjusted_cost = attack_base_cost * cost_modifier

    # Apply uncertainty range based on the *adjusted* cost
    # Example: +/- 15% uncertainty, minimum cost of 1
    uncertainty_factor = MOMENTUM_UNCERTAINTY_MIN_FACTOR # Use this for range (e.g., 0.15 means +/- 15%)
    cost_variation = speed_adjusted_cost * uncertainty_factor

    # Ensure costs are integers and at least 1
    min_cost = max(1, int(math.floor(speed_adjusted_cost - cost_variation)))
    max_cost = max(1, int(math.ceil(speed_adjusted_cost + cost_variation)))

    # Ensure min is not greater than max
    if min_cost > max_cost:
        min_cost = max_cost # Or set both to the average? Setting min=max is safer.

    return (min_cost, max_cost) 
