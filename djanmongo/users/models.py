from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator

# Import Attack model safely for relationship definition
from game.models import Attack

class User(AbstractUser):
    # Basic stats
    level = models.IntegerField(default=1)
    hp = models.IntegerField(default=20)
    max_hp = models.IntegerField(default=20) # Add max_hp
    attack = models.IntegerField(default=5)
    defense = models.IntegerField(default=5)
    speed = models.IntegerField(default=5)

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

    # Add methods here if needed, e.g., for calculating max HP based on level
    # def get_max_hp(self):
    #    return self.hp + (self.level - 1) * 5 # Example calculation
