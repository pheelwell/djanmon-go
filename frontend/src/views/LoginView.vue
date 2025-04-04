<template>
  <div>
    <h2>Login</h2>
    <form @submit.prevent="handleLogin">
      <div>
        <label for="username">Username:</label>
        <input type="text" id="username" v-model="username" required />
      </div>
      <div>
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <button type="submit" :disabled="loading">Login</button>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <p>Don't have an account? <router-link to="/register">Register here</router-link></p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const username = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref(null);

const router = useRouter();
const authStore = useAuthStore();

const handleLogin = async () => {
  loading.value = true;
  errorMessage.value = null;
  const success = await authStore.login(username.value, password.value);
  loading.value = false;

  if (success) {
    // Redirect to dashboard or home page after successful login
    router.push({ name: 'home' }); // Assuming you have a 'home' route
  } else {
    // Display error message from the store
    const errorData = authStore.loginError;
    if (errorData && typeof errorData === 'object') {
      // Combine multiple errors if backend returns them (e.g., non_field_errors)
      errorMessage.value = Object.values(errorData).flat().join(' ');
    } else {
      errorMessage.value = errorData?.detail || 'Login failed. Please check your credentials.';
    }
  }
};
</script>

<style scoped>
.error {
  color: red;
}
div {
    max-width: 400px;
    margin: 2rem auto;
    padding: 2rem;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
label {
    display: block;
    margin-bottom: 0.5rem;
}
input {
    width: 100%;
    padding: 0.5rem;
    margin-bottom: 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}
button {
    padding: 0.75rem 1.5rem;
    background-color: #42b983; /* Vue green */
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s;
}
button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}
button:hover:not(:disabled) {
    background-color: #36a374;
}
p {
    margin-top: 1rem;
}
.error {
    margin-top: 1rem;
    color: #e74c3c; /* Red */
}
</style> 