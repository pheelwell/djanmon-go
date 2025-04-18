from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import UserRegisterSerializer, UserProfileSerializer, BasicUserSerializer, UserSerializer, UserStatsSerializer, LeaderboardUserSerializer
from game.models import Attack # Import Attack model

class RegisterView(generics.CreateAPIView):
    """Handles user registration.

    Allows any user to create a new account via a POST request.
    Uses the `UserRegisterSerializer` for validation and creation.
    Endpoint: `/api/users/register/` (typically)
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegisterSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieves or updates the profile of the currently authenticated user.
    
    Responds to GET requests with the logged-in user's data,
    serialized using `UserSerializer`.
    Responds to PUT/PATCH requests to update user data (including base stats).
    Requires authentication.
    Endpoint: `/api/users/profile/` (typically)
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        """Returns the currently authenticated user."""
        return self.request.user # Return the logged-in user's profile

class UserListView(generics.ListAPIView):
    """Lists users available for battling (excluding the requester).
    
    Responds to GET requests with a list of users (excluding the one making
    the request), serialized using `BasicUserSerializer`.
    Used for populating opponent lists.
    Requires authentication.
    Endpoint: `/api/users/` (typically)
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BasicUserSerializer # Use a simpler serializer for lists

    def get_queryset(self):
        """Returns a queryset of all users excluding the requesting user."""
        # Exclude the requesting user from the list
        return User.objects.exclude(pk=self.request.user.pk).order_by('username')

# --- Add UserSelectedAttacksUpdateView ---
class UserSelectedAttacksUpdateView(APIView):
    """Updates the selected attacks for the authenticated user.

    Handles PUT requests to update the `selected_attacks` ManyToMany field.
    Expects data in the format: `{"attack_ids": [id1, id2, ...]}`.
    Validates that the user knows the attacks and the list has <= 6 IDs.
    Requires authentication.
    Endpoint: `/api/users/profile/selected-attacks/` (typically)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer # Use UserSerializer for response

    def put(self, request, *args, **kwargs):
        """Handles the PUT request to update selected attacks."""
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

# --- NEW: Leaderboard Views ---

# --- MODIFIED: UserStatsView for GET and PATCH --- 
class UserStatsView(generics.RetrieveUpdateAPIView):
    """Retrieves or updates detailed battle statistics/base stats for the logged-in user.

    GET: Returns user's win/loss record, etc. (UserStatsSerializer).
    PATCH/PUT: Updates user's base hp, attack, defense, speed (UserStatsUpdateSerializer).
    Requires authentication.
    Endpoint: `/api/users/me/stats/` 
    """
    permission_classes = (permissions.IsAuthenticated,)
    # serializer_class determined by get_serializer_class

    def get_object(self):
        """Returns the currently authenticated user."""
        return self.request.user

    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ('PUT', 'PATCH'):
            # Import locally to potentially avoid circular dependency issues
            from .serializers import UserStatsUpdateSerializer 
            return UserStatsUpdateSerializer
        # For GET requests
        from .serializers import UserStatsSerializer
        return UserStatsSerializer

    # Optional: Override perform_update for additional logic after successful update
    # def perform_update(self, serializer):
    #     # Add any post-save logic here if needed
    #     super().perform_update(serializer)
    #     # e.g., send a signal, log the update

class LeaderboardView(generics.ListAPIView):
    """Provides a public leaderboard of users.

    Responds to GET requests with a list of all users, serialized using
    `LeaderboardUserSerializer` (includes username, level, wins, selected attacks).
    Currently fetches all users; sorting/ranking logic might be handled client-side
    or refined here later if needed.
    Allows any user (no authentication required).
    Endpoint: `/api/leaderboard/` (typically)
    """
    # Allow any user (authenticated or not) to view the leaderboard
    permission_classes = (permissions.AllowAny,)
    serializer_class = LeaderboardUserSerializer

    def get_queryset(self):
        # Fetch all users, annotate with win counts, and order by wins descending
        # Note: Annotating directly might be more efficient for large user bases
        # than relying solely on the serializer method field if sorting is needed.
        # However, for simplicity and consistency with the serializer, we'll 
        # fetch all users and let the frontend sort or paginate if needed.
        # If performance becomes an issue, revisit this with annotation.
        # queryset = User.objects.annotate(win_count=Count('won_battles')).order_by('-win_count', 'username')
        
        # Simpler approach: Get all users, rely on serializer methods for stats.
        # Frontend will handle sorting/display.
        return User.objects.all().order_by('username') # Default order, can be overridden
