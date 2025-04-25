import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient from '@/services/api'; // Adjust path if needed
import { logoutUser as apiLogoutUser } from '@/services/api'; // Import specific API function
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
  // --- State ---
  // Remove token state
  // const accessToken = ref(localStorage.getItem('accessToken') || null);
  // const refreshToken = ref(localStorage.getItem('refreshToken') || null);
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null')); // Keep user state
  const loginError = ref(null);
  const registerError = ref(null);
  const isUpdatingMoveset = ref(false);
  const movesetUpdateError = ref(null);
  const isUpdatingStats = ref(false);
  const statsUpdateError = ref(null);

  // --- Getters ---
  // Update isAuthenticated to check for user object instead of token
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
      // No tokens to store
      // accessToken.value = response.data.access;
      // refreshToken.value = response.data.refresh;
      // localStorage.setItem('accessToken', accessToken.value);
      // localStorage.setItem('refreshToken', refreshToken.value);
      
      // Backend now returns user data on successful login
      user.value = response.data;
      localStorage.setItem('user', JSON.stringify(user.value)); 
      // No need to explicitly call fetchUserProfile here anymore
      // await fetchUserProfile(); 
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
      // apiClient now handles auth via cookies + csrf
      const response = await apiClient.get('/users/me/');
      user.value = response.data;
      localStorage.setItem('user', JSON.stringify(user.value));
    } catch (error) {
      console.error('Failed to fetch user profile:', error.response?.data || error.message);
      // If fetching profile fails (e.g., 401/403), it implies no valid session.
      // Clear local user state.
      user.value = null; // Clear user state
      localStorage.removeItem('user'); // Clear stored user data
      // The global response interceptor might also trigger logout/redirect
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
        
        // Redirect to login page
        router.push({ name: 'login' }); 
    }
  }

  // --- Refresh Token Logic (Placeholder) --- 
  // REMOVE THIS SECTION
  // async function refreshTokenIfNeeded() { ... }

  // --- Initialization --- 
  // Remove direct fetchUserProfile call here. Let app initialization handle it if needed.
  // if (accessToken.value) {
  //   fetchUserProfile();
  // }

  // --- Remove Store-Specific Interceptors --- 
  // Remove the JWT request interceptor previously added here.
  // The global interceptors in api.js handle session/CSRF now.
  // apiClient.interceptors.request.use(config => { ... });

  // Remove the response interceptor previously added here.
  // A global one might still be useful in api.js or main.js.
  // apiClient.interceptors.response.use(response => response, error => { ... });

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
    updateUserProfile
  };
}); 