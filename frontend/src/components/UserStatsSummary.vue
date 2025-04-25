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
  <div v-if="isLoading" class="loading">Loading stats...</div>
  <div v-else-if="stats" class="my-stats-grid"> 
      <p>Wins: {{ stats.total_wins ?? 'N/A' }}</p>
      <p>Losses: {{ stats.total_losses ?? 'N/A' }}</p>
      <p>Rounds Played: {{ stats.total_rounds_played ?? 'N/A' }}</p>
      <p>Nemesis: {{ nemesisDisplay }}</p>
      <!-- Add other stats here as needed -->
  </div>
  <div v-else class="no-stats-message">
    No stats available.
  </div>
</template>

<style scoped>
/* Styles adapted from LeaderboardView.vue */
.my-stats {
  background-color: var(--color-background-soft);
  padding: 1.5rem 2rem;
  border-radius: 8px;
  margin-bottom: 2.5rem;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  border-left: 5px solid var(--color-border-hover);
}

.my-stats h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.8rem;
}

.loading,
.no-stats-message {
  text-align: center;
  padding: 1rem;
  color: var(--color-text-muted);
  font-style: italic;
}

.my-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
}

.my-stats p {
  margin: 0;
  line-height: 1.6;
  background-color: var(--color-background-mute);
  padding: 0.8rem 1rem;
  border-radius: 4px;
}

.my-stats strong {
    color: var(--color-text);
    display: block;
    margin-bottom: 0.25rem;
    font-size: 0.9em;
    color: var(--color-text-muted);
}
</style> 