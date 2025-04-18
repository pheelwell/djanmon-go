# djanmongo/game/logic/constants.py

# Battle Mechanics
MAX_STAT_STAGE = 6
MIN_STAT_STAGE = -6
DAMAGE_RANDOM_FACTOR_MIN = 0.85
DAMAGE_RANDOM_FACTOR_MAX = 1.00

# Momentum Mechanics
BASELINE_SPEED_FOR_MOMENTUM = 100 # Speed at which cost multiplier is 1.0
MOMENTUM_COST_SPEED_MULTIPLIER_MIN = 0.5 # Max cost reduction (e.g., 0.5 means cost can be halved at high speed)
MOMENTUM_COST_SPEED_MULTIPLIER_MAX = 1.5 # Max cost increase (e.g., 1.5 means cost * 1.5 at low speed)
MOMENTUM_UNCERTAINTY_MIN_FACTOR = 0.15 # +/- factor for cost variance (e.g., 0.15 -> +/- 15%)
INITIAL_MOMENTUM = 50 # Starting momentum for each player 