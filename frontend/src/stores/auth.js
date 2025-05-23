import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient from '@/services/api'; // Adjust path if needed
import { logoutUser as apiLogoutUser, fetchCsrfToken } from '@/services/api'; // Import specific API function and fetchCsrfToken
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
  // --- State ---
  // Tokens are handled by HttpOnly cookies now
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
  const loginError = ref(null);
  const registerError = ref(null);
  const isUpdatingMoveset = ref(false);
  const movesetUpdateError = ref(null);
  const isUpdatingStats = ref(false);
  const statsUpdateError = ref(null);
  const actionError = ref(null);
  const actionSuccessMessage = ref(null);

  // --- Getters ---
  // isAuthenticated checks for the presence of the user object
  const isAuthenticated = computed(() => !!user.value);
  const currentUser = computed(() => user.value);

  // --- Actions ---

  async function login(username, password) {
    loginError.value = null;
    try {
      const response = await apiClient.post('/users/login/', {
        username,
        password,
      });
      // No tokens to store locally
      
      // Backend now returns user data on successful login
      user.value = response.data;
      localStorage.setItem('user', JSON.stringify(user.value)); 
      
      // *** FETCH CSRF TOKEN AFTER LOGIN ***
      await fetchCsrfToken(); 
      
      return true;
    } catch (error) {
      console.error('Login failed:', error.response?.data || error.message);
      loginError.value = error.response?.data || { detail: 'Login failed. Please check credentials.' };
      // Clear user state on failed login attempt
      user.value = null;
      localStorage.removeItem('user');
      return false;
    }
  }

  async function register(username, password, password2, email = '') {
    registerError.value = null; 
    try {
      await apiClient.post('/users/register/', {
        username,
        password,
        password2,
        email, 
      });
      // Don't auto-login, let user log in separately
      // await login(username, password);
      return true;
    } catch (error) {
      console.error('Registration failed:', error.response?.data || error.message);
      registerError.value = error.response?.data || { detail: 'Registration failed. Please check your input.' };
      return false;
    }
  }

  async function fetchUserProfile() {
    // Fetching profile is still useful on app load if a session exists,
    // or after certain actions to get updated data.
    try {
      // apiClient handles auth via cookies + csrf
      const response = await apiClient.get('/users/me/');
      user.value = response.data;
      localStorage.setItem('user', JSON.stringify(user.value));
      
      // *** FETCH CSRF TOKEN AFTER PROFILE FETCH ***
      await fetchCsrfToken(); 
      
    } catch (error) {
      console.error('Failed to fetch user profile:', error.response?.data || error.message);
      // If fetching profile fails (e.g., 401/403), it implies no valid session.
      // Clear local user state.
      user.value = null; // Clear user state
      localStorage.removeItem('user'); // Clear stored user data
      // The global response interceptor might also trigger logout/redirect

      router.push({ name: 'login' }); 
    }
  }

  async function logout() {
    try {
        await apiLogoutUser(); // Call the specific API function for logout
    } catch (error) {
        console.error("Logout API call failed:", error.response?.data || error.message);
        // Still clear local state even if API call fails
    } finally {
        // Clear local state regardless of API call success/failure
        // accessToken.value = null;
        // refreshToken.value = null;
        user.value = null;
        // localStorage.removeItem('accessToken');
        // localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        
        // TODO: Ideally, clear the stored csrfToken in api.js as well.
        // This requires exporting a setter/clearer function from api.js
        // or managing the token within this store (more complex).
        // For now, the token will remain until the next fetch/page load.

        router.push({ name: 'login' }); 
    }
  }

  // --- Existing Actions (Keep as is, they use apiClient which now handles auth) ---
  async function updateSelectedAttacks(attackIds) {
    if (!isAuthenticated.value) return;

    isUpdatingMoveset.value = true;
    movesetUpdateError.value = null;

    try {
      const response = await apiClient.put('/users/me/selected-attacks/', { attack_ids: attackIds });
      user.value = response.data; 
      localStorage.setItem('user', JSON.stringify(response.data));
    } catch (error) {
      console.error('Failed to update selected attacks:', error.response?.data || error.message);
      movesetUpdateError.value = error.response?.data || {'detail': 'Could not save moveset.'};
    } finally {
      isUpdatingMoveset.value = false;
    }
  }

  async function updateUserStats(statsData) {
    if (!isAuthenticated.value) return;

    isUpdatingStats.value = true;
    statsUpdateError.value = null;

    try {
      const response = await apiClient.patch('/users/me/stats/', statsData);
      if (user.value && response.data) {
          for (const key in response.data) {
              if (Object.hasOwnProperty.call(response.data, key) && key in user.value) {
                  user.value[key] = response.data[key];
              }
          }
          localStorage.setItem('user', JSON.stringify(user.value)); 
      } else {
           console.warn("Could not merge stats: user state or response data missing.");
           await fetchUserProfile(); 
      }
    } catch (error) {
      console.error('Failed to update user stats:', error.response?.data || error.message);
      statsUpdateError.value = error.response?.data || {'detail': 'Could not save stats.'};
    } finally {
      isUpdatingStats.value = false;
    }
  }

  async function updateUserProfile(profileData) {
    if (!isAuthenticated.value) return false; // Or throw error?

    try {
      const response = await apiClient.patch('/users/me/', profileData);
      user.value = response.data; 
      localStorage.setItem('user', JSON.stringify(response.data));
      return true;
    } catch (error) {
      console.error('Failed to update user profile:', error.response?.data || error.message);
      return false;
    }
  }

  async function deleteAttack(attackId) {
      console.log('Attempting to delete attack with ID:', attackId); // Add log
      if (!attackId) {
          throw new Error("Attack ID is required for deletion.");
      }
      try {
          // Ensure the API path matches your Django urls.py
          const response = await apiClient.delete(`/game/attacks/${attackId}/delete/`);
          console.log('API delete response:', response); // Log response

          // Update local state
          if (user.value && user.value.attacks) {
              const attackIndex = user.value.attacks.findIndex(a => a && a.id === attackId);
              if (attackIndex > -1) {
                  user.value.attacks.splice(attackIndex, 1);
                  console.log(`Attack ${attackId} removed from local user.attacks.`);
              }
          }
          if (user.value && user.value.selected_attacks) {
               const selectedIndex = user.value.selected_attacks.findIndex(a => a && a.id === attackId);
              if (selectedIndex > -1) {
                  user.value.selected_attacks.splice(selectedIndex, 1);
                   console.log(`Attack ${attackId} removed from local user.selected_attacks.`);
              }
          }
          localStorage.setItem('user', JSON.stringify(user.value)); // Re-save user state

          // actionSuccessMessage.value = 'Attack deleted successfully!'; // Set success message if defined
          return { success: true };

      } catch (error) {
           console.error("Error deleting attack in store action:", error);
           const errorMsg = error.response?.data?.error || error.message || 'Failed to delete attack.';
           // actionError.value = errorMsg; // Set error message if defined
           throw new Error(errorMsg);
    }
  }

  // --- NEW: Toggle Favorite Status --- 
  async function toggleAttackFavorite(attackId) {
    if (!attackId) return;
    actionError.value = null;
    actionSuccessMessage.value = null;
    const currentAttack = currentUser.value?.attacks?.find(a => a.id === attackId);
    if (!currentAttack) {
      actionError.value = 'Attack not found in user profile.';
      throw new Error(actionError.value);
    }
    const newFavoriteStatus = !currentAttack.is_favorite;

    try {
      const response = await apiClient.patch(`/game/attacks/${attackId}/favorite/`, { 
        is_favorite: newFavoriteStatus
      });
      // Update the attack in the user's list locally
      const attackIndex = currentUser.value.attacks.findIndex(a => a.id === attackId);
      if (attackIndex !== -1) {
        currentUser.value.attacks[attackIndex] = response.data; 
      }
      // Update selected attacks too if it's there
      const selectedIndex = currentUser.value.selected_attacks.findIndex(a => a.id === attackId);
      if (selectedIndex !== -1) {
        currentUser.value.selected_attacks[selectedIndex] = response.data;
      }
      actionSuccessMessage.value = `Attack "${response.data.name}" ${newFavoriteStatus ? 'favorited' : 'unfavorited'}.`;
      setTimeout(() => actionSuccessMessage.value = null, 3000); // Clear after 3s
      return response.data; // Return updated attack
    } catch (error) {
      console.error('Failed to toggle favorite:', error.response?.data || error.message);
      actionError.value = error.response?.data?.detail || 'Could not update favorite status.';
      // Optionally revert optimistic update here if needed
      throw error;
    }
  }

  // --- END NEW ---

  function clearMessages() {
    actionError.value = null;
    actionSuccessMessage.value = null;
  }

  return {
    // State refs (Tokens removed)
    user,
    loginError,
    registerError,
    isUpdatingMoveset,
    movesetUpdateError,
    isUpdatingStats,
    statsUpdateError,

    // Getters (isAuthenticated logic updated)
    isAuthenticated,
    currentUser,

    // Actions (Login/Logout updated, fetchUserProfile potentially called differently)
    login,
    logout,
    register,
    fetchUserProfile,
    updateSelectedAttacks,
    updateUserStats,
    updateUserProfile,
    deleteAttack,
    toggleAttackFavorite,
    clearMessages
  };
}); 