<template>
  <div class="auth-container">
    <h2>Register</h2>
    <form @submit.prevent="handleRegister" class="auth-form">
      <div class="form-group">
        <label for="username">Username:</label>
        <input type="text" id="username" v-model="username" required />
      </div>
      <div class="form-group">
        <label for="email">Email (optional):</label>
        <input type="email" id="email" v-model="email" />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <div class="form-group">
        <label for="password2">Confirm Password:</label>
        <input type="password" id="password2" v-model="password2" required />
      </div>
      <button type="submit" :disabled="loading" class="btn btn-primary">{{ loading ? '...' : 'Register' }}</button>
      <p v-if="errorMessage" class="error-message">⚠️ {{ errorMessage }}</p>
      <p v-if="successMessage" class="success-message">✅ {{ successMessage }}</p>
      <p class="form-footer">Already have an account? <router-link to="/login">Login here</router-link></p>
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

label {
    display: block;
    margin-bottom: 5px;
    font-weight: normal;
    font-size: 0.9em;
    color: var(--color-text);
    text-transform: uppercase;
}


/* Assume button uses global .btn styles */
.btn {
    width: 100%; 
    margin-top: 10px;
}

.form-footer {
    margin-top: 15px;
    text-align: center;
    font-size: 0.9em;
    color: var(--color-text);
}

.form-footer a {
    color: var(--color-accent-secondary);
    text-decoration: none;
}

.form-footer a:hover {
    color: var(--color-accent);
}

/* Reusing error/success message styles */
.error-message, .success-message {
    padding: 8px 10px;
    border-radius: 0;
    font-weight: normal;
    text-align: center;
    border: 1px solid;
    font-size: 0.9em;
    margin-top: 0; /* Remove potential extra margin */
}
.error-message {
    background-color: rgba(233, 69, 96, 0.1);
    color: var(--color-accent);
    border-color: var(--color-accent);
}
.success-message {
    background-color: rgba(53, 208, 104, 0.1);
    color: var(--color-hp-high);
    border-color: var(--color-hp-high);
}

</style> 