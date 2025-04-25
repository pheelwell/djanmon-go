import axios from 'axios';

// Determine the base URL based on the environment
let baseURL;

if (import.meta.env.VITE_API_BASE_URL) {
    // 1. Use environment variable if provided (Primary for production)
    baseURL = import.meta.env.VITE_API_BASE_URL;
    console.log(`Using VITE_API_BASE_URL: ${baseURL}`);
} else if (import.meta.env.DEV) {
    // 2. Fallback for local development (if no env var set)
    baseURL = 'http://localhost:8000/api'; 
    console.log(`Using development fallback baseURL: ${baseURL}`);
} else {
    // 3. Fallback for production if no env var set (assuming relative path)
    baseURL = window.location.origin + '/api'; 
    console.log(`Using production relative path fallback baseURL: ${baseURL}`);
}

const apiClient = axios.create({
  baseURL: baseURL,
  withCredentials: true, // Keep this for session cookies
  // headers: { // You might set common headers here if needed
  //   'Content-Type': 'application/json',
  // }
});

// Optional: Add interceptors for things like adding auth tokens to requests
// or handling global errors (like 401 Unauthorized for auto-logout)

// --- REMOVE JWT Interceptor Example ---
// apiClient.interceptors.request.use(
//   config => {
//     const token = localStorage.getItem('accessToken'); 
//     if (token) {
//       config.headers['Authorization'] = `Bearer ${token}`;
//     }
//     return config;
//   },
//   error => {
//     return Promise.reject(error);
//   }
// );

// --- CSRF Token Handling --- 
let csrfToken = null; // Variable to store the fetched token

// Function to fetch CSRF token (Call this early in your app)
export async function fetchCsrfToken() {
    try {
        console.log('Fetching CSRF token...');
        // Use the apiClient instance itself, credentials will be sent
        const response = await apiClient.get('/users/csrf-token/'); 
        csrfToken = response.data.csrfToken;
        console.log('CSRF token fetched successfully.');
    } catch (error) {
        console.error('Failed to fetch CSRF token:', error.response?.data || error.message);
        csrfToken = null; // Reset on failure
    }
}

// --- Axios Interceptor --- 
apiClient.interceptors.request.use(config => {
  // Add CSRF token header for non-safe methods using the fetched token
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(config.method.toUpperCase())) {
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
      console.log('Attached X-CSRFToken header from fetched token.');
    } else {
        console.warn('CSRF token not available for non-safe request.');
        // Optionally: You could try to fetch the token here again before proceeding,
        // or queue the request, but simply warning might be sufficient initially.
    }
  }
  return config;
});

// --- END CSRF Interceptor ---

// Example Response Interceptor (Handle 401)
// apiClient.interceptors.response.use(
//   response => response,
//   error => {
//     if (error.response && error.response.status === 401) {
//       // Handle unauthorized access, e.g., redirect to login, clear tokens
//       console.error("Unauthorized access - Redirecting to login");
//       // authStore.logout(); // Assuming you have an auth store action
//       // router.push('/login'); // Assuming you have access to the router
//     }
//     return Promise.reject(error);
//   }
// );

// Add interceptors for auth tokens and error handling
// apiClient.interceptors.request.use(/* ... request interceptor ... */);
// apiClient.interceptors.response.use(/* ... response interceptor ... */);

export default apiClient;

// --- User/Auth Related --- 
export const loginUser = (credentials) => apiClient.post('/users/login/', credentials);
export const registerUser = (userData) => apiClient.post('/users/register/', userData);
export const logoutUser = () => apiClient.post('/users/logout/');
export const fetchUserProfile = () => apiClient.get('/users/me/');
export const updateUserSelectedAttacks = (attackIds) => apiClient.put('/users/me/selected-attacks/', { attack_ids: attackIds }); // Send as object
export const fetchUserList = () => apiClient.get('/users/'); // Fetch list of potential opponents
export const updateUserStats = (statsData) => apiClient.patch('/users/me/stats/', statsData); // ADDED for completeness
export const updateUserProfile = (profileData) => apiClient.patch('/users/me/', profileData); // ADDED for completeness

// --- Game/Battle Related --- 
export const fetchAttacks = () => apiClient.get('/game/attacks/');
export const fetchBattle = (battleId) => apiClient.get(`/game/battles/${battleId}/`);
export const initiateBattle = (opponentId, fightAsBot = false) => apiClient.post('/game/battles/initiate/', { opponent_id: opponentId, fight_as_bot: fightAsBot });
export const respondToBattle = (battleId, action) => apiClient.post(`/game/battles/${battleId}/respond/`, { action });
export const sendBattleAction = (battleId, attackId) => apiClient.post(`/game/battles/${battleId}/action/`, { attack_id: attackId });
export const fetchPendingBattles = () => apiClient.get('/game/battles/requests/');
export const fetchActiveBattle = () => apiClient.get('/game/battles/active/'); // Get the user's currently active battle, if any
export const concedeBattle = (battleId) => apiClient.post(`/game/battles/${battleId}/concede/`);
export const cancelChallenge = (battleId) => apiClient.post(`/game/battles/${battleId}/cancel/`);
export const generateAttacks = (concept, favorite_attack_ids = []) => apiClient.post('/game/attacks/generate/', { concept, favorite_attack_ids });
export const fetchMyAttacks = () => apiClient.get('/game/attacks/my-attacks/');

// --- NEW: Leaderboard Related ---
export const fetchMyStats = () => apiClient.get('/users/me/stats/');
export const fetchLeaderboard = () => apiClient.get('/users/leaderboard/');
export const fetchAttackLeaderboard = (sortBy = 'used', limit = 50) => apiClient.get(`/game/leaderboard/attacks/?sort=${sortBy}&limit=${limit}`);