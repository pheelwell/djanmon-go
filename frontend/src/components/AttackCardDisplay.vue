<script setup>
import { computed } from 'vue';

const props = defineProps({
  attack: {
    type: Object,
    required: true
  },
  showDeleteButton: {
    type: Boolean,
    default: false
  }
});
const emit = defineEmits(['delete-clicked']);

// You could add computed properties here if needed for display logic,
// e.g., formatting descriptions or determining icons.
const displayEmoji = computed(() => props.attack.emoji || '⚔️');

</script>

<template>
  <div class="attack-card-content">
    <!-- Delete Button (Top Left) -->
    <button
      v-if="showDeleteButton"
      @click.stop="$emit('delete-clicked')"
      class="delete-button"
      title="Delete Attack"
    >
      &times;
    </button>

    <!-- Top Right Cost Display -->
    <div v-if="attack.momentum_cost > 0" class="cost-display">
        <span class="energy-symbol">⚡️</span>
        <span class="cost-value">{{ attack.momentum_cost }}</span>
    </div>

    <!-- Main Content -->
    <span class="emoji">{{ attack.emoji || '⚔️' }}</span>
    <h4>{{ attack.name }}</h4>
    <p class="power" v-if="attack.power > 0">Power: {{ attack.power }}</p>
    <p class="desc">{{ attack.description || 'No description' }}</p>
  </div>
</template>

<style scoped>
.attack-card-content {
    position: relative;
    /* text-align: center; */
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center; 
    width: 100%; 
    height: 100%; 
    padding: 5px;
    font-family: var(--font-primary);
    line-height: 1.3;
    border: 2px solid var(--color-border);
    background-color: var(--color-panel-bg);
    box-shadow: 2px 2px 0px var(--color-border);
    border-radius: 0;
}

.cost-display {
    position: absolute;
    top: 3px;
    right: 3px;
    display: flex;
    align-items: center;
    gap: 2px;
    background-color: var(--color-bg);
    padding: 1px 4px;
    border: 1px solid var(--color-border);
    font-size: 0.8em;
    font-weight: normal;
    color: var(--color-momentum-user);
    z-index: 1;
    border-radius: 0;
}

.energy-symbol {
    font-size: 1em;
}

.emoji {
    font-size: 2.5em;
    margin-bottom: 4px;
    margin-top: 8px;
    line-height: 1;
}

h4 {
    margin: 2px 0 4px 0;
    font-size: 1em;
    color: var(--color-accent-secondary);
    font-weight: normal;
    line-height: 1.2;
    text-transform: uppercase;
    text-align: center;
}

.power {
    font-size: 0.9em;
    color: var(--color-stat-up);
    font-weight: normal;
    margin: 0 0 4px 0;
    text-align: center;
}

.desc {
    font-size: 1em;
    color: var(--color-log-system);
    line-height: 1.3;
    margin: auto 0;
    max-width: 95%;
    padding-bottom: 2px;
    text-align: center;
    font-family: 'Roboto', sans-serif;
}

.delete-button {
  position: absolute;
  top: 1px;
  left: 1px;
  background-color: var(--color-accent);
  color: var(--color-panel-bg);
  border: 1px solid var(--color-border);
  border-radius: 0;
  width: 18px;
  height: 18px;
  font-size: 14px;
  line-height: 16px;
  text-align: center;
  padding: 0;
  cursor: pointer;
  z-index: 2;
  box-shadow: 1px 1px 0px var(--color-border);
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.delete-button:hover {
  background-color: #c0392b;
}
.delete-button:active {
   transform: translate(1px, 1px);
   box-shadow: none;
}
</style> 