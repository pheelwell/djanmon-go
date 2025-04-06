import axios from 'axios';

// Determine the base URL based on the environment
// Use VITE_API_BASE_URL from .env file during development (npm run dev)
// Use the current window origin for production builds (assuming frontend and backend are served from the same domain or handled by a proxy)
const baseURL = import.meta.env.VITE_API_BASE_URL || window.location.origin + '/api';

const apiClient = axios.create({
  baseURL: baseURL,
  // headers: { // You might set common headers here if needed
  //   'Content-Type': 'application/json',
  // }
});

// Optional: Add interceptors for things like adding auth tokens to requests
// or handling global errors (like 401 Unauthorized for auto-logout)

// Example Request Interceptor (Add Authorization Header)
// apiClient.interceptors.request.use(
//   config => {
//     const token = localStorage.getItem('accessToken'); // Or wherever you store your token
//     if (token) {
//       config.headers['Authorization'] = `Bearer ${token}`;
//     }
//     return config;
//   },
//   error => {
//     return Promise.reject(error);
//   }
// );

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
export const fetchUserProfile = () => apiClient.get('/users/me/');
export const updateUserSelectedAttacks = (attackIds) => apiClient.put('/users/me/selected-attacks/', { attack_ids: attackIds }); // Send as object
export const fetchUserList = () => apiClient.get('/users/'); // Fetch list of potential opponents

// --- Game/Battle Related --- 
export const fetchAttacks = () => apiClient.get('/game/attacks/');
export const fetchBattle = (battleId) => apiClient.get(`/game/battles/${battleId}/`);
export const initiateBattle = (opponentId) => apiClient.post('/game/battles/initiate/', { opponent_id: opponentId });
export const respondToBattle = (battleId, action) => apiClient.post(`/game/battles/${battleId}/respond/`, { action });
export const sendBattleAction = (battleId, attackId) => apiClient.post(`/game/battles/${battleId}/action/`, { attack_id: attackId });
export const fetchPendingBattles = () => apiClient.get('/game/battles/pending/');
export const fetchActiveBattle = () => apiClient.get('/game/battles/active/'); // Get the user's currently active battle, if any

// --- NEW: Leaderboard Related ---
export const fetchMyStats = () => apiClient.get('/users/me/stats/');
export const fetchLeaderboard = () => apiClient.get('/users/leaderboard/');