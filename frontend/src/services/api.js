import axios from 'axios';

// Determine the base URL based on the environment
// Use VITE_API_BASE_URL from .env file during development (npm run dev)
// Use the current window origin for production builds (assuming frontend and backend are served from the same domain or handled by a proxy)
// const baseURL = import.meta.env.VITE_API_BASE_URL || window.location.origin + '/api';

// --- MODIFIED for SameSite Development ---
// Explicitly target localhost:8000 to match the likely browser access point
// Ensures browser treats requests as same-site if frontend is on localhost:5173
const useDevServer = import.meta.env.DEV; // Check if in development mode (Vite default)
const baseURL = useDevServer 
    ? 'http://localhost:8000/api' 
    : (window.location.origin + '/api'); // Production remains same-origin
// --- END MODIFICATION ---

const apiClient = axios.create({
  baseURL: baseURL,
  withCredentials: true, // <-- ADDED: Send cookies with requests
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

// --- ADD CSRF Token Interceptor ---
// Function to get CSRF cookie
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

apiClient.interceptors.request.use(config => {
  // Add CSRF token header for non-safe methods
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(config.method.toUpperCase())) {
    const csrfToken = getCookie('csrftoken'); // Django's default CSRF cookie name
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
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