<template>
  <div class="auth-container">
    <h2>Login</h2>
    <form @submit.prevent="handleLogin" class="auth-form">
      <div class="form-group">
        <label for="username">Username:</label>
        <input type="text" id="username" v-model="username" required />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <button type="submit" :disabled="loading" class="btn btn-primary">{{ loading ? '...' : 'Login' }}</button>
      <p v-if="errorMessage" class="error-message">⚠️ {{ errorMessage }}</p>
      <p class="form-footer">Don't have an account? <router-link to="/register">Register here</router-link></p>
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
.auth-container {
    max-width: 350px;
    margin: 3rem auto;
    padding: var(--panel-padding);
    border: var(--border-width) solid var(--color-border);
    border-radius: 0;
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
    background-color: var(--color-panel-bg);
    font-family: var(--font-primary);
}

h2 {
    font-size: 1.3em; 
    color: var(--color-accent-secondary);
    margin: -15px -15px 20px -15px; /* Extend to edges */
    padding: 8px 15px;
    text-align: center;
    border-bottom: var(--border-width) solid var(--color-border);
    text-transform: uppercase;
    background-color: var(--color-border);
    color: var(--color-text);
    font-weight: normal;
    box-shadow: inset 0 0 0 1px var(--color-panel-bg);
}

.auth-form {
    display: flex;
    flex-direction: column;
    gap: 15px; /* Gap between form elements */
}

.form-group {
    /* No extra styles needed, just contains label+input */
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: normal;
    font-size: 0.9em;
    color: var(--color-text);
    text-transform: uppercase;
}

/* Assume input uses global styles from main.css */
input[type="text"],
input[type="password"] {
    /* Inherit from main.css */
}

/* Assume button uses global .btn styles */
.btn {
    width: 100%; /* Make button full width */
    margin-top: 10px; /* Add space above button */
}

.form-footer {
    margin-top: 15px;
    text-align: center;
    font-size: 0.9em;
    color: var(--color-text); /* Use standard text color */
}

.form-footer a {
    color: var(--color-accent-secondary); /* Link color */
    text-decoration: none;
}

.form-footer a:hover {
    color: var(--color-accent);
}

.error-message {
    /* Style adapted from HomeView/AttackCreator */
    padding: 8px 10px;
    border-radius: 0;
    font-weight: normal;
    text-align: center;
    border: 1px solid var(--color-accent);
    font-size: 0.9em;
    background-color: rgba(233, 69, 96, 0.1);
    color: var(--color-accent);
    margin-top: 0; /* Remove extra margin if needed */
}

</style> 