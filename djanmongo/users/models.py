from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator
from django.db.models import Q, Count
from django.db import models as db_models
from django.utils import timezone # Added for default value
import json # For JSONField default

# --- NEW: Import Django Settings --- 
from django.conf import settings
# --- END NEW ---

# Import Attack model safely for relationship definition
from game.models import Attack

class User(AbstractUser):
    # Basic stats
    level = models.IntegerField(default=1)
    hp = models.IntegerField(default=100)
    attack = models.IntegerField(default=100)
    defense = models.IntegerField(default=100)
    speed = models.IntegerField(default=100)

    # NEW: Currency for boosters
    booster_credits = models.PositiveIntegerField(default=100, help_text="Currency earned from battles to open boosters.")

    # NEW: Track user activity
    last_seen = models.DateTimeField(default=timezone.now, help_text="Last time the user made an authenticated request.")

    # NEW: Profile Picture fields (Storing Base64)
    profile_picture_base64 = models.TextField(
        blank=True, 
        null=True, 
        help_text="Base64 encoded string of the generated profile picture."
    )
    profile_picture_prompt = models.TextField(
        blank=True, 
        null=True, 
        help_text="The prompt used to generate the current profile picture."
    )

    # --- Fields removed to match DB state: is_bot, difficulty ---
    # NEW: Allow others to fight this user as a bot
    allow_bot_challenges = models.BooleanField(
        default=False, 
        help_text="Allows other users to initiate a battle against this user controlled by AI."
    )
    # -----------------------

    # Relationships
    # All attacks the user has learned
    attacks = models.ManyToManyField('game.Attack', related_name='learned_by_users', blank=True)
    
    # Attacks currently selected for battle (max 6)
    # Add the missing field:
    selected_attacks = models.ManyToManyField(
        'game.Attack',
        related_name='selected_by_users',
        blank=True,
        # You might add a validator here later if needed, 
        # but view-level validation is often sufficient for M2M counts
    )

    # NEW: Store detailed battle stats
    stats = models.JSONField(
        default=dict, 
        help_text="Stores battle statistics like wins/losses vs human/bot, damage dealt etc."
    )

    def __str__(self):
        return f"{self.username} (Lvl {self.level})"

    # --- Leaderboard Stats ---

    def get_total_wins(self):
        """Counts the number of finished battles this user has won."""
        # Ensure we import Battle model locally to avoid potential circular imports at module level
        from game.models import Battle 
        return Battle.objects.filter(winner=self, status='finished').count()

    def get_total_losses(self):
        """Counts the number of finished battles this user has lost."""
        from game.models import Battle
        # Battles where the user participated but was not the winner, and the battle is finished
        return Battle.objects.filter(
            Q(player1=self) | Q(player2=self), 
            status='finished'
        ).exclude(winner=self).count()

    def get_total_rounds_played(self):
        """Counts the total number of finished battles this user participated in."""
        from game.models import Battle
        return Battle.objects.filter(
            Q(player1=self) | Q(player2=self), 
            status='finished'
        ).count()

    def get_nemesis(self):
        """Finds the opponent the user has lost to the most using DB aggregation."""
        from game.models import Battle
        from django.db.models import Count, Case, When, F, Q, IntegerField # Import necessary functions

        # Filter finished battles where this user participated but did not win
        lost_battles_base_qs = Battle.objects.filter(
            Q(player1=self) | Q(player2=self),
            status='finished'
        ).exclude(winner=self)

        # Annotate with the opponent's ID, group by it, count, and order
        opponent_losses = lost_battles_base_qs.annotate(
            # Determine opponent ID based on who player1/player2 is
            opponent_id=Case(
                When(player1=self, then=F('player2_id')),
                When(player2=self, then=F('player1_id')),
                # default=Value(None), # Should not happen due to the initial filter
                output_field=IntegerField(), # Specify the output type
            )
        ).values(
            'opponent_id' # Group by the annotated opponent_id
        ).annotate(
            losses=Count('opponent_id') # Count battles for each opponent_id group
        ).order_by(
            '-losses' # Order by the count descending to get the highest first
        )

        # Get the top result (the nemesis)
        nemesis_data = opponent_losses.first()

        if nemesis_data and nemesis_data.get('opponent_id') is not None:
            try:
                # Fetch the nemesis User object using the ID found
                # No need for _default_manager here, standard manager is fine
                nemesis_user = User.objects.get(pk=nemesis_data['opponent_id'])
                return {
                    "username": nemesis_user.username,
                    "losses_against": nemesis_data['losses']
                }
            except User.DoesNotExist:
                # This case should ideally not happen if foreign keys are intact
                # Log an error maybe?
                return None 
        else:
            # No losses found or opponent_id was somehow None
            return None

    # --- NEW: Method to update stats after a battle --- 
    def update_stats_on_battle_end(self, is_winner, is_vs_bot, damage_dealt=0):
        """Updates stats stored in the profile's JSON field after a battle.
           Also updates the user's booster credits.
        """
        # Ensure stats is a dictionary
        if not isinstance(self.stats, dict):
            # Attempt to load if it's a string, otherwise reset
            try:
                loaded_stats = json.loads(self.stats) if isinstance(self.stats, str) else {}
                self.stats = loaded_stats if isinstance(loaded_stats, dict) else {}
            except json.JSONDecodeError:
                self.stats = {}

        # Ensure keys exist and increment damage
        self.stats.setdefault('wins_vs_human', 0)
        self.stats.setdefault('losses_vs_human', 0)
        self.stats.setdefault('wins_vs_bot', 0)
        self.stats.setdefault('losses_vs_bot', 0)
        self.stats.setdefault('total_damage_dealt', 0)
        # self.stats.setdefault('total_battles', 0) # Optional: track total battles

        self.stats['total_damage_dealt'] += damage_dealt
        # self.stats['total_battles'] += 1 # Optional

        # --- NEW: Calculate and Update Booster Credits ---
        credits_earned = 0
        if is_winner:
            if is_vs_bot:
                self.stats['wins_vs_bot'] += 1
                credits_earned = settings.CREDITS_WIN_VS_BOT # Use settings
            else:
                self.stats['wins_vs_human'] += 1
                credits_earned = settings.CREDITS_WIN_VS_HUMAN # Use settings
        else: # Loser
            if is_vs_bot:
                self.stats['losses_vs_bot'] += 1
            else:
                self.stats['losses_vs_human'] += 1
            credits_earned = settings.CREDITS_LOSS # Use settings

        self.booster_credits = (self.booster_credits or 0) + credits_earned # Ensure booster_credits is not None
        # --- END NEW ---

        # Save the updated stats and booster_credits fields
        self.save(update_fields=['stats', 'booster_credits'])
        print(f"[Stats Update - User] User {self.username} awarded {credits_earned} credits. New total: {self.booster_credits}") # Add logging
