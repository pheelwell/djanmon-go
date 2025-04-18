<script setup>
import { computed } from 'vue';
import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue';

const props = defineProps({
  user: {
    type: Object,
    required: true
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

</style> 