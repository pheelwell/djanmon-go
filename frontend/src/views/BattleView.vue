<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import AttackGrid from '@/components/AttackGrid.vue';
import PlayerInfoCard from '@/components/PlayerInfoCard.vue';
import BattleLog from '@/components/BattleLog.vue';
import _ from 'lodash';

const route = useRoute();
const router = useRouter();
const gameStore = useGameStore();
const authStore = useAuthStore();

// Define clamp locally
function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

const battleId = computed(() => parseInt(route.params.id));
const isLoading = ref(false);
const submittingAction = ref(false);
const isConceding = computed(() => gameStore.isConceding);
const displayedLogEntries = ref([]);
const displayedBattleState = ref(null);
const isProcessingLogs = ref(false);
let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 1000;
const MOMENTUM_THRESHOLD = 50; // Threshold for pendulum swing based on current turn momentum

// NEW: State for the previewed attack card
const selectedAttackPreview = ref(null); 

// Helper delay function
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// --- Computed properties from Stores ---
const battle = computed(() => gameStore.activeBattle);
const currentUser = computed(() => authStore.currentUser);
const battleError = computed(() => gameStore.battleError);
const battleMessage = computed(() => gameStore.battleMessage);

// Determine player roles and opponent (Uses displayed state)
const userPlayerRole = computed(() => {
    if (!displayedBattleState.value || !currentUser.value) return null;
    if (displayedBattleState.value.player1.id === currentUser.value.id) return 'player1';
    if (displayedBattleState.value.player2.id === currentUser.value.id) return 'player2';
    return null;
});

const userPlayer = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return null;
    return displayedBattleState.value[userPlayerRole.value];
});

const opponentPlayer = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return null;
    return userPlayerRole.value === 'player1' ? displayedBattleState.value.player2 : displayedBattleState.value.player1;
});

const userCurrentHp = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return 0;
    return userPlayerRole.value === 'player1' ? displayedBattleState.value.current_hp_player1 : displayedBattleState.value.current_hp_player2;
});

const opponentCurrentHp = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return 0;
    return userPlayerRole.value === 'player1' ? displayedBattleState.value.current_hp_player2 : displayedBattleState.value.current_hp_player1;
});

// Check if it's user's turn to act (Uses displayed state)
const canAct = computed(() => {
    if (!displayedBattleState.value || displayedBattleState.value.status !== 'active' || !userPlayerRole.value) return false;
    return displayedBattleState.value.whose_turn === userPlayerRole.value;
});

// --- Computed: Stat Stages (Uses displayed state) ---
const userStatStages = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return {};
    return userPlayerRole.value === 'player1' 
        ? displayedBattleState.value.stat_stages_player1 
        : displayedBattleState.value.stat_stages_player2;
});

const opponentStatStages = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return {};
    const opponentRole = userPlayerRole.value === 'player1' ? 'player2' : 'player1';
    return displayedBattleState.value[`stat_stages_${opponentRole}`];
});

// --- Computed: Custom Statuses (Uses displayed state) ---
const userCustomStatuses = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return {};
    const fieldName = `custom_statuses_${userPlayerRole.value}`;
    return displayedBattleState.value[fieldName] || {}; 
});

const opponentCustomStatuses = computed(() => {
    if (!userPlayerRole.value || !displayedBattleState.value) return {};
    const opponentRole = userPlayerRole.value === 'player1' ? 'player2' : 'player1';
    const fieldName = `custom_statuses_${opponentRole}`;
    return displayedBattleState.value[fieldName] || {};
});

// --- Momentum Calculation (Uses displayed state) ---
const currentMomentumP1 = computed(() => displayedBattleState.value?.current_momentum_player1 ?? 0);
const currentMomentumP2 = computed(() => displayedBattleState.value?.current_momentum_player2 ?? 0);
const totalMomentum = computed(() => Math.max(100, currentMomentumP1.value + currentMomentumP2.value)); // Assume base total 100 if both 0?

// Calculate percentage for the *user's* momentum bar
const userMomentumPercent = computed(() => {
  if (!userPlayerRole.value) return 0;
  const userMomentum = userPlayerRole.value === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
  // Calculate based on a potential max (e.g., 100 or a dynamic value if needed)
  const maxMomentum = 100; // Or adjust as needed
  return clamp((userMomentum / maxMomentum) * 100, 0, 100);
});

const userMomentumStyle = computed(() => ({
  width: `${userMomentumPercent.value}%`
}));

// Calculate percentage for the *opponent's* momentum bar (display purposes)
const opponentMomentumPercent = computed(() => {
    if (!userPlayerRole.value) return 0;
    const opponentMomentum = userPlayerRole.value === 'player1' ? currentMomentumP2.value : currentMomentumP1.value;
    const maxMomentum = 100; // Or adjust as needed
    return clamp((opponentMomentum / maxMomentum) * 100, 0, 100);
});

// Available actions now come directly from the displayed battle data
const mySelectedAttacks = computed(() => {
    // Ensure attacks have unique keys if IDs might not be enough (though they should be)
    return (displayedBattleState.value?.my_selected_attacks || []).map((attack, index) => ({
        ...attack,
        key: `${attack.id}-${index}` // Simple unique key
    }));
});

// --- Methods ---
async function fetchBattleData() {
    isLoading.value = true;
    try {
        await gameStore.fetchBattleById(battleId.value);
        if (!gameStore.activeBattle || gameStore.activeBattle.id !== battleId.value) {
            console.error('Failed to load correct battle data or battle ended.');
        }
    } catch (error) {
        console.error('Error fetching battle data in view:', error);
    } finally {
        isLoading.value = false;
    }
}

// NEW: Handler for desktop grid click
function handleGridAttackClick(attack) {
    if (!submittingAction.value && canAct.value && attack?.id) {
        // console.log("Grid click, submitting:", attack.id);
        submitAction(attack.id);
    }
}

async function submitAction(attackIdToSubmit) {
    if (!attackIdToSubmit || !displayedBattleState.value || !canAct.value || submittingAction.value) return;
    
    submittingAction.value = true;
    selectedAttackPreview.value = null; // Clear preview immediately on submission
    const initialPlayerRole = userPlayerRole.value; 
    const opponentIsBot = opponentPlayer.value?.is_bot; // Check if opponent is bot (might be null initially)

    try {
        await gameStore.submitBattleAction(displayedBattleState.value.id, attackIdToSubmit);
        const finalBattleState = gameStore.activeBattle; 
        const turnSwitched = finalBattleState && finalBattleState.whose_turn !== initialPlayerRole;
        const battleEnded = finalBattleState && finalBattleState.status === 'finished';

        // Simplified delay: If the turn is no longer the user's (or battle ended), and opponent was a bot, delay slightly
        if (opponentIsBot && (turnSwitched || battleEnded)) {
            await delay(1500); // Slightly shorter delay?
        }
    } catch (error) {
        console.error("Error during battle action submission:", error);
        // Optionally clear preview on error too, or let user retry
    } finally {
        submittingAction.value = false; 
    }
}

async function handleConcede() {
    if (confirm("Are you sure you want to concede the battle?")) {
       await gameStore.concedeBattle(battleId.value);
    }
}

function startPolling() {
    if (pollingIntervalId) clearInterval(pollingIntervalId); 
    console.log('Starting battle polling...');
    pollingIntervalId = setInterval(() => {
        // Check displayedBattleState for status instead of gameStore directly?
        if (displayedBattleState.value && displayedBattleState.value.status === 'active') {
             gameStore.fetchBattleById(battleId.value).catch(err => {
                 console.error("Polling error:", err);
                 // Maybe stop polling on error?
                 stopPolling();
             });
        } else {
             console.log('Stopping polling, battle not active.');
             stopPolling();
        }
    }, POLLING_INTERVAL_MS);
}

function stopPolling() {
     if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
        pollingIntervalId = null;
        console.log('Battle polling stopped.');
     }
}

// --- NEW: Handle Emoji Click ---
function handleEmojiClick(attack) {
    if (canAct.value && !submittingAction.value) {
        selectedAttackPreview.value = attack;
        previewAttackCost(attack); // Show pendulum preview for the selected attack
    }
}

// --- NEW: Handle Preview Card Click ---
function handlePreviewCardClick() {
    if (selectedAttackPreview.value && canAct.value && !submittingAction.value) {
        submitAction(selectedAttackPreview.value.id);
    } else {
        // If not clickable (e.g., not user's turn), just clear the preview
        selectedAttackPreview.value = null;
        clearAttackCostPreview();
    }
}

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchBattleData(); 
  displayedBattleState.value = gameStore.activeBattle ? { ...gameStore.activeBattle } : null;
  displayedLogEntries.value = gameStore.activeBattle?.last_turn_summary ? [...gameStore.activeBattle.last_turn_summary] : [];
  
  if (displayedBattleState.value?.status === 'active') {
           startPolling();
  }
});

onUnmounted(() => {
  stopPolling();
  gameStore.clearMessages();
});

// --- Watchers (Simplified for now, complex log processing removed temporarily) ---
watch(() => battle.value, (newBattleState) => {
    // Directly update displayed state and logs from the store state
    // This avoids complex incremental processing for now
    displayedBattleState.value = newBattleState ? { ...newBattleState } : null;
    displayedLogEntries.value = newBattleState?.last_turn_summary ? [...newBattleState.last_turn_summary] : [];

    // Stop polling if status changes from active
    if (newBattleState?.status !== 'active' && pollingIntervalId) {
        stopPolling();
    }
    // Start polling if status becomes active and polling isn't running
    else if (newBattleState?.status === 'active' && !pollingIntervalId) {
        startPolling();
    }
    
    // Clear preview if it's no longer the user's turn
    if (newBattleState?.whose_turn !== userPlayerRole.value) {
        selectedAttackPreview.value = null;
        clearAttackCostPreview();
    }

}, { deep: true });

</script>

<template>
  <div class="battle-screen">
    <div v-if="isLoading && !displayedBattleState" class="loading-message">
      <p>Loading Battle...</p>
    </div>
    <div v-else-if="battleError && !displayedBattleState" class="error-container">
       <p class="error-message">Error: {{ battleError }}</p>
       <router-link :to="{ name: 'home' }" class="btn">Return Home</router-link>
    </div>
    <div v-else-if="displayedBattleState">

      <!-- Header -->
      <header class="battle-header panel">
          <h1>BATTLE ZONE</h1>
          <div class="battle-status">STATUS: <span :class="`status-${displayedBattleState.status}`">{{ displayedBattleState.status.toUpperCase() }}</span></div>
          <button 
            v-if="displayedBattleState.status === 'active'" 
            @click="handleConcede"
            :disabled="isConceding || submittingAction"
            class="btn btn-concede"
          >
            {{ isConceding ? '...' : 'CONCEDE' }}
          </button>
      </header>

      <!-- Main Display Area -->
      <div class="main-display">
          <!-- Opponent Info Panel -->
          <PlayerInfoCard
              :player="opponentPlayer"
              :currentHp="opponentCurrentHp"
              :maxHp="opponentPlayer?.hp" 
              :statStages="opponentStatStages"
              :customStatuses="opponentCustomStatuses"
              playerType="opponent"
              class="player-info opponent panel"
          />

          <!-- Momentum Display Panel -->
          <div class="momentum-display panel">
              <div class="momentum-label">MOMENTUM</div>
              <div class="momentum-meter">
                 <!-- Display user's momentum fill -->
                 <div class="momentum-fill user-momentum" :style="userMomentumStyle">
                    <span class="momentum-value">{{ userPlayerRole === 'player1' ? currentMomentumP1 : currentMomentumP2 }}</span> 
                 </div>
              </div>
          </div>

          <!-- User Info Panel -->
           <PlayerInfoCard
                :player="userPlayer"
                :currentHp="userCurrentHp"
                :maxHp="userPlayer?.hp"
                :statStages="userStatStages"
                :customStatuses="userCustomStatuses"
                playerType="user"
                :isCurrentUser="true"
                class="player-info user panel"
            />
      </div>

      <!-- Bottom Panels Area -->
      <div class="bottom-panels">
          <!-- Battle Log Panel -->
          <div class="battle-log panel">
              <div class="panel-title">BATTLE LOG</div>
              <BattleLog
                :logEntries="displayedLogEntries"
                :userPlayerRole="userPlayerRole"
                :player1Name="displayedBattleState.player1.username"
                :player2Name="displayedBattleState.player2.username"
                :battleId="displayedBattleState.id"
              />
          </div>

          <!-- Action Select Panel -->
          <div class="action-select panel">
               <div class="panel-title">CHOOSE ACTION</div>
               <div v-if="displayedBattleState.status === 'active' && userPlayer">
                   <AttackGrid
                      v-if="canAct && mySelectedAttacks.length > 0"
                      :attacks="mySelectedAttacks"
                      :isSubmitting="submittingAction"
                      @attackClick="handleGridAttackClick"
                      class="action-grid"
                   />
                   <div v-else-if="!canAct" class="waiting-message">WAITING...</div>
                   <div v-else class="waiting-message">NO ATTACKS?</div>
               </div>
               <div v-else class="action-placeholder">
                    <!-- Placeholder for non-active state -->
                    <p>...</p>
               </div>
          </div>
      </div>

       <!-- Finished State Overlay -->
       <div v-if="displayedBattleState.status === 'finished'" class="battle-finished-overlay">
          <h2>Battle Over!</h2>
          <p v-if="displayedBattleState.winner?.id === currentUser?.id" class="win-message">🎉 You won! 🎉</p>
          <p v-else-if="displayedBattleState.winner" class="lose-message">😢 {{ displayedBattleState.winner.username }} won! 😢</p>
          <p v-else class="draw-message">The battle ended unexpectedly.</p>
          <router-link :to="{ name: 'home' }" class="btn return-home-button">Return Home</router-link>
       </div>

    </div>
    <div v-else class="loading-message">
        <p>Could not load battle information.</p>
         <router-link :to="{ name: 'home' }" class="btn">Return Home</router-link>
    </div>
  </div>
</template>


<style scoped>
/* Import font if not global - better in index.html or main.css */
/* @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap'); */

/* Apply base variables */
.battle-screen {
    max-width: 1000px;
    margin: 10px auto; /* Reduced margin */
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: var(--element-gap);
}

.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding);
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border); /* Inner border + outer pixel shadow */
    border-radius: 0; /* Ensure no radius */
}

.panel-title {
    font-size: 1.2em; 
    color: var(--color-accent-secondary);
    margin: -10px -10px 10px -10px; /* Adjust margins to stretch */
    padding: 5px 10px; /* Adjust padding */
    text-align: center;
    border-bottom: var(--border-width) solid var(--color-border);
    text-transform: uppercase;
    background-color: var(--color-border); /* Title background */
    color: var(--color-text); /* Title text color */
    box-shadow: inset 0 0 0 1px var(--color-panel-bg); /* Inner highlight */
}

.btn {
    font-family: var(--font-primary);
    font-size: 0.9em;
    padding: 8px 12px;
    border: var(--border-width) solid var(--color-border);
    background-color: var(--color-accent-secondary);
    color: var(--color-panel-bg);
    cursor: pointer;
    text-align: center;
    transition: background-color 0.2s ease, color 0.2s ease, transform 0.1s ease;
    box-shadow: 2px 2px 0px var(--color-border); /* Pixel shadow */
    text-transform: uppercase;
}

.btn:hover {
    background-color: var(--color-text);
    color: var(--color-bg);
}

.btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px var(--color-border);
}

.btn:disabled {
    background-color: var(--color-border); 
    color: #555; 
    cursor: not-allowed;
    opacity: 0.7;
    box-shadow: 1px 1px 0px #000; 
    transform: none;
}

.btn-concede {
    background-color: var(--color-accent);
    color: var(--color-text);
}
.btn-concede:hover:not(:disabled) {
    background-color: #c0392b; /* Darker red */
    color: var(--color-text);
}

/* --- Layout Specific --- */
.battle-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px var(--panel-padding); /* Reduced padding */
    margin-bottom: 0; /* Remove bottom margin if needed */
}

.battle-header h1 {
    font-size: 1.4em;
    color: var(--color-accent);
    margin: 0;
}

.battle-status {
    font-size: 1em;
}

.battle-status .status-active {
    color: var(--color-hp-high);
    font-weight: bold; 
}
.battle-status .status-finished { color: var(--color-log-system); }
/* Add other status colors if needed */

.main-display {
    display: flex;
    justify-content: space-between;
    align-items: stretch; 
    gap: calc(var(--element-gap) * 2); 
    margin-top: var(--element-gap); /* Add margin above */
    margin-bottom: var(--element-gap); /* Add margin below */
}

.player-info {
    flex: 1 1 30%; /* Allow shrinking/growing */
    min-width: 200px; /* Prevent extreme squishing */
}

.momentum-display {
    flex: 1 1 25%; 
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center; 
    min-width: 150px;
    gap: 8px; /* Add gap for spacing */
}

.momentum-label {
    font-size: 1em;
    color: var(--color-text);
    text-transform: uppercase;
}
.momentum-meter {
    height: 25px; /* Slightly taller bar */
    background-color: #333;
    border: 1px solid var(--color-border);
    position: relative; 
    overflow: hidden; 
    padding: 1px; /* Padding for fill */
    box-shadow: inset 1px 1px 0px rgba(0,0,0,0.5); /* Inner shadow */
}
.momentum-fill {
    position: absolute;
    top: 1px; /* Position within padding */
    left: 1px;
    bottom: 1px;
    /* height controlled by top/bottom/parent */
    width: var(--momentum-percent, 0%); /* Controlled by inline style */
    transition: width 0.5s ease-in-out;
    display: flex;
    align-items: center;
    justify-content: center; 
}
.momentum-fill.user-momentum {
    background: var(--color-momentum-user); /* Solid color, remove gradient */
    color: var(--color-bg); /* Ensure contrast */
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2); /* Optional highlight */
}
.momentum-value {
    font-size: 0.9em;
    font-weight: normal; /* No bold for pixel font */
    mix-blend-mode: difference; /* Keep this for visibility */
    color: white; /* Ensure visible with mix-blend */
}


.bottom-panels {
    display: flex;
    gap: var(--element-gap);
}

.battle-log,
.action-select {
    display: flex; /* Use flex for internal layout */
    flex-direction: column;
}

.battle-log {
    flex: 1; 
    min-width: 300px;
}

.action-select {
    flex-basis: 45%;
    min-width: 250px;
}

.action-grid {
    flex-grow: 1; /* Allow grid to fill space */
    overflow-y: auto; /* Scroll if needed */
    margin-top: 5px;
}

.waiting-message,
.action-placeholder p {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--color-log-system);
    font-style: italic;
    font-size: 1em;
    text-transform: uppercase;
}

/* Battle Finished Overlay */
.battle-finished-overlay {
  position: fixed; /* Use fixed to cover whole screen */
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 20px;
  background-color: rgba(var(--color-bg-rgb, 26, 26, 46), 0.9); /* Use rgba from variable if available, fallback */
  z-index: 100; 
  font-family: var(--font-primary);
  color: var(--color-text);
}
.battle-finished-overlay h2 {
    font-size: 2em;
    margin-bottom: 15px;
    color: var(--color-accent);
    text-transform: uppercase;
}
.battle-finished-overlay p {
    font-size: 1.2em;
    margin-bottom: 20px;
    line-height: 1.4;
}
.battle-finished-overlay .win-message { color: var(--color-hp-high); font-weight: normal; }
.battle-finished-overlay .lose-message { color: var(--color-accent); font-weight: normal; }
.battle-finished-overlay .draw-message { color: var(--color-log-system); }
.return-home-button { 
    font-size: 1.1em;
    padding: 10px 20px;
}

/* --- Remove Old Responsive Styles --- */
/* @media (min-width: 768px) { ... } */
/* @media (max-width: 768px) { ... } */
/* @media (max-width: 480px) { ... } */

/* Ensure the new responsive rules are applied if needed */
@media (max-width: 800px) { /* Adjust breakpoint as needed */
    .battle-screen {
        padding: 5px; /* Reduce padding on small screens */
        gap: 5px;
        margin: 5px auto;
    }

    .battle-header {
        flex-direction: column; /* Stack header items */
        gap: 5px;
        text-align: center;
        padding: 8px; 
    }
    .battle-header h1 {
        font-size: 1.2em;
    }
    .battle-header .btn-concede {
        font-size: 0.8em;
        padding: 6px 10px;
    }

    .main-display {
        flex-direction: column;
        align-items: stretch;
        gap: 5px;
    }
    
    /* Ensure player info cards take full width when stacked */
    .player-info {
        flex-basis: auto; 
        min-width: initial; /* Remove min-width */
    }

    .momentum-display {
        flex-basis: auto;
        min-width: initial;
        order: -1; /* Move momentum display up visually */
        padding: 10px;
    }

     .bottom-panels {
        flex-direction: column;
        gap: 5px;
        min-height: initial; /* Remove fixed min-height */
    }
    
    .battle-log, .action-select {
        flex-basis: auto;
        min-width: initial; 
    }

    .battle-log {
        /* Maybe limit height and allow scroll */
        max-height: 300px; 
        min-height: 150px;
        padding: 5px;
    }
    .action-select {
        min-height: 200px; /* Ensure action area has some height */
        padding: 5px;
    }

    .action-grid {
         grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); /* Smaller min size */
         gap: 5px;
    }
    
    .panel {
        padding: 10px;
    }

    .panel-title {
        font-size: 1em;
    }

    .battle-finished-overlay h2 { font-size: 1.8em; }
    .battle-finished-overlay p { font-size: 1em; }
}

</style> 