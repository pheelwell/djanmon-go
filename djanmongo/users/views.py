from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import UserRegisterSerializer, UserProfileSerializer, BasicUserSerializer, UserSerializer
from game.models import Attack # Import Attack model

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegisterSerializer

class UserProfileView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user # Return the logged-in user's profile

class UserListView(generics.ListAPIView):
    """Lists users available for battling (excluding self)."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BasicUserSerializer # Use a simpler serializer for lists

    def get_queryset(self):
        # Exclude the requesting user from the list
        return User.objects.exclude(pk=self.request.user.pk).order_by('username')

# --- Add UserSelectedAttacksUpdateView ---
class UserSelectedAttacksUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer # Use UserSerializer for response

    def put(self, request, *args, **kwargs):
        user = request.user
        print(f"--- DEBUG: Received data for user {user.username}: {request.data} (Type: {type(request.data)}) ---")
        
        # --- Updated data extraction ---
        if not isinstance(request.data, dict) or 'attack_ids' not in request.data:
             return Response({"detail": "Invalid data format. Expected a dictionary with an 'attack_ids' key."}, status=status.HTTP_400_BAD_REQUEST)

        attack_ids = request.data.get('attack_ids') # Extract the list from the dictionary

        # --- Check if the extracted value is actually a list ---
        if not isinstance(attack_ids, list):
            return Response({"detail": "Invalid data format. 'attack_ids' must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        # --- Existing validation continues from here ---
        # Basic validation (e.g., max 6 attacks)
        if len(attack_ids) > 6:
            return Response({"detail": "Cannot select more than 6 attacks."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate IDs and fetch Attack objects
        try:
            selected_attacks = []
            # Ensure all provided IDs correspond to attacks the user actually knows
            known_attack_ids = set(user.attacks.values_list('id', flat=True))
            valid_ids = []
            invalid_ids = []

            for attack_id in attack_ids:
                if not isinstance(attack_id, int):
                     return Response({"detail": f"Invalid attack ID type: {attack_id}. Expected integer."}, status=status.HTTP_400_BAD_REQUEST)
                 
                if attack_id in known_attack_ids:
                    valid_ids.append(attack_id)
                else:
                    invalid_ids.append(attack_id)
            
            if invalid_ids:
                 return Response({"detail": f"Invalid or unknown attack IDs provided: {invalid_ids}. User may not have learned these attacks."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the valid Attack objects in the desired order
            selected_attacks = list(Attack.objects.filter(id__in=valid_ids))
             # Re-order based on input list order if necessary (preserves selection order)
            selected_attacks.sort(key=lambda x: valid_ids.index(x.id))

        except Attack.DoesNotExist:
             # This case is less likely now due to the pre-check, but good practice
             return Response({"detail": "One or more selected attacks not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e: # Catch other potential errors during fetch/validation
             print(f"Error fetching attacks: {e}") # Log for debugging
             return Response({"detail": "Error processing attack selection."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update the user's selected attacks
        # Using set() is efficient for M2M relationships
        user.selected_attacks.set(selected_attacks)
        # No need to call user.save() for M2M changes via set()

        # Return the updated user profile
        serializer = self.serializer_class(user, context={'request': request})
        return Response(serializer.data)
