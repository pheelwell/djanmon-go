from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q # For OR queries

from .models import Attack, Battle
from users.models import User
from .serializers import (
    AttackSerializer, BattleInitiateSerializer, BattleRespondSerializer,
    BattleActionSerializer, BattleSerializer, BattleListSerializer
)
from .battle_logic import apply_attack # Import the new logic function


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
            attack_id = serializer.validated_data['attack_id']
            try:
                attack = user.selected_attacks.get(pk=attack_id)
            except Attack.DoesNotExist:
                return Response({"error": "Invalid attack: Attack not learned or not selected for battle."}, status=status.HTTP_400_BAD_REQUEST)

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

        # Serialize the final state
        final_state_serializer = BattleSerializer(battle)

        return Response({
            "message": f"{user.username} conceded. {opponent.username} wins!",
            "final_state": final_state_serializer.data
        }, status=status.HTTP_200_OK)