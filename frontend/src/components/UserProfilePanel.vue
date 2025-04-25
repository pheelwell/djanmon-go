<script setup>
import { computed, ref } from 'vue';
import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue';
import { useAuthStore } from '@/stores/auth';

const props = defineProps({
  user: {
    type: Object,
    required: true
  }
});

const authStore = useAuthStore();
const isUpdatingBotOptIn = ref(false);

const allowBotChallengesModel = computed({
  get: () => props.user?.allow_bot_challenges ?? false,
  async set(newValue) {
    if (!props.user) return;
    isUpdatingBotOptIn.value = true;
    const success = await authStore.updateUserProfile({ allow_bot_challenges: newValue });
    if (!success) {
      console.error('Failed to update bot challenge preference');
    } else {
       // Optionally show success feedback
    }
    isUpdatingBotOptIn.value = false;
  }
});

</script>

<template>
  <div class="user-panel panel">
      <div v-if="user">
        <h2>{{ user.username }}'s Quarters</h2>

        <!-- Display Booster Credits -->
        <div class="user-currency">
          <span class="label">💰 Credits:</span>
          <span class="value">{{ user.booster_credits ?? 0 }}</span>
        </div>

        <!-- Basic Info Display (Stats bars removed) -->
        <div class="user-basic-info">
            <div class="stat-level">
                <span class="label">LVL</span>
                <!-- Assuming level is still a concept, adjust if not -->
                <span class="value">{{ user.level || '1' }}</span>
            </div>
        </div>

        <!-- Embed Stats Editor directly -->
        <UserProfileStatsEditor />

        <!-- NEW: Allow Bot Challenges Toggle -->
        <div class="bot-challenge-toggle">
          <label for="allow-bot-challenge-checkbox">
            <input 
              type="checkbox" 
              id="allow-bot-challenge-checkbox" 
              v-model="allowBotChallengesModel" 
              :disabled="isUpdatingBotOptIn"
            />
            Allow others to fight me as an AI
          </label>
          <span v-if="isUpdatingBotOptIn" class="loading-indicator">⚙️</span>
        </div>
      </div>
      <div v-else>
        <p>Loading user profile...</p>
      </div>
  </div>
</template>

<style scoped>
/* Styles adapted from HomeView.vue */
.panel {
    background-color: var(--color-background-soft);
    padding: 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.user-panel {
  /* Add any specific container styles if needed */
   position: relative; /* Needed if child elements use absolute positioning relative to this */
}

.user-panel h2 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    color: var(--color-heading);
    text-align: center;
    border-bottom: 1px solid var(--color-border-hover);
    padding-bottom: 0.8rem;
}

.user-currency {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1em;
    margin-bottom: 1.5rem;
    background-color: var(--color-background-mute);
    padding: 0.5rem 1rem;
    border-radius: 6px;
    width: fit-content;
    margin-left: auto;
    margin-right: auto;
}
.user-currency .label {
    font-weight: bold;
    color: var(--color-text-muted);
}
.user-currency .value {
    font-weight: bold;
    color: var(--vt-c-yellow);
}

.user-basic-info {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 2rem;
    margin-bottom: 2rem;
}

.stat-level {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: var(--color-background-mute);
    padding: 0.5rem 1rem;
    border-radius: 50%; /* Make it circular */
    width: 60px;
    height: 60px;
    justify-content: center;
    border: 2px solid var(--color-border-hover);
}
.stat-level .label {
    font-size: 0.8em;
    color: var(--color-text-muted);
    font-weight: bold;
    line-height: 1;
}
.stat-level .value {
    font-size: 1.4em;
    font-weight: bold;
    color: var(--color-heading);
    line-height: 1.1;
}

.bot-challenge-toggle {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.bot-challenge-toggle label {
  cursor: pointer;
  display: inline-flex; /* Align checkbox and text */
  align-items: center;
  gap: 0.5rem;
}

.bot-challenge-toggle input[type="checkbox"] {
  cursor: pointer;
  /* Remove default appearance */
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  /* Custom Styling */
  width: 14px; /* Pixel-friendly size */
  height: 14px;
  background-color: var(--color-bg); /* Dark background */
  border: 1px solid var(--color-border);
  position: relative;
  display: inline-block;
  vertical-align: middle; /* Align with text */
  border-radius: 0; /* No rounded corners */
  box-shadow: 1px 1px 0px var(--color-border); /* Pixel shadow */
}

.bot-challenge-toggle input[type="checkbox"]:checked {
  background-color: var(--color-accent-secondary); /* Use theme color for checked */
  border-color: var(--color-border);
}

/* Custom Checkmark */
.bot-challenge-toggle input[type="checkbox"]:checked::after {
  content: '';
  display: block;
  position: absolute;
  /* Style a simple pixel checkmark */
  left: 4px;
  top: 1px;
  width: 3px;
  height: 7px;
  border: solid var(--color-bg); /* Checkmark color */
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.bot-challenge-toggle input[type="checkbox"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    box-shadow: none;
}

.loading-indicator {
    display: inline-block;
    margin-left: 0.5rem;
    animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

</style> 