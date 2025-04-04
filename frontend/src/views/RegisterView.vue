<template>
  <div>
    <h2>Register</h2>
    <form @submit.prevent="handleRegister">
      <div>
        <label for="username">Username:</label>
        <input type="text" id="username" v-model="username" required />
      </div>
      <div>
        <label for="email">Email (optional):</label>
        <input type="email" id="email" v-model="email" />
      </div>
      <div>
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <div>
        <label for="password2">Confirm Password:</label>
        <input type="password" id="password2" v-model="password2" required />
      </div>
      <button type="submit" :disabled="loading">Register</button>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
       <p v-if="successMessage" class="success">{{ successMessage }}</p>
      <p>Already have an account? <router-link to="/login">Login here</router-link></p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const username = ref('');
const email = ref('');
const password = ref('');
const password2 = ref('');
const loading = ref(false);
const errorMessage = ref(null);
const successMessage = ref(null);

const router = useRouter();
const authStore = useAuthStore();

const handleRegister = async () => {
  loading.value = true;
  errorMessage.value = null;
  successMessage.value = null;

  if (password.value !== password2.value) {
      errorMessage.value = "Passwords do not match.";
      loading.value = false;
      return;
  }

  const success = await authStore.register(
    username.value,
    password.value,
    password2.value,
    email.value
  );
  loading.value = false;

  if (success) {
    successMessage.value = 'Registration successful! You can now log in.';
    // Optionally clear form or redirect
    // username.value = '';
    // email.value = '';
    // password.value = '';
    // password2.value = '';
    // setTimeout(() => router.push('/login'), 2000); // Redirect after delay
  } else {
    const errorData = authStore.registerError;
     if (errorData && typeof errorData === 'object') {
      // Combine multiple errors (e.g., username already exists, password too common)
      errorMessage.value = Object.entries(errorData)
        .map(([field, errors]) => `${field}: ${errors.join(' ')}`)
        .join('; ');
    } else {
        errorMessage.value = errorData?.detail || 'Registration failed. Please try again.';
    }
  }
};
</script>

<style scoped>
/* Reuse styles from LoginView or create shared styles */
.error {
  color: red;
}
.success {
  color: green;
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
.success {
     margin-top: 1rem;
     color: #2ecc71; /* Green */
}
</style> 