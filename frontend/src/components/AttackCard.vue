<script setup>
import { computed } from 'vue';

defineProps({
  attack: {
    type: Object,
    required: true,
  },
});

// Example: Formatting stat change display
const statChangeDisplay = computed(() => {
  if (!attack || !attack.target_stat || attack.target_stat === 'NONE' || attack.stat_mod === 0) {
    return null;
  }
  const direction = attack.stat_mod > 0 ? '+' : '';
  return `${attack.target_stat} ${direction}${attack.stat_mod}`;
});

const hpChangeDisplay = computed(() => {
    if (!attack || attack.hp_amount === 0) return null;
    const prefix = attack.hp_amount > 0 ? '+' : '';
    const type = attack.hp_amount > 0 ? 'Heal' : 'Damage';
    return `${type} ${prefix}${attack.hp_amount} HP`;
})

</script>

<template>
  <div class="attack-card">
    <div class="attack-header">
        <span class="attack-emoji" v-if="attack.emoji">{{ attack.emoji }}</span>
        <span class="attack-name">{{ attack.name }}</span>
    </div>
    <p class="attack-description" v-if="attack.description">{{ attack.description }}</p>
    <div class="attack-stats">
        <span v-if="attack.power > 0">Power: {{ attack.power }}</span>
        <span v-if="statChangeDisplay">Effect: {{ statChangeDisplay }}</span>
        <span v-if="hpChangeDisplay">Effect: {{ hpChangeDisplay }}</span>
        <span>Target: {{ attack.target }}</span>
        <span>Momentum: {{ attack.momentum_cost }}</span>
    </div>
  </div>
</template>

<style scoped>
.attack-card {
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.8rem 1rem;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  max-width: 280px; /* Adjust as needed */
  font-size: 0.9rem;
  color: var(--color-text);
  position: absolute; /* Needed for positioning relative to trigger */
  z-index: 10; /* Ensure it appears above table */
  pointer-events: none; /* Prevent card itself from interfering with hover */
  opacity: 0; /* Hidden by default */
  transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
  transform: translateY(10px);
}

.attack-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border-hover);
}

.attack-emoji {
    font-size: 1.2em;
}

.attack-name {
  font-weight: bold;
  color: var(--color-heading);
}

.attack-description {
  font-style: italic;
  margin-bottom: 0.8rem;
  color: var(--color-text-muted);
  font-size: 0.85em;
}

.attack-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.8rem; /* Row and column gap */
  font-size: 0.85em;
}

.attack-stats span {
  background-color: var(--color-background-soft);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}
</style> 