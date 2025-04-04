from rest_framework import serializers
from .models import Attack, Battle
from users.serializers import UserSerializer, BasicUserSerializer
from .battle_logic import calculate_momentum_gain_range

class AttackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attack
        fields = ('id', 'name', 'description', 'power', 'target', 'hp_amount', 'target_stat', 'stat_mod', 'emoji', 'momentum_cost')

# --- Battle Serializers ---

class BattleInitiateSerializer(serializers.Serializer):
    opponent_id = serializers.IntegerField(required=True)

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
            'last_turn_summary',
            'current_momentum_player1', 'current_momentum_player2', 'whose_turn',
            'my_selected_attacks',
            'updated_at'
        )
        read_only_fields = fields
        
    def get_my_selected_attacks(self, battle_instance):
        """ 
        Returns a list of the requesting user's selected attacks.
        Includes calculated min/max momentum gain *only* if it's the user's turn.
        """
        requesting_user = self.context.get('request').user
        if not requesting_user:
            return [] # Should not happen with IsAuthenticated

        user_role = battle_instance.get_player_role(requesting_user)
        if not user_role:
             return [] # User is not part of this battle

        # Get the user's selected attacks
        my_attacks = requesting_user.selected_attacks.all()

        # Determine if it's the user's turn to calculate gains
        is_my_turn = battle_instance.whose_turn == user_role
        actor_stages = battle_instance.stat_stages_player1 if user_role == 'player1' else battle_instance.stat_stages_player2

        serialized_attacks = []
        attack_serializer = AttackSerializer() # Instantiate once
        
        for attack in my_attacks:
            serialized_attack = attack_serializer.to_representation(attack)
            # Only calculate and add gain range if it is the user's turn
            if is_my_turn:
                min_gain, max_gain = calculate_momentum_gain_range(attack, requesting_user, actor_stages)
                serialized_attack['calculated_min_gain'] = min_gain
                serialized_attack['calculated_max_gain'] = max_gain
            # else: min/max gain fields will be absent
            serialized_attacks.append(serialized_attack)
            
        return serialized_attacks

class BattleListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing battles/requests."""
    player1 = BasicUserSerializer(read_only=True)
    player2 = BasicUserSerializer(read_only=True)

    class Meta:
        model = Battle
        fields = ('id', 'player1', 'player2', 'status', 'created_at')
