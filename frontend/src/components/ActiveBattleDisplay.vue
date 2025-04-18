<script setup>
const props = defineProps({
  activeBattle: {
    type: Object,
    required: true
  },
  opponent: {
    type: Object,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['goToBattle']);

function emitGoToBattle() {
  emit('goToBattle', props.activeBattle.id);
}
</script>

<template>
  <div v-if="isLoading" class="loading-placeholder">
      Checking battle status...
  </div>
  <div v-else-if="activeBattle && opponent" class="active-battle-display subsection">
      <h3>Active Battle</h3>
      <p>You are currently battling {{ opponent.username }}.</p>
      <button
          @click="emitGoToBattle"
          class="button button-primary resume-button"
      >
          Resume Battle
      </button>
  </div>
  <!-- Optionally, add a placeholder if no active battle, but parent might handle this -->
  <!-- <div v-else class="no-active-battle-placeholder">No active battle.</div> -->
</template>

<style scoped>
/* Styles adapted from HomeView.vue */
.subsection {
    padding: 1rem 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    background-color: var(--color-background-mute);
}

.loading-placeholder {
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-mute);
    font-style: italic;
    border-radius: 8px;
    border: 1px dashed var(--color-border);
    margin-top: 1rem; /* Add some space if standalone */
}

.active-battle-display {
    text-align: center;
    background-color: var(--color-primary-soft); /* Highlight active battle */
    border-color: var(--color-primary);
}

.active-battle-display h3 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.1em;
    color: var(--color-primary-dark);
    border-bottom: none;
}

.active-battle-display p {
    margin: 0 0 1rem 0;
    color: var(--color-text);
}

.resume-button {
    width: auto; /* Don't force full width */
    display: inline-block;
    /* Assuming general button styles are available */
}

/* Import general button styles if not global */
.button {
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.2s ease, opacity 0.2s ease;
}
.button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
.button-primary {
    background-color: var(--color-primary);
    color: white;
}
.button-primary:hover:not(:disabled) {
    background-color: var(--color-primary-dark);
}

</style> 