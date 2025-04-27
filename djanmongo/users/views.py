from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login, logout # <-- Add imports
from django.middleware.csrf import get_token # <-- Add import

from .models import User
from .serializers import UserRegisterSerializer, UserProfileSerializer, BasicUserSerializer, UserSerializer, UserStatsSerializer, LeaderboardUserSerializer, UserStatsUpdateSerializer
from game.models import Attack, GameConfiguration # Import Attack model and GameConfiguration

# --- NEW: Import services ---
from .services import construct_profile_pic_prompt_for_llm, call_llm_for_profile_prompt, generate_profile_image_with_pixellab
# -------------------------

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
        # Update: We need server-side sorting for the leaderboard based on stats.
        # This requires annotation or careful ORM filtering/sorting.
        # Simple annotation example (requires PostgreSQL for JSONField key lookups efficiently):
        # from django.db.models.functions import Cast, Coalesce
        # from django.db.models import IntegerField, Value
        # queryset = User.objects.annotate(
        #     human_wins=Coalesce(Cast(KeyTextTransform('wins_vs_human', 'stats'), IntegerField()), Value(0))
        # ).order_by('-human_wins', 'username')
        
        # Simpler approach: Get all users, rely on serializer methods for stats.
        # Let's SORT on the backend now. This might be slow without indexing/annotation.
        # We'll sort by human wins descending primarily, then username.
        # Note: Sorting on JSONField keys directly is database-dependent and can be slow.
        # Consider creating dedicated fields or using annotations for performance.
        users = sorted(
            list(User.objects.all()), 
            key=lambda u: (
                u.stats.get('wins_vs_human', 0) if isinstance(u.stats, dict) else 0, 
                u.username
            ),
            reverse=True # Sort descending by wins_vs_human
        )
        return users

# --- NEW: CSRF Token View ---
class CsrfTokenView(APIView):
    permission_classes = [permissions.AllowAny] # Anyone can get the token

    def get(self, request, *args, **kwargs):
        # Ensure a CSRF cookie is set for the session if it doesn't exist
        # get_token() also handles setting the cookie if needed.
        csrf_token = get_token(request)
        return Response({'csrfToken': csrf_token})
# --- END CSRF Token View ---

# --- NEW: View for Profile Picture Generation ---
class GenerateProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer # To return updated user data

    def post(self, request, *args, **kwargs):
        user = request.user

        # 1. Check Credits
        try:
            config = GameConfiguration.objects.first()
            # TODO: Add profile_pic_generation_cost field to GameConfiguration model if needed
            generation_cost = getattr(config, 'profile_pic_generation_cost', 1) 
        except Exception:
            generation_cost = 1 # Fallback if config fails

        if user.booster_credits < generation_cost:
            return Response(
                {"detail": f"Insufficient credits. Need {generation_cost}, have {user.booster_credits}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Deduct Credits (Consider transaction if needed)
        try:
            user.booster_credits -= generation_cost
            user.save(update_fields=["booster_credits"])
            print(f"[View] Deducted {generation_cost} credits from {user.username} for profile pic. New balance: {user.booster_credits}")
        except Exception as e:
             print(f"[View Error] Failed to deduct credits for user {user.username}: {e}")
             return Response({"detail": "Error processing credits."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Generate Prompt
        try:
            # Fetch selected attacks (limit for context)
            selected_attacks = list(user.selected_attacks.all()[:6])
            llm_input_prompt = construct_profile_pic_prompt_for_llm(user.username, selected_attacks)
            generated_image_prompt = call_llm_for_profile_prompt(llm_input_prompt) # Blocking call - consider async/celery for production
        except Exception as e:
             print(f"[View Error] LLM prompt generation failed: {e}")
             # Optionally restore credits here if needed
             return Response({"detail": "Failed to generate image prompt."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not generated_image_prompt:
            # Optionally restore credits
            return Response({"detail": "LLM did not return a valid prompt."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Generate Image
        try:
            # Service now returns base64 data
            base64_image_data = generate_profile_image_with_pixellab(generated_image_prompt) 
        except Exception as e:
             print(f"[View Error] Pixel Lab image generation failed: {e}")
             # Optionally restore credits
             return Response({"detail": "Failed to generate image."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not base64_image_data:
             # Optionally restore credits
            return Response({"detail": "Image generation service failed to return image data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Save Base64 and Prompt to User
        try:
            user.profile_picture_base64 = base64_image_data # Save base64 data
            user.profile_picture_prompt = generated_image_prompt
            # Update the correct fields
            user.save(update_fields=["profile_picture_base64", "profile_picture_prompt"])
        except Exception as e:
             print(f"[View Error] Failed to save image data for user {user.username}: {e}")
             # Credits already deducted, log error but maybe still return success? Or specific error?
             return Response({"detail": "Generated image but failed to save data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 6. Return Updated User Data
        serializer = self.serializer_class(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
# --- END NEW VIEW --- 

# --- Session-based Login View ---
class LoginView(APIView):
    permission_classes = [permissions.AllowAny] # Allow anyone to access the login endpoint
    serializer_class = UserSerializer # To serialize the user data on success

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Authentication successful, log the user in to establish session
            login(request, user) 
            # 'login' handles setting the sessionid cookie in the response

            # Serialize and return user data (frontend expects this)
            serializer = self.serializer_class(user, context={'request': request}) 
            return Response(serializer.data) 
        else:
            # Authentication failed
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
# --- END Login View ---

# --- MODIFIED Logout View ---
class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,) # Ensure user is logged in

    def post(self, request, *args, **kwargs):
        # Use Django's logout function to clear the session
        logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
# --- END Logout View ---
