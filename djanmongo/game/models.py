from django.db import models
from django.conf import settings
import json # For stat stages
import random # For initial turn
from django.core.exceptions import ValidationError # Needed for singleton
from .logic import constants # <-- Import local constants

# --- Game Configuration Singleton Model ---
class GameConfiguration(models.Model):
    attack_generation_cost = models.PositiveIntegerField(
        default=1, # Set the new default cost
        help_text="The cost in Booster Credits to generate a set of attacks."
    )

    def save(self, *args, **kwargs):
        if not self.pk and GameConfiguration.objects.exists():
            # Prevent creation of a new instance if one already exists
            raise ValidationError('There can be only one GameConfiguration instance')
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Game Configuration"
        
    class Meta:
        verbose_name_plural = "Game Configuration"

# --- END Game Configuration Model ---

# --- NEW: Script Model ---
class Script(models.Model):
    WHO_CHOICES = [
        ('ME', 'Me (Original Attacker)'),
        ('ENEMY', 'Enemy (Original Target)'),
        ('ANY', 'Any Player (Current Actor)'),
        # ('PLAYER1', 'Player 1 (Absolute)'), # Maybe add later if needed
        # ('PLAYER2', 'Player 2 (Absolute)'), # Maybe add later if needed
    ]
    WHEN_CHOICES = [
        ('ON_USE', 'On Attack Use (Immediate, Once)'),
        ('BEFORE_TURN', 'Before Turn Start'),
        ('AFTER_TURN', 'After Turn End'),
        ('BEFORE_ATTACK', 'Before Attack Action'),
        ('AFTER_ATTACK', 'After Attack Action'),
    ]
    DURATION_CHOICES = [
        ('ONCE', 'Once (Next time conditions met)'),
        ('PERSISTENT', 'Persistent (Until unregistered)'),
        # ('EVERY', 'Every Time (Synonym for Persistent?)') # Let's stick to PERSISTENT for now
    ]

    name = models.CharField(max_length=100, unique=True, help_text="Unique name for identifying the script in admin.")
    description = models.TextField(blank=True, help_text="Optional description of what the script does.")
    lua_code = models.TextField("Lua Code", help_text="The actual Lua script content.")
    # --- NEW Fields for Frontend Display --- 
    icon_emoji = models.CharField(max_length=5, blank=True, null=True, default="⚙️", help_text="Emoji to represent this script in the UI.")
    tooltip_description = models.CharField(max_length=150, blank=True, help_text="Short description shown on hover in the UI.")
    # --- END NEW Fields --- 
    
    # --- Link back to the Attack --- 
    attack = models.ForeignKey(
        'Attack', 
        related_name='scripts', # Attack can access its scripts via attack.scripts.all()
        on_delete=models.CASCADE, 
        help_text="The Attack this script is associated with."
    )
    
    # --- NEW Trigger System ---
    trigger_who = models.CharField(
        max_length=10, choices=WHO_CHOICES, default='ENEMY',
        help_text="Which player relative to the attack use triggers the script? 'ME'=Original Attacker, 'ENEMY'=Original Target, 'ANY'=Current Actor."
    )
    trigger_when = models.CharField(
        max_length=15, choices=WHEN_CHOICES, default='AFTER_TURN',
        help_text="When does the script trigger relative to turns or attacks?"
    )
    trigger_duration = models.CharField(
        max_length=10, choices=DURATION_CHOICES, default='PERSISTENT',
        help_text="How long does the script last? 'ONCE' triggers the next time, 'PERSISTENT' triggers repeatedly until unregistered."
    )

    # --- OLD Trigger Points (To be removed by migration) ---
    # trigger_on_attack = models.BooleanField(...)
    # trigger_before_attacker_turn = models.BooleanField(...)
    # trigger_after_attacker_turn = models.BooleanField(...)
    # trigger_before_target_turn = models.BooleanField(...)
    # trigger_after_target_turn = models.BooleanField(...)
    # --- End OLD Trigger Points ---

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_trigger_who_display()}, {self.get_trigger_when_display()}, {self.get_trigger_duration_display()})"

    def save(self, *args, **kwargs):
        # Ensure ON_USE is always ONCE
        if self.trigger_when == 'ON_USE':
            self.trigger_duration = 'ONCE'
            self.trigger_who = 'ME' # 'ON_USE' applies immediately for the user of the attack
        super().save(*args, **kwargs)

# --- END Script Model ---


class Attack(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=5, blank=True, null=True, help_text="Optional emoji icon for the attack")
    momentum_cost = models.PositiveIntegerField(default=1, help_text="Base momentum cost before speed modification")
    is_favorite = models.BooleanField(default=False, db_index=True, help_text="Whether the user marked this attack as a favorite.")
    
    # --- NEW: Link to Creator ---
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='created_attacks',
        on_delete=models.SET_NULL, # Keep attack even if creator deleted
        null=True, # Allow attacks without a creator (e.g., pre-defined)
        blank=True,
        help_text="The user who generated this attack."
    )
    # --- END Creator Link ---

    # turn_number = models.IntegerField(default=1) # This field seems unused, consider removing?
    
    def __str__(self):
        return self.name

# --- NEW: Attack Usage Stats Model ---
class AttackUsageStats(models.Model):
    attack = models.OneToOneField(
        Attack,
        on_delete=models.CASCADE,
        primary_key=True, # Use the attack's ID as the primary key
        related_name='usage_stats'
    )
    times_used = models.PositiveIntegerField(default=0, db_index=True, help_text="Total times this attack was used in any battle.")

    # --- NEW STAT FIELDS ---
    wins_vs_human = models.PositiveIntegerField(default=0, db_index=True, help_text="Wins in battles vs human opponents where this attack was used by the winner.")
    losses_vs_human = models.PositiveIntegerField(default=0, db_index=True, help_text="Losses in battles vs human opponents where this attack was used by the loser.")
    wins_vs_bot = models.PositiveIntegerField(default=0, db_index=True, help_text="Wins in battles vs bot opponents where this attack was used by the winner.")
    losses_vs_bot = models.PositiveIntegerField(default=0, db_index=True, help_text="Losses in battles vs bot opponents where this attack was used by the loser.")

    total_damage_dealt = models.BigIntegerField(default=0, help_text="Sum of all direct damage dealt by this attack across all uses.")
    total_healing_done = models.BigIntegerField(default=0, help_text="Sum of all direct healing done by this attack across all uses.")

    # Stores counts of other attacks used in the same battles by the same player
    # Format: {"<attack_id>": <count>, "<attack_id>": <count>, ...}
    co_used_with_counts = models.JSONField(default=dict, help_text="Counts of other attacks used alongside this one.")
    # --- END NEW STAT FIELDS ---

    def __str__(self):
        return f"Stats for {self.attack.name}"
# --- END Attack Usage Stats Model ---

class Battle(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('finished', 'Finished'),
        ('declined', 'Declined'),
    ]
    TURN_CHOICES = [
        ('player1', 'Player 1'),
        ('player2', 'Player 2'),
    ]

    player1 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='battles_as_player1', on_delete=models.CASCADE)
    player2 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='battles_as_player2', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='battles_won')

    # Game state fields
    current_hp_player1 = models.IntegerField(default=100)
    current_hp_player2 = models.IntegerField(default=100)
    # Use JSONField for stat stages, initialized as empty dict
    stat_stages_player1 = models.JSONField(default=dict)
    stat_stages_player2 = models.JSONField(default=dict)
    custom_statuses_player1 = models.JSONField(default=dict)
    custom_statuses_player2 = models.JSONField(default=dict)
    registered_scripts = models.JSONField(default=list) # Stores active script instances
    last_turn_summary = models.JSONField(default=list) # Log of actions/effects

    # --- Momentum and Turn --- 
    current_momentum_player1 = models.IntegerField(default=0) 
    current_momentum_player2 = models.IntegerField(default=0)
    whose_turn = models.CharField(max_length=10, choices=[('player1', 'Player 1'), ('player2', 'Player 2')], blank=True, null=True) # Can be null initially
    turn_number = models.IntegerField(default=1)
    
    # NEW: Flag if player2 is AI-controlled for this specific battle
    player2_is_ai_controlled = models.BooleanField(default=False, help_text="True if player 2 is being controlled by AI in this battle.")
    
    # ADDED BACK: Store attacks selected specifically for this battle
    battle_attacks_player1 = models.ManyToManyField(
        'Attack',
        related_name='battles_as_player1_attack',
        through='BattlePlayer1AttackSelection',
        blank=True
    )
    battle_attacks_player2 = models.ManyToManyField(
        'Attack',
        related_name='battles_as_player2_attack',
        through='BattlePlayer2AttackSelection',
        blank=True
    )

    # ADDED: Store attacks actually used by each player in this battle
    # This helps determine win contributions later
    player1_attacks_used = models.ManyToManyField(
        'Attack',
        related_name='battles_used_by_player1',
        blank=True
    )
    player2_attacks_used = models.ManyToManyField(
        'Attack',
        related_name='battles_used_by_player2',
        blank=True
    )

    # Timestamping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def initialize_battle_state(self):
        """Sets initial state based on players' current profiles WHEN battle becomes active."""
        # Ensure this is only called when status is being set to active
        # The actual status change should happen *before* calling this in the view.
        if self.status != 'active':
            print(f"Warning: initialize_battle_state called on non-active battle (status: {self.status}). Skipping initialization.")
            return

        print(f"[Battle {self.id}] Initializing state for ACTIVE battle.")
        
        if self.player1:
            self.current_hp_player1 = self.player1.hp
            # Copy player1's CURRENT selected attacks
            self.battle_attacks_player1.set(self.player1.selected_attacks.all())
            print(f"  Copied {self.battle_attacks_player1.count()} attacks for Player 1 ({self.player1.username})")
        else:
            self.current_hp_player1 = 0 # Or handle error
            self.battle_attacks_player1.clear()
            
        if self.player2:
            self.current_hp_player2 = self.player2.hp
            # Copy player2's CURRENT selected attacks
            self.battle_attacks_player2.set(self.player2.selected_attacks.all())
            print(f"  Copied {self.battle_attacks_player2.count()} attacks for Player 2 ({self.player2.username})")
        else:
            self.current_hp_player2 = 0
            self.battle_attacks_player2.clear()
        
        # Reset other state fields
        self.stat_stages_player1 = {}
        self.stat_stages_player2 = {}
        self.custom_statuses_player1 = {}
        self.custom_statuses_player2 = {}
        self.registered_scripts = []
        self.last_turn_summary = []
        self.current_momentum_player1 = settings.BASE_MOMENTUM
        self.current_momentum_player2 = settings.BASE_MOMENTUM
        self.turn_number = 1
        self.whose_turn = 'player1' # Player 1 starts by default
        
        # Save the initialized state
        # The calling view might save again, but saving here ensures consistency
        self.save() 

    def get_player_role(self, user):
        """Returns 'player1' or 'player2' if the user is in this battle, else None."""
        if user == self.player1:
            return 'player1'
        elif user == self.player2:
            return 'player2'
        return None

    # Resolve turn logic will be in battle_logic.py, but could be called from here
    # def resolve_turn(self):
    #     from .battle_logic import resolve_battle_turn # Avoid circular import
    #     resolve_battle_turn(self)

# --- Through Models for Battle Attacks --- 
class BattlePlayer1AttackSelection(models.Model):
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE)
    attack = models.ForeignKey(Attack, on_delete=models.CASCADE)
    # Add any extra fields if needed, e.g., usage count
    class Meta:
        unique_together = ('battle', 'attack')

class BattlePlayer2AttackSelection(models.Model):
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE)
    attack = models.ForeignKey(Attack, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('battle', 'attack')