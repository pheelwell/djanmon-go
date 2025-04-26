<script setup>
import { computed } from 'vue';

const props = defineProps({
  stats: {
    type: [Object, null], // Can be null if loading or error
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

// Helper to format nemesis display
const nemesisDisplay = computed(() => {
  if (!props.stats || !props.stats.nemesis) {
    return 'None (yet!)';
  }
  // Ensure losses_against exists before displaying
  const losses = props.stats.nemesis.losses_against !== undefined 
                 ? `(${props.stats.nemesis.losses_against} losses)` 
                 : '';
  return `${props.stats.nemesis.username} ${losses}`.trim();
});

</script>

<template>
  <div v-if="isLoading" class="loading-placeholder">Loading your stats...</div>
  <div v-else-if="stats" class="my-stats-container">
      <h3>Your Stats</h3>
      <div class="my-stats-grid"> 
          <p>Wins: <span>{{ stats.total_wins ?? 'N/A' }}</span></p>
          <p>Losses: <span>{{ stats.total_losses ?? 'N/A' }}</span></p>
          <p>Rounds Played: <span>{{ stats.total_rounds_played ?? 'N/A' }}</span></p>
          <p>Nemesis: <span>{{ nemesisDisplay }}</span></p>
      </div>
  </div>
  <div v-else class="no-stats-message">
    No stats available yet.
  </div>
</template>

<style scoped>
.my-stats-container {
  background-color: var(--color-panel-bg); /* Match panel */
  padding: 10px;
  border-radius: 0;
  border: 1px solid var(--color-border); /* Subtler border */
  box-shadow: inset 0 0 0 1px var(--color-bg); /* Inner shadow like panel */
  font-family: var(--font-primary);
}

.my-stats-container h3 {
    font-size: 1.1em; 
    color: var(--color-accent-secondary);
    margin: 0 0 10px 0;
    padding-bottom: 5px;
    text-align: center;
    border-bottom: 1px dashed var(--color-border);
    text-transform: uppercase;
    font-weight: normal;
}

.loading-placeholder,
.no-stats-message {
  text-align: center;
  padding: 10px;
  color: var(--color-log-system);
  font-style: italic;
  font-size: 0.9em;
  border: 1px dashed var(--color-border);
  background-color: var(--color-bg);
  text-transform: uppercase;
  font-family: var(--font-primary);
}

.my-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 8px;
}

.my-stats-grid p {
  margin: 0;
  line-height: 1.3;
  background-color: var(--color-bg); /* Darker bg for stat items */
  padding: 5px 8px;
  border: 1px solid var(--color-border);
  font-size: 0.9em;
  display: flex; /* Use flex to align text */
  justify-content: space-between;
}

.my-stats-grid p span {
    font-weight: bold; /* Make value bold */
    color: var(--color-text);
}

/* Remove old .my-stats styles */

</style> 