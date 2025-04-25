import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { fetchCsrfToken } from '@/services/api'

const app = createApp(App)

app.use(createPinia())
app.use(router)

async function initializeApp() {
  try {
    await fetchCsrfToken();
    
    const authStore = useAuthStore();
    await authStore.fetchUserProfile();
    console.log('Initial user profile fetch attempted.');

  } catch (error) {
    console.error("Initialization error (CSRF or profile fetch failed):", error);
  } finally {
    app.mount('#app')
    console.log('App mounted.');
  }
}

initializeApp();
