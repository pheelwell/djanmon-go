from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator
from django.db.models import Q, Count
from django.db import models as db_models
from django.utils import timezone # Added for default value

# Import Attack model safely for relationship definition
from game.models import Attack

class User(AbstractUser):
    # Basic stats
    level = models.IntegerField(default=1)
    hp = models.IntegerField(default=20)
    attack = models.IntegerField(default=5)
    defense = models.IntegerField(default=5)
    speed = models.IntegerField(default=5)

    # NEW: Currency for boosters
    booster_credits = models.PositiveIntegerField(default=0, help_text="Currency earned from battles to open boosters.")

    # NEW: Track user activity
    last_seen = models.DateTimeField(default=timezone.now, help_text="Last time the user made an authenticated request.")

    # --- NEW: Bot Fields ---
    is_bot = models.BooleanField(default=False, help_text="Identifies if this user is an AI-controlled bot.")
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        blank=True, # Allow blank for regular users
        null=True,  # Allow null for regular users
        help_text="Difficulty level if this user is a bot."
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
        """Finds the opponent the user has lost to the most."""
        from game.models import Battle
        
        # Find all finished battles the user lost
        lost_battles = Battle.objects.filter(
            Q(player1=self) | Q(player2=self), 
            status='finished'
        ).exclude(winner=self)

        # Determine the opponent in each lost battle
        opponent_ids = []
        for battle in lost_battles:
            if battle.player1 == self:
                opponent_ids.append(battle.player2_id)
            else:
                opponent_ids.append(battle.player1_id)
        
        if not opponent_ids:
            return None # No losses, no nemesis

        # Count losses against each opponent ID
        loss_counts = {}
        for opp_id in opponent_ids:
            loss_counts[opp_id] = loss_counts.get(opp_id, 0) + 1
        
        # Find the opponent ID with the maximum losses
        if not loss_counts:
             return None
             
        nemesis_id = max(loss_counts, key=loss_counts.get)
        
        # Get the User object for the nemesis
        try:
            # Use the base manager to avoid any default filtering
            nemesis_user = User._default_manager.get(pk=nemesis_id) 
            return {
                "username": nemesis_user.username,
                "losses_against": loss_counts[nemesis_id]
            }
        except User.DoesNotExist:
            return None # Should not happen if data is consistent
