from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q # For OR queries
import json # For parsing potential JSON output from LLM
import bleach # For sanitizing text output from LLM
import random # For generating random data
from django.conf import settings # <-- Add settings import
import google.generativeai as genai # <-- Add genai import

from .models import Attack, Battle, Script
from users.models import User
from .serializers import (
    AttackSerializer, BattleInitiateSerializer, BattleRespondSerializer,
    BattleActionSerializer, BattleSerializer, BattleListSerializer,
    GenerateAttackRequestSerializer
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
            player1 = request.user

            if player1.id == opponent_id:
                return Response({"error": "You cannot battle yourself."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                player2 = User.objects.get(pk=opponent_id)
            except User.DoesNotExist:
                return Response({"error": "Opponent not found."}, status=status.HTTP_404_NOT_FOUND)

            # Check if an active or pending battle already exists between these users
            existing_battle = Battle.objects.filter(
                (Q(player1=player1, player2=player2) | Q(player1=player2, player2=player1)),
                status__in=['pending', 'active']
            ).first()

            if existing_battle:
                 return Response({"error": "An active or pending battle already exists with this user.", "battle_id": existing_battle.id}, status=status.HTTP_400_BAD_REQUEST)

            # Check if player1 already has an active battle
            if Battle.objects.filter(Q(player1=player1) | Q(player2=player1), status='active').exists():
                 return Response({"error": "You are already in an active battle."}, status=status.HTTP_400_BAD_REQUEST)
             # Check if player2 already has an active battle
            if Battle.objects.filter(Q(player1=player2) | Q(player2=player2), status='active').exists():
                 return Response({"error": "Opponent is already in an active battle."}, status=status.HTTP_400_BAD_REQUEST)


            battle = Battle.objects.create(player1=player1, player2=player2, status='pending')
            battle_serializer = BattleListSerializer(battle) # Use simpler serializer for response
            return Response(battle_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingBattlesView(generics.ListAPIView):
    """Lists battles waiting for the logged-in user's response."""
    serializer_class = BattleListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
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

        # Get user role (player1 or player2)
        role = battle.get_player_role(user)
        if not role:
            return Response({"error": "You are not part of this battle."}, status=status.HTTP_403_FORBIDDEN)

        # Check battle status
        if battle.status != 'active':
            return Response({"error": "Battle is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if it's the user's turn
        if battle.whose_turn != role:
            return Response({"error": "It's not your turn!"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate serializer and attack
        if serializer.is_valid():
            attack_id = serializer.validated_data["attack_id"]
            
            # --- CORRECTED ATTACK VALIDATION ---
            # Get the correct battle-specific attack list based on the user's role
            if role == 'player1':
                battle_attack_list = battle.battle_attacks_player1
            else: # role == 'player2'
                battle_attack_list = battle.battle_attacks_player2

            try:
                # Check if the attack exists in the BATTLE's list for this player
                attack = battle_attack_list.get(pk=attack_id)
            except Attack.DoesNotExist:
                # Use a more specific error message
                return Response({"error": f"Invalid action: Attack ID {attack_id} not available in this battle for {role}."}, status=status.HTTP_400_BAD_REQUEST)
            # --- END CORRECTION ---

            # --- Apply Attack using new logic ---
            try:
                log_entries, battle_ended = apply_attack(battle, user, attack)
            except ValueError as e:
                 # Catch validation errors from apply_attack (e.g., wrong turn - though already checked)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # --- Respond with updated battle state ---
            # The battle object is modified and saved within apply_attack
            # Pass request context to the serializer
            updated_battle_state = BattleSerializer(battle, context={'request': request}).data

            if battle_ended:
                return Response({
                    "message": "Battle finished!",
                    "battle_state": updated_battle_state
                }, status=status.HTTP_200_OK)
            else:
                # Determine message based on whose turn it is now
                message = "Action applied. "
                if battle.whose_turn == role: # Turn didn't switch
                    message += "It's still your turn."
                else: # Turn switched
                    opponent = battle.player1 if role == 'player2' else battle.player2
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

        # --- Check Booster Credits --- 
        required_credits = 6
        if user.booster_credits < required_credits:
            return Response(
                {"error": f"Not enough Booster Credits. You need {required_credits}, but only have {user.booster_credits}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # --- End Check --- 

        # --- Fetch and Validate Favorite Attacks --- 
        favorite_attacks = []
        if favorite_attack_ids:
            # Ensure the user actually owns these attacks
            # The serializer should have already validated max_length=6
            favorite_attacks = list(user.attacks.filter(id__in=favorite_attack_ids))
            if len(favorite_attacks) != len(favorite_attack_ids):
                 # Find which IDs were invalid (either non-existent or not owned by user)
                invalid_ids = set(favorite_attack_ids) - set(a.id for a in favorite_attacks)
                return Response(
                    {"error": f"One or more favorite attack IDs are invalid or not owned by you: {list(invalid_ids)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        # --- End Fetch --- 

        try:
            # Pass validated favorite attacks (if any) to the prompt constructor
            prompt = construct_generation_prompt(concept, favorite_attacks=favorite_attacks)
            llm_response_text = call_gemini_api(prompt)

            if llm_response_text is None:
                return Response({"error": "Failed to get response from generation model."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            try:
                generated_data = json.loads(llm_response_text)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from LLM response: {llm_response_text}")
                return Response({"error": "Attack generation failed: Invalid format received."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Validate, sanitize, save, and associate attacks
            created_attacks = process_and_save_generated_attacks(generated_data, user)

            # --- Deduct Credits on Success --- 
            user.booster_credits -= required_credits
            user.save(update_fields=["booster_credits"])
            print(f"[User: {user.username}] Spent {required_credits} credits opening booster. Remaining: {user.booster_credits}.")
            # --- End Deduct --- 

            # Serialize the newly created attacks for the response
            attack_serializer = AttackSerializer(created_attacks, many=True)
            return Response({
                "message": f"Booster opened! {len(created_attacks)} new attacks generated and added to your collection.", 
                "attacks": attack_serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValueError as ve:
            return Response({"error": f"Attack generation failed: {ve}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            print(f"Unhandled error in GenerateAttacksView: {e}")
            traceback.print_exc()
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