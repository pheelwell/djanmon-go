import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)


app.use(createPinia())
app.use(router)

const authStore = useAuthStore();

authStore.fetchUserProfile().then(() => {
    app.mount('#app')
}).catch(error => {
    console.error("Initial profile fetch failed (may just mean not logged in):", error);
    app.mount('#app')
});
