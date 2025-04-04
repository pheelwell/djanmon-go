import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient from '@/services/api'; // Adjust path if needed
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
  // --- State --- 
  const accessToken = ref(localStorage.getItem('accessToken') || null);
  const refreshToken = ref(localStorage.getItem('refreshToken') || null);
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
  const loginError = ref(null);
  const registerError = ref(null);
  const isUpdatingMoveset = ref(false);
  const movesetUpdateError = ref(null);

  // --- Getters --- 
  const isAuthenticated = computed(() => !!accessToken.value);
  const currentUser = computed(() => user.value);

  // --- Actions --- 

  async function login(username, password) {
    loginError.value = null; // Reset error
    try {
      const response = await apiClient.post('/users/login/', {
        username,
        password,
      });
      accessToken.value = response.data.access;
      refreshToken.value = response.data.refresh;
      localStorage.setItem('accessToken', accessToken.value);
      localStorage.setItem('refreshToken', refreshToken.value);
      // Fetch user profile after successful login
      await fetchUserProfile(); 
      return true;
    } catch (error) {
      console.error('Login failed:', error.response?.data || error.message);
      loginError.value = error.response?.data || { detail: 'Login failed. Please check credentials.' };
      logout(); // Clear any potentially partially set state
      return false;
    }
  }

  async function register(username, password, password2, email = '') {
    registerError.value = null; // Reset error
    try {
      await apiClient.post('/users/register/', {
        username,
        password,
        password2,
        email, // Include email if provided
      });
      // Optionally log the user in automatically after registration
      // await login(username, password);
      return true;
    } catch (error) {
      console.error('Registration failed:', error.response?.data || error.message);
      registerError.value = error.response?.data || { detail: 'Registration failed. Please check your input.' };
      return false;
    }
  }

  async function fetchUserProfile() {
    if (!accessToken.value) return; // Don't fetch if not logged in

    try {
      // Add Authorization header dynamically for this request
      const response = await apiClient.get('/users/me/', {
        headers: { Authorization: `Bearer ${accessToken.value}` }
      });
      user.value = response.data;
      localStorage.setItem('user', JSON.stringify(user.value));
    } catch (error) {
      console.error('Failed to fetch user profile:', error.response?.data || error.message);
      // Handle error, maybe token expired? Consider logout or refresh token logic here
      if (error.response && error.response.status === 401) {
         // Attempt refresh token or logout
         // console.log('Token might be expired, attempting refresh or logout...');
         logout(); // Simple logout for now
      }
    }
  }

  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    // Optionally redirect to login page using router
    // import router from '@/router'; // Be careful with imports inside functions
    // router.push('/login');
  }

  // --- Refresh Token Logic (Placeholder) --- 
  // async function refreshTokenIfNeeded() { ... }

  // --- Initialization --- 
  // Attempt to fetch user profile if tokens exist on store initialization
  if (accessToken.value) {
    fetchUserProfile();
  }

  // Add interceptor to apiClient to automatically add auth header
  apiClient.interceptors.request.use(config => {
    if (accessToken.value) {
      config.headers.Authorization = `Bearer ${accessToken.value}`;
    }
    return config;
  }, error => {
    return Promise.reject(error);
  });

  // Add response interceptor to handle 401 errors globally
  apiClient.interceptors.response.use(
    response => response, // Simply return successful responses
    error => {
      // Check if the error is a 401 Unauthorized
      if (error.response && error.response.status === 401) {
        // Check if the failed request was *not* for login or token refresh itself,
        // to avoid potential logout loops on failed login/refresh attempts.
        const originalRequestUrl = error.config.url;
        if (!originalRequestUrl.includes('/users/login')) { // Add refresh check if implemented
            console.log('API request unauthorized (401). Logging out.');
            logout();
             // Optionally, redirect here as well, though logout already handles it conceptually
             // router.push({ name: 'login' });
        }
      }
      // Important: Return the error so other error handling can occur if needed
      return Promise.reject(error);
    }
  );

  // NEW ACTION: Update selected attacks
  async function updateSelectedAttacks(attackIds) {
    if (!isAuthenticated.value) return;

    isUpdatingMoveset.value = true;
    movesetUpdateError.value = null;

    try {
      const response = await apiClient.put('/users/me/selected-attacks/', { attack_ids: attackIds });
      // Update the currentUser state with the full profile returned by the backend
      user.value = response.data; 
      localStorage.setItem('user', JSON.stringify(response.data)); // Update local storage too
      // Optionally show a success message?
    } catch (error) {
      console.error('Failed to update selected attacks:', error.response?.data || error.message);
      movesetUpdateError.value = error.response?.data || {'detail': 'Could not save moveset.'};
      // Optionally re-fetch profile to revert optimistic update if needed?
      // await fetchUserProfile();
    } finally {
      isUpdatingMoveset.value = false;
    }
  }

  return {
    // State refs
    accessToken,
    refreshToken,
    user,
    loginError,
    registerError,
    isUpdatingMoveset,
    movesetUpdateError,

    // Getters (computed)
    isAuthenticated,
    currentUser,

    // Actions
    login,
    logout,
    register,
    fetchUserProfile,
    updateSelectedAttacks,
  };
}); 