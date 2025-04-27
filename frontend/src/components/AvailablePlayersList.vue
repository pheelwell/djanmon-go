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
      <div class="players-grid">
          <div v-for="player in players" :key="player.id" class="player-card panel">
              <div class="player-card-info">
                    <div class="player-card-pic-container">
                         <img 
                            v-if="player.profile_picture_base64" 
                            :src="'data:image/png;base64,' + player.profile_picture_base64" 
                            alt="Profile Picture" 
                            class="player-card-pic"
                         />
                         <div v-else class="player-card-pic-placeholder">?</div>
                    </div>
                  <div class="player-card-details">
                    <span class="player-username">{{ player.username }}</span>
                    <span class="level-badge">Lvl {{ player.level || '1' }}</span>
                 </div>
              </div>

              <div class="player-card-actions">
                <template v-if="isChallengePending(player.id)">
                  <button
                      class="button button-secondary button-small challenged-button"
                      @mouseover="hoveredChallenge = player.id"
                      @mouseleave="hoveredChallenge = null"
                      @click="handleCancelChallenge(player.id)"
                      :disabled="gameStore.actionError"
                  >
                    {{ hoveredChallenge === player.id ? 'Abort' : 'Pending' }}
                  </button>
                </template>
                <template v-else>
                  <button
                      @click="handleChallenge(player.id, false)"
                      :disabled="challengingUserId === player.id"
                      class="button button-primary button-small challenge-button"
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
                      🤖
                  </button>
                </template>
              </div>
          </div>
      </div>
  </div>
   <div v-else class="subsection no-items-placeholder">
      No other players available to challenge.
  </div>
</template>

<style scoped>
/* Reusing .panel style from global/HomeView */
.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding, 10px); /* Use variable with fallback */
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
    border-radius: 0;
}

.subsection {
    padding: 0; /* Remove outer padding, panel handles it */
    border: none;
    background-color: transparent;
    box-shadow: none;
}

.subsection h3 {
    /* Style for the section title */
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 1.2em;
    color: var(--color-accent-secondary);
    text-transform: uppercase;
    text-align: center;
    padding-bottom: 5px;
    border-bottom: 1px solid var(--color-border);
}

.loading-placeholder,
.no-items-placeholder {
    /* Styles unchanged */
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-mute);
    font-style: italic;
    border-radius: 8px;
    border: 1px dashed var(--color-border);
}

/* --- Player Card Grid --- */
.players-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); /* Responsive columns */
    gap: 10px;
    max-height: 400px; /* Or desired height */
    overflow-y: auto; /* Scroll vertically if needed */
    padding: 5px; /* Padding around the grid */
}

/* --- Player Card Styling --- */
.player-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 8px; /* Slightly reduced padding */
    gap: 8px; /* Space between info and actions */
}

.player-card-info {
    display: flex;
    flex-direction: column; /* Stack pic and details */
    align-items: center;
    gap: 6px;
    margin-bottom: 5px; /* Space above actions */
}

.player-card-pic-container {
    width: 80px; /* Increased size again */
    height: 80px;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    box-shadow: 1px 1px 0px var(--color-border);
    flex-shrink: 0;
}

.player-card-pic {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
}

.player-card-pic-placeholder {
    font-size: 2.8em; /* Increased placeholder size again */
    color: var(--color-text-muted);
    font-family: var(--font-primary);
}

.player-card-details {
    display: flex;
    flex-direction: column;
    align-items: center;
    line-height: 1.2;
}

.player-username {
    font-weight: normal; /* Use primary font weight */
    font-size: 0.9em;
}

.level-badge {
    font-size: 0.7em;
    color: var(--color-text-muted);
    margin-top: 2px; /* Space below username */
}

.bot-opt-in-label {
   /* This style is no longer needed if the span is removed */
   /* display: none; */ 
}

.player-card-actions {
    display: flex;
    justify-content: center; /* Center buttons */
    gap: 6px;
    width: 100%; /* Make button container take width */
    margin-top: auto; /* Push buttons to bottom */
    padding-top: 5px;
    /* border-top: 1px solid var(--color-border); /* Optional separator */
}

/* --- Button Styles (Using global .button if possible) --- */
/* Assuming .button, .button-primary, .button-secondary, .button-small exist */

.challenge-button {
    flex-grow: 1; /* Allow challenge button to take more space */
}

.bot-challenge-button {
    flex-shrink: 0; /* Don't shrink AI button */
}

.challenged-button {
  /* Styles unchanged */
  background-color: var(--color-background-mute);
  color: var(--color-text-mute); 
  border: 1px solid var(--color-border); 
  opacity: 0.7;
  width: 100%; /* Make pending button take full width */
}

.challenged-button:hover:not(:disabled) {
  /* Styles unchanged */
  background-color: var(--vt-c-red-soft); 
  color: var(--vt-c-red-dark);
  border-color: var(--vt-c-red); 
  border-style: solid; 
  opacity: 1; 
}

/* --- Button Styles --- */
/* Reduce padding and font size for buttons within the card */
.player-card-actions .button {
    padding: 4px 8px; /* Smaller padding */
    font-size: 0.8em; /* Smaller font */
    /* Inherit other base .button styles */
}

</style> 