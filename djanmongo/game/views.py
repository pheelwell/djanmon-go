from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q # For OR queries
import json # For parsing potential JSON output from LLM
import bleach # For sanitizing text output from LLM
import random # For generating random data
from django.conf import settings # <-- Add settings import
import google.generativeai as genai # <-- Add genai import
# --- Add imports for time calculations --- 
from django.utils import timezone
from datetime import timedelta 
# ---------------------------------------

from .models import Attack, Battle, Script, AttackUsageStats, GameConfiguration # <-- Add GameConfiguration
from users.models import User
from .serializers import (
    AttackSerializer, BattleInitiateSerializer, BattleRespondSerializer,
    BattleActionSerializer, BattleSerializer, BattleListSerializer,
    GenerateAttackRequestSerializer, AttackLeaderboardSerializer # Added AttackLeaderboardSerializer
)
from .battle_logic import apply_attack # Import the new logic function
# Import new helper functions
from .attack_generation import (
    construct_generation_prompt,
    call_gemini_api,
    process_and_save_generated_attacks
)


class AttackListView(generics.ListAPIView):
    queryset = Attack.objects.all()
    serializer_class = AttackSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Allow viewing, maybe restrict creation


class InitiateBattleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = BattleInitiateSerializer(data=request.data)
        if serializer.is_valid():
            opponent_id = serializer.validated_data['opponent_id']
            fight_as_bot = serializer.validated_data['fight_as_bot'] # Get the new flag
            player1 = request.user

            if player1.id == opponent_id:
                return Response({"error": "You cannot battle yourself."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                player2 = User.objects.get(pk=opponent_id)
            except User.DoesNotExist:
                return Response({"error": "Opponent not found."}, status=status.HTTP_404_NOT_FOUND)

            # --- Check if trying to fight as bot is allowed --- 
            if fight_as_bot and not player2.allow_bot_challenges:
                return Response({"error": f"{player2.username} does not allow being fought as a bot."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if an active or pending battle already exists between these users
            existing_battle = Battle.objects.filter(
                (Q(player1=player1, player2=player2) | Q(player1=player2, player2=player1)),
                status__in=['pending', 'active']
            ).first()

            if existing_battle:
                 # If fighting as bot is requested, maybe allow starting even if pending exists?
                 # For now, keep the strict check: no existing pending/active battles.
                 return Response({"error": "An active or pending battle already exists with this user.", "battle_id": existing_battle.id}, status=status.HTTP_400_BAD_REQUEST)

            # --- MODIFIED BATTLE CHECK ---
            # Check if player1 is in an active HUMAN vs HUMAN battle
            player1_in_human_battle = Battle.objects.filter(
                (Q(player1=player1) | Q(player2=player1)),
                status='active',
                player2_is_ai_controlled=False # Check if it's NOT an AI battle
            ).exists()
            if player1_in_human_battle:
                return Response({"error": "You are currently in an active battle against a human."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if player2 is in an active HUMAN vs HUMAN battle
            # We only need to check player2 if they are not a bot themselves (though bots might be handled differently)
            # This check assumes player2 is human; if player2 is a bot, this check is likely unnecessary
            # or should check if the *bot instance* is somehow capacity-limited.
            # For simplicity, let's check player2 regardless, assuming a human player could be selected as opponent.
            player2_in_human_battle = Battle.objects.filter(
                (Q(player1=player2) | Q(player2=player2)),
                status='active',
                player2_is_ai_controlled=False
            ).exists()
            if player2_in_human_battle:
                 return Response({"error": "Opponent is currently in an active battle against a human."}, status=status.HTTP_400_BAD_REQUEST)
            # --- END MODIFIED BATTLE CHECK ---

            # --- Create Battle based on fight_as_bot flag --- 
            if fight_as_bot:
                 # Start immediately as active, player2 is AI controlled
                print(f"Challenge initiated against {player2.username} AS BOT. Starting immediately.")
                battle = Battle.objects.create(
                    player1=player1, 
                    player2=player2, 
                    status='active', # Start active
                    player2_is_ai_controlled=True # Mark player2 as AI for this battle
                )
                battle.initialize_battle_state() # This also saves the battle
                # Use the full BattleSerializer for the response as the battle is active
                battle_serializer = BattleSerializer(battle, context={'request': request})
                return Response({
                    "message": f"Battle with {player2.username} (as BOT) started immediately!",
                    "battle": battle_serializer.data # Return full battle state
                }, status=status.HTTP_201_CREATED)
            else:
                # Normal challenge: Create the battle as pending
                print(f"Normal challenge initiated against {player2.username}. Status: pending.")
                battle = Battle.objects.create(player1=player1, player2=player2, status='pending')
                # Return the simple serializer data PLUS the battle ID for cancellation
                response_data = BattleListSerializer(battle).data 
                response_data['battle_id'] = battle.id # Add the ID
                return Response(response_data, status=status.HTTP_201_CREATED)
            # --- REMOVE old bot auto-accept logic --- 

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingBattlesView(generics.ListAPIView):
    """Lists battles waiting for the logged-in user's response."""
    serializer_class = BattleListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # --- Auto-delete old pending battles --- 
        time_threshold = timezone.now() - timedelta(minutes=10)
        expired_battles = Battle.objects.filter(
            player2=user, 
            status='pending',
            created_at__lt=time_threshold
        )
        count = expired_battles.count()
        if count > 0:
            expired_battles.delete()
            print(f"[User: {user.username}] Deleted {count} expired pending battle requests older than 10 minutes.")
        # --- End auto-delete --- 

        # Return remaining pending battles for this user
        return Battle.objects.filter(player2=user, status='pending').order_by('-created_at')


class RespondBattleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        battle = get_object_or_404(Battle, pk=pk)
        user = request.user
        serializer = BattleRespondSerializer(data=request.data)

        if battle.player2 != user:
            return Response({"error": "You are not the recipient of this battle request."}, status=status.HTTP_403_FORBIDDEN)

        if battle.status != 'pending':
            return Response({"error": "This battle request is no longer pending."}, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            action = serializer.validated_data['action']
            if action == 'accept':
                 # Check if player1 is now in another active battle
                if Battle.objects.filter(Q(player1=battle.player1) | Q(player2=battle.player1), status='active').exists():
                    battle.status = 'declined' # Auto-decline if initiator started another battle
                    battle.save()
                    return Response({"error": "The challenger is already in another battle. Request declined."}, status=status.HTTP_400_BAD_REQUEST)
                # Check if player2 (acceptor) is now in another active battle
                if Battle.objects.filter(Q(player1=user) | Q(player2=user), status='active').exclude(pk=battle.pk).exists():
                     return Response({"error": "You are already in an active battle."}, status=status.HTTP_400_BAD_REQUEST)

                battle.status = 'active'
                battle.initialize_battle_state() # Sets initial turn/momentum now
                battle_data = BattleSerializer(battle).data
                # TODO: Potentially send a notification to player1 (e.g., via WebSockets)
                return Response({"message": "Battle accepted!", "battle": battle_data}, status=status.HTTP_200_OK)
            else: # action == 'decline'
                battle.status = 'declined'
                battle.save()
                # TODO: Potentially send a notification to player1
                return Response({"message": "Battle declined."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BattleDetailView(generics.RetrieveAPIView):
    """Gets the current state of a specific battle."""
    serializer_class = BattleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Allow user to see details only if they are player1 or player2
        return Battle.objects.filter(Q(player1=user) | Q(player2=user))
        
    # Add this method to pass context
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class ActiveBattleView(views.APIView):
    """Gets the user's current active battle, if any."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        active_battle = Battle.objects.filter(
            (Q(player1=user) | Q(player2=user)),
            status='active'
        ).first()

        if active_battle:
            serializer = BattleSerializer(active_battle, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No active battle found."}, status=status.HTTP_404_NOT_FOUND)


class BattleActionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        battle = get_object_or_404(Battle, pk=pk)
        user = request.user
        serializer = BattleActionSerializer(data=request.data)

        role = battle.get_player_role(user)
        if not role:
            return Response({"error": "You are not part of this battle."}, status=status.HTTP_403_FORBIDDEN)
        if battle.status != 'active':
            return Response({"error": "Battle is not active."}, status=status.HTTP_400_BAD_REQUEST)
        if battle.whose_turn != role:
            return Response({"error": "It's not your turn!"}, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            attack_id = serializer.validated_data["attack_id"]
            if role == 'player1':
                battle_attack_list = battle.battle_attacks_player1
            else: # role == 'player2'
                battle_attack_list = battle.battle_attacks_player2
            try:
                attack = battle_attack_list.get(pk=attack_id)
            except Attack.DoesNotExist:
                return Response({"error": f"Invalid action: Attack ID {attack_id} not available in this battle for {role}."}, status=status.HTTP_400_BAD_REQUEST)

            # --- Apply Player Attack ---
            try:
                _, battle_ended = apply_attack(battle, user, attack)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # --- BEGIN BOT TURN LOGIC --- # REPLACED current_player.is_bot check
            while not battle_ended and battle.status == 'active':
                current_turn_role = battle.whose_turn
                is_player2_ai = battle.player2_is_ai_controlled # Check the battle flag

                # --- Determine if current turn is AI controlled --- 
                is_ai_turn = (is_player2_ai and current_turn_role == 'player2')
                # Add logic here if player1 could also be AI controlled in the future
                # is_ai_turn = (is_player2_ai and current_turn_role == 'player2') or \ 
                #            (battle.player1_is_ai_controlled and current_turn_role == 'player1')

                if not is_ai_turn:
                    break # Exit loop if it's a human's turn

                # --- It's an AI Controlled Turn --- 
                # Determine which player object and attack list to use based on role
                if current_turn_role == 'player1':
                    current_player = battle.player1
                    bot_attack_list = battle.battle_attacks_player1.all()
                else: # player2
                    current_player = battle.player2
                    bot_attack_list = battle.battle_attacks_player2.all()

                print(f"[Battle {battle.id}] AI controlling {current_player.username} (Role: {current_turn_role})...")
                
                if not bot_attack_list:
                    print(f"Warning: AI-controlled player {current_player.username} (Role: {current_turn_role}) in Battle {battle.id} has no attacks. Skipping turn.")
                    original_turn = battle.whose_turn
                    battle.whose_turn = 'player1' if current_turn_role == 'player2' else 'player2'
                    if battle.whose_turn != original_turn:
                        battle.turn_number += 1
                    if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
                    battle.last_turn_summary.append({
                        "source": "system",
                        "text": f"{current_player.username} (AI) has no moves and skips the turn.",
                        "effect_type": "info"
                    })
                    battle.save()
                    break # Exit the loop after skipping

                bot_chosen_attack = random.choice(list(bot_attack_list))
                print(f"  AI chose attack: {bot_chosen_attack.name} (ID: {bot_chosen_attack.id})")

                try:
                    # Apply the AI's attack
                    _, bot_battle_ended = apply_attack(battle, current_player, bot_chosen_attack)
                    battle_ended = bot_battle_ended # Update overall status
                except ValueError as e:
                    print(f"Error during AI ({current_player.username}) turn in Battle {battle.id}: {e}")
                    if not isinstance(battle.last_turn_summary, list): battle.last_turn_summary = []
                    battle.last_turn_summary.append({
                        "source": "system",
                        "text": f"Error processing AI ({current_player.username}) turn: {e}",
                        "effect_type": "error"
                    })
                    original_turn = battle.whose_turn
                    battle.whose_turn = 'player1' if current_turn_role == 'player2' else 'player2'
                    if battle.whose_turn != original_turn:
                        battle.turn_number += 1
                    battle.save()
                    break # Exit the loop on error
            # --- END BOT/AI TURN LOGIC ---

            # --- Respond with final battle state ---
            updated_battle_state = BattleSerializer(battle, context={'request': request}).data
            if battle_ended:
                return Response({
                    "message": "Battle finished!",
                    "battle_state": updated_battle_state
                }, status=status.HTTP_200_OK)
            else:
                message = "Action applied. "
                final_turn_role = battle.whose_turn
                if final_turn_role == role:
                    message += "It's your turn!"
                else:
                    opponent = battle.player1 if final_turn_role == 'player1' else battle.player2
                    message += f"Waiting for {opponent.username}."
                return Response({
                    "message": message,
                    "battle_state": updated_battle_state
                 }, status=status.HTTP_200_OK)
        # Serializer invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConcedeBattleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        battle = get_object_or_404(Battle, pk=pk)
        user = request.user

        role = battle.get_player_role(user)
        if not role:
            return Response({"error": "You are not part of this battle."}, status=status.HTTP_403_FORBIDDEN)

        if battle.status != 'active':
            return Response({"error": "Battle is not active or already finished."}, status=status.HTTP_400_BAD_REQUEST)

        # Determine the winner (the opponent)
        opponent = battle.player2 if role == 'player1' else battle.player1

        # Update battle state
        battle.status = 'finished'
        battle.winner = opponent
        battle.save()

        # --- Award Booster Credits on Concede ---
        conceder = user # The user making the request is the conceder (loser)
        winner = opponent 
        winner_credits_earned = 2
        loser_credits_earned = 1 # Conceder still gets 1 credit

        winner.booster_credits += winner_credits_earned
        conceder.booster_credits += loser_credits_earned
        
        winner.save(update_fields=['booster_credits'])
        conceder.save(update_fields=['booster_credits'])
        print(f"[Battle {battle.id}] Awarded {winner_credits_earned} credits to winner {winner.username}, {loser_credits_earned} credit to conceder {conceder.username}.")
        # --- End Award Credits ---

        # Serialize the final state
        final_state_serializer = BattleSerializer(battle, context={'request': request}) # Pass context

        return Response({
            "message": f"{user.username} conceded. {opponent.username} wins!",
            "final_state": final_state_serializer.data
        }, status=status.HTTP_200_OK)


class GenerateAttacksView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GenerateAttackRequestSerializer # Expects only 'concept' now

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        concept = serializer.validated_data["concept"]
        favorite_attack_ids = serializer.validated_data.get("favorite_attack_ids", []) # Get optional list

        # --- Get Cost from Game Configuration --- 
        game_config = GameConfiguration.objects.first()
        if not game_config:
            # Handle case where config hasn't been created yet
            print("Error: GameConfiguration not found in database.")
            return Response({"error": "Game configuration is missing. Please contact an administrator."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        required_credits = game_config.attack_generation_cost
        # --- End Get Cost ---

        # --- Check Booster Credits --- 
        if user.booster_credits < required_credits:
            return Response(
                {"error": f"Not enough Booster Credits. You need {required_credits}, but only have {user.booster_credits}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # --- End Check --- 

        # --- Fetch and Validate Favorite Attacks --- 
        favorite_attacks = []
        if favorite_attack_ids:
            favorite_attacks = list(user.attacks.filter(id__in=favorite_attack_ids))
            if len(favorite_attacks) != len(favorite_attack_ids):
                invalid_ids = set(favorite_attack_ids) - set(a.id for a in favorite_attacks)
                return Response(
                    {"error": f"One or more favorite attack IDs are invalid or not owned by you: {list(invalid_ids)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            # --- Deduct Credits BEFORE generation attempt --- 
            user.booster_credits -= required_credits
            user.save(update_fields=["booster_credits"])
            print(f"[User: {user.username}] Spent {required_credits} credits attempting booster open. Remaining: {user.booster_credits}.")
            # --- End Deduct --- 
            
            prompt = construct_generation_prompt(concept, favorite_attacks=favorite_attacks)
            llm_response_text = call_gemini_api(prompt)

            if llm_response_text is None:
                 # --- REFUND CREDITS ON FAILURE --- 
                user.booster_credits += required_credits
                user.save(update_fields=["booster_credits"])
                print(f"[User: {user.username}] REFUNDED {required_credits} credits due to Gemini API failure.")
                # --- END REFUND --- 
                return Response({"error": "Failed to get response from generation model."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            try:
                generated_data = json.loads(llm_response_text)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from LLM response: {llm_response_text}")
                # --- REFUND CREDITS ON FAILURE --- 
                user.booster_credits += required_credits
                user.save(update_fields=["booster_credits"])
                print(f"[User: {user.username}] REFUNDED {required_credits} credits due to JSON decode failure.")
                # --- END REFUND --- 
                return Response({"error": "Attack generation failed: Invalid format received."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Validate, sanitize, save, and associate attacks
            created_attacks = process_and_save_generated_attacks(generated_data, user)

            # Note: process_and_save_generated_attacks now raises ValueError if credits were insufficient
            # which is caught below. Credits are already deducted. 
            # No further deduction needed here.
            
            attack_serializer = AttackSerializer(created_attacks, many=True)
            return Response({
                "message": f"Booster opened! {len(created_attacks)} new attacks generated and added to your collection.", 
                "attacks": attack_serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValueError as ve:
            # Specific ValueErrors from process_and_save (like insufficient credits) are caught here
            # Credits were already deducted at the start, so no refund needed for this specific error. 
            # (Unless process_and_save is refactored to not deduct upfront)
            return Response({"error": f"Attack generation failed: {ve}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            print(f"Unhandled error in GenerateAttacksView: {e}")
            traceback.print_exc()
            # --- REFUND CREDITS ON UNEXPECTED FAILURE --- 
            user.booster_credits += required_credits
            user.save(update_fields=["booster_credits"])
            print(f"[User: {user.username}] REFUNDED {required_credits} credits due to unexpected error: {e}.")
            # --- END REFUND --- 
            return Response({"error": "An unexpected error occurred during attack generation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyAttacksListView(generics.ListAPIView):
    """
    Returns a list of attacks owned by the currently authenticated user.
    """
    serializer_class = AttackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter attacks to only those owned by the requesting user."""
        user = self.request.user
        return user.attacks.all()

# --- Add CancelBattleView --- 
class CancelBattleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        battle = get_object_or_404(Battle, pk=pk)
        user = request.user

        # Only player1 can cancel a pending request they sent
        if battle.player1 != user:
            return Response({"error": "You did not initiate this challenge."}, status=status.HTTP_403_FORBIDDEN)

        if battle.status != 'pending':
            return Response({"error": "This battle request is no longer pending and cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete the battle record
        battle.delete()
        print(f"[User: {user.username}] Cancelled pending battle {pk} against {battle.player2.username}.")
        return Response({"message": "Challenge cancelled successfully."}, status=status.HTTP_200_OK)
# --- End CancelBattleView --- 

# --- NEW: Attack Leaderboard View ---
class AttackLeaderboardView(generics.ListAPIView):
    """Provides a leaderboard ranked by attack usage or wins."""
    serializer_class = AttackLeaderboardSerializer
    permission_classes = [permissions.AllowAny] # Leaderboard is public

    def get_queryset(self):
        # Pre-fetch related data for efficiency
        queryset = AttackUsageStats.objects.select_related(
            'attack',
            'attack__creator' # Include creator for username
        ).all() # Correct base queryset

        # Allow sorting via query parameters (e.g., ?sort=wins or ?sort=used)
        # sort_by = self.request.query_params.get('sort', 'used') # Default sort by times_used

        # --- SIMPLIFIED SORTING FOR NOW ---
        # Let's temporarily remove custom sorting to eliminate it as a potential issue
        # We rely on the default ordering in the serializer/model or apply a simple one here
        queryset = queryset.order_by('-times_used') # Simple default ordering
        # --- END SIMPLIFIED SORTING ---

        # Limit the results (e.g., top 50)
        limit = int(self.request.query_params.get('limit', 50))
        return queryset[:limit]
# --- END Attack Leaderboard View ---

# --- NEW: Attack Delete View ---
class AttackDeleteView(views.APIView):
    """
    Allows the creator of an attack to delete it.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        try:
            attack = Attack.objects.get(pk=pk)
        except Attack.DoesNotExist:
            return Response({"error": "Attack not found."}, status=status.HTTP_404_NOT_FOUND)

        # --- Verify Ownership ---
        if attack.creator != request.user:
            return Response({"error": "You do not have permission to modify this attack."}, status=status.HTTP_403_FORBIDDEN)

        # Optional checks for active battle/selection can be added here

        attack_name = attack.name # Get name for logging before removing
        
        # --- Remove Attack from User's Collections, DO NOT DELETE --- 
        request.user.attacks.remove(attack)
        request.user.selected_attacks.remove(attack) # Also remove if selected
        # attack.delete() # <-- REMOVED THIS LINE

        print(f"[User: {request.user.username}] Removed attack '{attack_name}' (ID: {pk}) from their collection.")

        return Response(status=status.HTTP_204_NO_CONTENT)
# --- End AttackDeleteView ---