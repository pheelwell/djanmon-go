# users/serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import json

from .models import User
# Import AttackSerializer locally where needed to avoid potential circular imports at module level
# from game.serializers import AttackSerializer 

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email') # Add other fields like email if desired
        extra_kwargs = {
            'email': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        # Basic validation for number of attacks (should ideally be in user update, not registration)
        # if 'attacks' in attrs and len(attrs['attacks']) > 6:
        #     raise serializers.ValidationError({"attacks": "Cannot have more than 6 attacks."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data.get('email', ''), # Handle optional email
        )
        user.set_password(validated_data['password'])
        # Maybe assign default stats/level here if not done in model defaults
        user.save()
        # Maybe assign default attacks here?
        return user

class BasicUserSerializer(serializers.ModelSerializer):
    """A basic serializer for listing users, now including profile picture."""
    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'level', 
            'allow_bot_challenges', 
            'profile_picture_base64'
        )

class UserProfileSerializer(serializers.ModelSerializer):
    # Use a SerializerMethodField to avoid circular import
    attacks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'level', 'hp', 'attack', 'defense', 'speed', 'attacks')
        read_only_fields = fields

    def get_attacks(self, user_instance):
        # Import AttackSerializer *inside* the method where it's needed
        from game.serializers import AttackSerializer
        # Access the related attacks and serialize them
        attacks_queryset = user_instance.attacks.all()
        return AttackSerializer(attacks_queryset, many=True, read_only=True).data

# --- Updated UserSerializer --- 
class UserSerializer(serializers.ModelSerializer):
    """Serializer for the full user profile, including selected attacks."""
    attacks = serializers.SerializerMethodField() 
    selected_attacks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'level', 
            'hp', 'attack', 'defense', 'speed',
            'attacks', 'selected_attacks', 'booster_credits',
            'allow_bot_challenges', 'last_seen', # Added last_seen
            'stats', # Added stats
            'profile_picture_base64', 'profile_picture_prompt' # Use base64 field
        )
        read_only_fields = (
            'id', 'username', 'level', 
            'hp', 'attack', 'defense', 'speed',
            'attacks', 'selected_attacks', 'booster_credits', 'last_seen', 'stats',
            'profile_picture_prompt' # Prompt usually read-only for client
            # profile_picture_base64 is implicitly read-only as it's not listed for update
        )

    def get_attacks(self, user_instance):
        # Moved import inside method
        from game.serializers import AttackSerializer
        attacks_queryset = user_instance.attacks.all()
        return AttackSerializer(attacks_queryset, many=True, read_only=True).data

    def get_selected_attacks(self, user_instance):
        # Moved import inside method
        from game.serializers import AttackSerializer
        attacks_queryset = user_instance.selected_attacks.all()
        return AttackSerializer(attacks_queryset, many=True, read_only=True).data

# --- NEW: Serializer for Updating Base Stats --- 
STAT_INCREMENT = 10
MIN_STAT_VALUE = 10
TARGET_SUM = 400

class UserStatsUpdateSerializer(serializers.ModelSerializer):
    hp = serializers.IntegerField(min_value=MIN_STAT_VALUE)
    attack = serializers.IntegerField(min_value=MIN_STAT_VALUE)
    defense = serializers.IntegerField(min_value=MIN_STAT_VALUE)
    speed = serializers.IntegerField(min_value=MIN_STAT_VALUE)

    class Meta:
        model = User
        fields = ('hp', 'attack', 'defense', 'speed') # Fields to update

    def validate(self, data):
        hp = data.get('hp')
        attack = data.get('attack')
        defense = data.get('defense')
        speed = data.get('speed')
        
        # Check increments
        for stat_name, value in data.items():
            if value % STAT_INCREMENT != 0:
                raise serializers.ValidationError({stat_name: f"Stat must be a multiple of {STAT_INCREMENT}."})

        # Check sum
        current_sum = hp + attack + defense + speed
        if current_sum != TARGET_SUM:
            raise serializers.ValidationError(
                f"Total stats must sum to {TARGET_SUM}. Current sum: {current_sum}."
            )
            
        return data
        
    # Override update if necessary, but RetrieveUpdateAPIView might handle it
    # if the fields match the model fields directly.


# --- NEW: Leaderboard Serializers ---

class UserStatsSerializer(serializers.ModelSerializer):
    """Serializer for the current user's detailed stats."""
    total_wins = serializers.SerializerMethodField()
    total_losses = serializers.SerializerMethodField()
    total_rounds_played = serializers.SerializerMethodField()
    nemesis = serializers.SerializerMethodField()
    # Note: Attack usage stats are deferred

    class Meta:
        model = User
        fields = (
            'username', # Or include other base User fields if needed
            'total_wins', 
            'total_losses', 
            'total_rounds_played', 
            'nemesis',
        )

    def get_total_wins(self, user_instance):
        return user_instance.get_total_wins()

    def get_total_losses(self, user_instance):
        return user_instance.get_total_losses()

    def get_total_rounds_played(self, user_instance):
        return user_instance.get_total_rounds_played()

    def get_nemesis(self, user_instance):
        # The model method already returns a dict or None
        return user_instance.get_nemesis()


class LeaderboardUserSerializer(serializers.ModelSerializer):
    """Serializer for displaying users on the public leaderboard."""
    # total_wins = serializers.SerializerMethodField() # REMOVED - Replaced by detailed stats
    selected_attacks = serializers.SerializerMethodField(read_only=True) # User's current loadout

    # --- RE-ADD STAT FIELDS --- 
    wins_vs_human = serializers.SerializerMethodField()
    losses_vs_human = serializers.SerializerMethodField()
    wins_vs_bot = serializers.SerializerMethodField()
    losses_vs_bot = serializers.SerializerMethodField()
    total_damage_dealt = serializers.SerializerMethodField()
    # --- END RE-ADD STAT FIELDS ---

    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'level', 
            'selected_attacks',
            # --- ADDED new stat fields to output ---
            'wins_vs_human',
            'losses_vs_human',
            'wins_vs_bot',
            'losses_vs_bot',
            'total_damage_dealt',
            # --- END ADDED ---
        )

    # def get_total_wins(self, user_instance):
    #     # Reuse the method from the User model
    #     return user_instance.get_total_wins()

    # --- RE-ADD Methods to get stats safely from JSON --- 
    def get_user_stat(self, obj, key, default=0):
        """Helper to safely get stats from user.stats JSON field."""
        stats_data = getattr(obj, 'stats', {})
        if not isinstance(stats_data, dict):
            # Attempt to load if it's a string, otherwise return default
            try:
                loaded_stats = json.loads(stats_data) if isinstance(stats_data, str) else {}
                stats_data = loaded_stats if isinstance(loaded_stats, dict) else {}
            except json.JSONDecodeError:
                stats_data = {}
        return stats_data.get(key, default)

    def get_wins_vs_human(self, obj):
        return self.get_user_stat(obj, 'wins_vs_human')

    def get_losses_vs_human(self, obj):
        return self.get_user_stat(obj, 'losses_vs_human')

    def get_wins_vs_bot(self, obj):
        return self.get_user_stat(obj, 'wins_vs_bot')

    def get_losses_vs_bot(self, obj):
        return self.get_user_stat(obj, 'losses_vs_bot')

    def get_total_damage_dealt(self, obj):
        return self.get_user_stat(obj, 'total_damage_dealt')
    # --- END RE-ADD Methods --- 

    def get_selected_attacks(self, user_instance):
        # Reuse logic similar to UserSerializer or import AttackSerializer
        from game.serializers import AttackSerializer
        attacks_queryset = user_instance.selected_attacks.all()
        # Limit the number of attacks shown in the leaderboard view if desired, e.g., [:4]
        return AttackSerializer(attacks_queryset, many=True, read_only=True).data