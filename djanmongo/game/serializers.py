from rest_framework import serializers
from .models import Attack, Battle, AttackUsageStats
from users.serializers import UserSerializer, BasicUserSerializer
from .logic import calculate_momentum_cost_range
import collections # For sorting co-used attacks

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

# --- Nested Attack Detail Serializer (reuse if needed) ---
class NestedAttackDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attack
        # Include fields needed for hover card display
        fields = ('id', 'name', 'emoji', 'description', 'momentum_cost', 'creator')


class AttackLeaderboardSerializer(serializers.ModelSerializer):
    # Nest the basic attack details
    # attack_details = AttackSerializer(source='attack', read_only=True)
    attack_details = NestedAttackDetailSerializer(source='attack', read_only=True)
    # Get the owner's username from the related Attack's creator field
    owner_username = serializers.CharField(source='attack.creator.username', read_only=True, allow_null=True)
    # Rename wins_contributed for clarity in API response
    # total_wins = serializers.IntegerField(source='wins_contributed', read_only=True)

    # --- Calculated Fields ---
    win_rate = serializers.SerializerMethodField()
    win_rate_vs_bot = serializers.SerializerMethodField()
    damage_per_use = serializers.SerializerMethodField()
    top_co_used_attacks = serializers.SerializerMethodField()
    # --- End Calculated Fields ---

    class Meta:
        model = AttackUsageStats
        # Include new raw stat fields and calculated fields
        fields = (
            'attack_details', # Includes ID, name, emoji etc.
            'owner_username',
            'times_used',
            'wins_vs_human',
            'losses_vs_human',
            'wins_vs_bot',
            'losses_vs_bot',
            'total_damage_dealt',
            'total_healing_done',
            # Calculated fields
            'win_rate',
            'win_rate_vs_bot',
            'damage_per_use',
            'top_co_used_attacks',
            # Exclude raw co-used counts unless needed directly
            # 'co_used_with_counts',
        )
        read_only_fields = fields # Make all fields read-only

    def get_win_rate(self, obj):
        total_wins = obj.wins_vs_human + obj.wins_vs_bot
        total_uses = obj.wins_vs_human + obj.losses_vs_human + obj.wins_vs_bot + obj.losses_vs_bot # Use wins+losses for total games
        if total_uses == 0:
            return 0.0
        # Corrected calculation using total games
        return round((total_wins / total_uses) * 100, 1) # Percentage rounded 

    def get_win_rate_vs_bot(self, obj):
        total_bot_uses = obj.wins_vs_bot + obj.losses_vs_bot
        if total_bot_uses == 0:
            return None # Or 0.0 if preferred
        return round((obj.wins_vs_bot / total_bot_uses) * 100, 1)

    def get_damage_per_use(self, obj):
        if obj.times_used == 0:
            return 0
        # Ensure division by zero is handled, though times_used should be > 0 if damage exists
        return round(obj.total_damage_dealt / obj.times_used) if obj.times_used > 0 else 0

    def get_top_co_used_attacks(self, obj):
        if not isinstance(obj.co_used_with_counts, dict) or not obj.co_used_with_counts:
            return []

        # Sort co-used attacks by count descending
        sorted_counts = sorted(obj.co_used_with_counts.items(), key=lambda item: item[1], reverse=True)

        # Get top 3 attack IDs
        top_ids = [int(attack_id_str) for attack_id_str, count in sorted_counts[:3]]

        # Fetch basic details for these top attacks (reduces extra DB hits per row)
        # This relies on having fetched these attacks somewhere accessible,
        # maybe via a context passed to the serializer or a prefetched list.
        # Simple approach (less efficient): Fetch here
        top_attacks_qs = Attack.objects.filter(id__in=top_ids).values('id', 'name', 'emoji')
        top_attacks_dict = {a['id']: a for a in top_attacks_qs}

        # Return basic info, ordered by original count
        result = []
        for attack_id in top_ids:
            attack_info = top_attacks_dict.get(attack_id)
            if attack_info:
                result.append({
                    'id': attack_info['id'],
                    'name': attack_info['name'],
                    'emoji': attack_info['emoji']
                })
        return result
