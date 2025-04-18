<script setup>
import { computed } from 'vue';

const props = defineProps({
  attack: {
    type: Object,
    required: true
  }
});

// You could add computed properties here if needed for display logic,
// e.g., formatting descriptions or determining icons.
const displayEmoji = computed(() => props.attack.emoji || '⚔️');

</script>

<template>
  <div class="attack-card-content">
    <!-- Top Right Cost Display -->
    <div v-if="attack.momentum_cost > 0" class="cost-display">
        <span class="energy-symbol">⚡️</span>
        <!-- Displaying the base cost, actual cost varies -->
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
/* Styles copied and adapted from BattleView.vue */
.attack-card-content {
    position: relative; /* Needed for absolute positioning of cost */
    text-align: center;
    display: flex;
    flex-direction: column;
    /* Align items to start (top) */
    justify-content: flex-start; 
    align-items: center; 
    width: 100%; 
    height: 100%; 
    padding: 0.5rem 0.2rem; /* Add small horizontal padding */
}

.cost-display {
    position: absolute;
    top: 0.2rem;      /* Reduced */
    right: 0.2rem;    /* Reduced */
    display: flex;
    align-items: center;
    gap: 0.15em;      /* Slightly reduced gap */
    background-color: rgba(0, 0, 0, 0.2); 
    padding: 0.05rem 0.3rem; /* Reduced padding */
    border-radius: 4px; /* Slightly smaller radius */
    font-size: 0.75em; /* Slightly smaller font */
    font-weight: bold;
    color: var(--vt-c-yellow); 
    z-index: 1; 
}

.energy-symbol {
    font-size: 1.1em;
}

.emoji {
    font-size: 2em; 
    margin-bottom: 0.2rem; /* Adjust margin */
    margin-top: 0.5rem; /* Add some top margin to push down from cost */
    line-height: 1;
}

h4 {
    margin: 0.2rem 0 0.3rem 0; /* Adjusted margin */
    font-size: 0.95em;
    color: var(--color-heading);
    font-weight: 600;
    line-height: 1.2;
}

.power {
    font-size: 0.8em;
    color: var(--vt-c-orange);
    font-weight: bold;
    margin: 0 0 0.3rem 0;
}

.desc {
    font-size: 0.75em;
    color: var(--color-text-mute);
    line-height: 1.2;
    margin: 0;
    max-width: 95%; /* Slightly increase max-width */
    margin-top: auto; /* Push description towards the bottom */
    padding-bottom: 0.2rem; /* Add slight padding at the very bottom */
}

/* Remove old .desc.cost style */
/* .desc.cost { ... } */
</style> 