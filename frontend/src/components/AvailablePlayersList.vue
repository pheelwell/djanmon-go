<script setup>
const props = defineProps({
  players: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  challengingUserId: {
    type: [Number, String, null],
    default: null
  }
});

const emit = defineEmits(['challenge']);

function handleChallenge(playerId) {
  emit('challenge', playerId);
}

</script>

<template>
  <div v-if="isLoading && !players.length" class="loading-placeholder">
      Loading available players...
  </div>
   <div v-else-if="players.length > 0" class="available-players subsection">
      <h3>Challenge a Player</h3>
      <ul class="simple-list players-list">
          <li v-for="player in players" :key="player.id" class="list-item-simple player-item">
              <span>{{ player.username }}
                <span v-if="player.is_bot" class="bot-label">(BOT)</span>
                (Lvl {{ player.level || '1' }})</span>
              <button
                  @click="handleChallenge(player.id)"
                  :disabled="challengingUserId === player.id"
                  class="button button-secondary button-small challenge-button"
               >
                  {{ challengingUserId === player.id ? 'Sending...' : 'Challenge' }}
              </button>
          </li>
      </ul>
  </div>
   <div v-else class="subsection no-items-placeholder">
      No other players available to challenge.
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
    /* margin-top: 1rem; */
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
   padding: 0.6rem 0.2rem;
   margin-bottom: 0.3rem;
   border-bottom: 1px solid var(--color-border-hover);
}
.list-item-simple:last-child {
    border-bottom: none;
}

.list-item-simple span {
    /* Optional: Style player name/level text if needed */
}

/* Basic Button Styles */
.button {
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.2s ease, opacity 0.2s ease;
    line-height: 1;
}
.button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.button-small {
    padding: 0.3rem 0.7rem;
    font-size: 0.85em;
}

.button-secondary {
  background-color: var(--color-secondary);
  color: var(--color-text);
  border: 1px solid var(--color-border-hover);
}
.button-secondary:hover:not(:disabled) {
  background-color: var(--color-background-mute);
}

.challenge-button {
    /* Add specific styles if needed */
}

.bot-label {
  font-weight: normal;
  font-size: 0.9em;
  color: var(--color-text-mute);
  margin-left: 0.3em;
}

</style> 