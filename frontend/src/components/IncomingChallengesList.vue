<script setup>
const props = defineProps({
  battles: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  respondingBattleId: {
    type: [Number, String, null],
    default: null
  }
});

const emit = defineEmits(['respond']);

function handleResponse(battleId, action) {
  emit('respond', battleId, action);
}

</script>

<template>
  <div v-if="isLoading && !battles.length" class="loading-placeholder">
       Loading incoming challenges...
  </div>
   <div v-else-if="battles.length > 0" class="incoming-challenges subsection">
      <h3>Incoming Challenges ({{ battles.length }})</h3>
      <ul class="simple-list challenges-list">
           <li v-for="battle in battles" :key="battle.id" class="list-item-simple challenge-item">
              <span><strong>{{ battle.player1.username }}</strong> (Lvl {{ battle.player1.level || '1' }})</span>
              <div class="button-group">
                  <button
                      @click="handleResponse(battle.id, 'accept')"
                      :disabled="respondingBattleId === battle.id"
                      class="button button-accept button-small"
                  >
                      {{ respondingBattleId === battle.id ? '...' : 'Accept' }}
                   </button>
                  <button
                      @click="handleResponse(battle.id, 'decline')"
                      :disabled="respondingBattleId === battle.id"
                       class="button button-decline button-small"
                  >
                       {{ respondingBattleId === battle.id ? '...' : 'Decline' }}
                  </button>
              </div>
          </li>
      </ul>
  </div>
  <div v-else class="subsection no-items-placeholder">
      No incoming challenges.
  </div>
</template>

<style scoped>
/* Styles adapted from HomeView.vue */
.subsection {
    padding: 1rem 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    background-color: var(--color-background-mute);
}

.subsection h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.1em;
    color: var(--color-heading);
    border-bottom: 1px solid var(--color-border-hover);
    padding-bottom: 0.5rem;
}

.loading-placeholder,
.no-items-placeholder {
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-mute);
    font-style: italic;
    border-radius: 8px;
    border: 1px dashed var(--color-border);
    /* margin-top: 1rem; */ /* Removed top margin for better integration */
}

.simple-list {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 300px; /* Limit height */
    overflow-y: auto;
}

.list-item-simple {
   display: flex;
   justify-content: space-between;
   align-items: center;
   padding: 0.6rem 0.2rem; /* Adjust padding */
   margin-bottom: 0.3rem;
   border-bottom: 1px solid var(--color-border-hover);
}
.list-item-simple:last-child {
    border-bottom: none;
}

.list-item-simple span strong {
    color: var(--color-heading);
}

.list-item-simple .button-group {
     display: flex;
     gap: 0.5rem;
}

/* Basic Button Styles (Assume these might be global or importable) */
.button {
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.2s ease, opacity 0.2s ease;
    line-height: 1; /* Prevent text jumping */
}
.button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.button-small {
    padding: 0.3rem 0.7rem;
    font-size: 0.85em;
}

.button-accept {
    background-color: var(--color-success);
    color: white;
}
.button-accept:hover:not(:disabled) {
    background-color: var(--color-success-dark);
}

.button-decline {
    background-color: var(--color-danger);
    color: white;
}
.button-decline:hover:not(:disabled) {
     background-color: var(--color-danger-dark);
}

</style> 