<script setup>
import { ref, computed } from 'vue';
import { useGameStore } from '@/stores/game';

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
const gameStore = useGameStore();

const hoveredChallenge = ref(null);

function isChallengePending(playerId) {
  return Object.keys(gameStore.outgoingPendingChallenges).map(Number).includes(playerId);
}

function getPendingChallengeId(playerId) {
  return gameStore.outgoingPendingChallenges[playerId];
}

function handleChallenge(playerId, fightAsBot = false) {
  if (!isChallengePending(playerId)) {
    emit('challenge', { opponentId: playerId, fightAsBot: fightAsBot });
  }
}

async function handleCancelChallenge(playerId) {
  const battleId = getPendingChallengeId(playerId);
  if (battleId) {
    await gameStore.cancelChallenge(battleId);
  }
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
              <span class="player-info">{{ player.username }}
                <span class="level-badge">(Lvl {{ player.level || '1' }})</span>
                <span v-if="player.allow_bot_challenges" class="bot-opt-in-label" title="This player can be fought as an AI">🤖</span>
              </span>
              <div class="player-actions">
                <template v-if="isChallengePending(player.id)">
                  <button
                      class="button button-secondary button-small challenged-button"
                      @mouseover="hoveredChallenge = player.id"
                      @mouseleave="hoveredChallenge = null"
                      @click="handleCancelChallenge(player.id)"
                      :disabled="gameStore.actionError"
                  >
                    {{ hoveredChallenge === player.id ? 'Abort' : 'Challenged!' }}
                  </button>
                </template>
                <template v-else>
                  <button
                      @click="handleChallenge(player.id, false)"
                      :disabled="challengingUserId === player.id"
                      class="button button-secondary button-small challenge-button"
                  >
                      {{ challengingUserId === player.id ? 'Sending...' : 'Challenge' }}
                  </button>
                  <button
                      v-if="player.allow_bot_challenges"
                      @click="handleChallenge(player.id, true)"
                      :disabled="challengingUserId === player.id"
                      class="button button-secondary button-small bot-challenge-button"
                      title="Fight this player as an AI"
                  >
                      AI
                  </button>
                </template>
              </div>
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

.player-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.level-badge {
    display: inline-block;
    background-color: var(--color-secondary);
    color: var(--color-text-mute);
    font-size: 0.75em;
    font-weight: bold;
    padding: 0.1em 0.5em;
    border-radius: 4px;
    margin-left: 0.5em;
    vertical-align: middle;
    line-height: 1.2;
}

.bot-opt-in-label {
    font-size: 1.1em;
    cursor: help;
    opacity: 0.8;
}

.player-actions {
    display: flex;
    gap: 0.5rem;
}

.bot-challenge-button {
  /* background-color: var(--vt-c-blue-soft); */
  /* border-color: var(--vt-c-blue); */
  /* Add specific styles if needed */
}

.challenged-button {
  background-color: var(--color-background-mute); /* Keep muted background */
  color: var(--color-text-mute); 
  border: 1px solid var(--color-border); /* Subtle border */
  opacity: 0.7; /* Slightly faded */
}

.challenged-button:hover:not(:disabled) {
  background-color: var(--vt-c-red-soft); /* Red background on hover */
  color: var(--vt-c-red-dark);
  border-color: var(--vt-c-red); 
  border-style: solid; /* Solid border on hover */
  opacity: 1; /* Full opacity on hover */
}

</style> 