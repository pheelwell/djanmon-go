import axios from 'axios';

// Determine the base URL for the Django backend
// Default to http://localhost:8000/api which is common for local Django dev
// You might need to adjust this based on your Django server's address and port
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Optional: Interceptor to add the JWT token to requests if logged in
// We'll integrate this properly with the auth store later
// apiClient.interceptors.request.use(config => {
//   // const authStore = useAuthStore(); // Assuming you have Pinia store
//   // const token = authStore.accessToken;
//   const token = localStorage.getItem('accessToken'); // Or get from store
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }
//   return config;
// }, error => {
//   return Promise.reject(error);
// });

export default apiClient; 