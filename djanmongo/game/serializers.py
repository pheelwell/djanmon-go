from rest_framework import serializers
from .models import Attack, Battle, AttackUsageStats
from users.serializers import UserSerializer, BasicUserSerializer
from .logic import calculate_momentum_cost_range

class AttackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attack
        fields = (
            'id', 'name', 'description', 'emoji', 'momentum_cost',
        )

# --- Battle Serializers ---

class BattleInitiateSerializer(serializers.Serializer):
    opponent_id = serializers.IntegerField(required=True)
    fight_as_bot = serializers.BooleanField(required=False, default=False, help_text="Set to true to fight the opponent as AI (if they allow it). Otherwise, sends a normal challenge.")

class BattleRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'], required=True)

class BattleActionSerializer(serializers.Serializer):
    attack_id = serializers.IntegerField(required=True)

class BattleSerializer(serializers.ModelSerializer):
    player1 = UserSerializer(read_only=True)
    player2 = UserSerializer(read_only=True)
    winner = BasicUserSerializer(read_only=True)
    
    my_selected_attacks = serializers.SerializerMethodField()

    class Meta:
        model = Battle
        fields = (
            'id', 'player1', 'player2', 'status', 'winner',
            'current_hp_player1', 'current_hp_player2',
            'stat_stages_player1', 'stat_stages_player2',
            'custom_statuses_player1', 'custom_statuses_player2',
            'last_turn_summary',
            'current_momentum_player1', 'current_momentum_player2', 'whose_turn',
            'my_selected_attacks',
            'player2_is_ai_controlled',
            'updated_at'
        )
        read_only_fields = fields
        
    def get_my_selected_attacks(self, battle_instance):
        """ 
        Returns a list of the requesting user's selected attacks *specific to this battle*.
        Includes calculated min/max momentum COST *only* if it's the user's turn.
        """
        requesting_user = self.context.get('request').user
        if not requesting_user:
            return [] # Should not happen with IsAuthenticated

        user_role = battle_instance.get_player_role(requesting_user)
        if not user_role:
             return [] # User is not part of this battle

        # --- MODIFIED: Get attacks from battle-specific fields --- 
        if user_role == 'player1':
            my_attacks = battle_instance.battle_attacks_player1.all()
            actor_stages = battle_instance.stat_stages_player1
        else: # user_role == 'player2'
            my_attacks = battle_instance.battle_attacks_player2.all()
            actor_stages = battle_instance.stat_stages_player2
        # --- END MODIFICATION --- 

        # Determine if it's the user's turn to calculate gains
        is_my_turn = battle_instance.whose_turn == user_role

        serialized_attacks = []
        attack_serializer = AttackSerializer() # Instantiate once
        
        for attack in my_attacks:
            serialized_attack = attack_serializer.to_representation(attack)
            # Only calculate and add cost range if it is the user's turn
            if is_my_turn:
                # Construct base stats dict from the user object
                attacker_base_stats = {
                    'hp': requesting_user.hp,
                    'attack': requesting_user.attack,
                    'defense': requesting_user.defense,
                    'speed': requesting_user.speed
                }
                # Use the renamed cost calculation function
                # Pass the base cost, the stats dict, and the stages dict
                min_cost, max_cost = calculate_momentum_cost_range(
                    attack.momentum_cost, 
                    attacker_base_stats, 
                    actor_stages
                )
                # Rename the fields
                serialized_attack['calculated_min_cost'] = min_cost
                serialized_attack['calculated_max_cost'] = max_cost
            # else: min/max cost fields will be absent
            serialized_attacks.append(serialized_attack)
            
        return serialized_attacks

class BattleListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing battles/requests."""
    player1 = BasicUserSerializer(read_only=True)
    player2 = BasicUserSerializer(read_only=True)

    class Meta:
        model = Battle
        fields = ('id', 'player1', 'player2', 'status', 'created_at')

# --- Attack Generation Serializer ---
class GenerateAttackRequestSerializer(serializers.Serializer):
    concept = serializers.CharField(max_length=50, required=True, help_text="Short concept (max 50 chars) to guide attack generation.")
    favorite_attack_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        max_length=6,
        help_text="Optional list of up to 6 favorite attack IDs to influence generation."
    )

# --- NEW: Attack Leaderboard Serializer ---
class AttackLeaderboardSerializer(serializers.ModelSerializer):
    # Nest the basic attack details
    attack_details = AttackSerializer(source='attack', read_only=True)
    # Get the owner's username from the related Attack's creator field
    owner_username = serializers.CharField(source='attack.creator.username', read_only=True, allow_null=True)
    # Rename wins_contributed for clarity in API response
    total_wins = serializers.IntegerField(source='wins_contributed', read_only=True)

    class Meta:
        model = AttackUsageStats
        fields = (
            # 'attack', # Don't need the raw ID probably
            'attack_details',
            'owner_username',
            'times_used',
            'total_wins' 
        )
# --- END Attack Leaderboard Serializer ---
