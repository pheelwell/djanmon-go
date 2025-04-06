# users/serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

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
            email=validated_data.get('email', '') # Handle optional email
        )
        user.set_password(validated_data['password'])
        # Maybe assign default stats/level here if not done in model defaults
        user.save()
        # Maybe assign default attacks here?
        return user

class BasicUserSerializer(serializers.ModelSerializer):
    """A very basic serializer for listing users"""
    class Meta:
        model = User
        fields = ('id', 'username', 'level')

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
            'id', 'username', 'level', 'hp', 'attack', 'defense', 'speed',
            'attacks', 'selected_attacks' 
        )
        read_only_fields = fields

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
    total_wins = serializers.SerializerMethodField()
    selected_attacks = serializers.SerializerMethodField(read_only=True) # User's current loadout

    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'level', 
            'total_wins', 
            'selected_attacks',
        )

    def get_total_wins(self, user_instance):
        # Reuse the method from the User model
        return user_instance.get_total_wins()

    def get_selected_attacks(self, user_instance):
        # Reuse logic similar to UserSerializer or import AttackSerializer
        from game.serializers import AttackSerializer
        attacks_queryset = user_instance.selected_attacks.all()
        # Limit the number of attacks shown in the leaderboard view if desired, e.g., [:4]
        return AttackSerializer(attacks_queryset, many=True, read_only=True).data