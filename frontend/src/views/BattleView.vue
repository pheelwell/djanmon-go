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

// --- Momentum Calculation (Refactored for Active Player) ---
const currentMomentumP1 = computed(() => displayedBattleState.value?.current_momentum_player1 ?? 0);
const currentMomentumP2 = computed(() => displayedBattleState.value?.current_momentum_player2 ?? 0);

// Determine whose turn it is
const activePlayerRole = computed(() => displayedBattleState.value?.whose_turn);

// Get the momentum value of the active player
const activePlayerMomentumValue = computed(() => {
    if (!activePlayerRole.value) return 0;
    return activePlayerRole.value === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
});

// Calculate the momentum percentage for the active player
const activePlayerMomentumPercent = computed(() => {
    const maxMomentum = 100; // Assuming max 100 for now
    return clamp((activePlayerMomentumValue.value / maxMomentum) * 100, 0, 100);
});

// Style object for the momentum bar fill
const activeMomentumBarStyle = computed(() => ({
  width: `${activePlayerMomentumPercent.value}%`
}));

// Class object for the momentum bar fill (user vs opponent color)
const activeMomentumBarClass = computed(() => {
    if (!activePlayerRole.value) return 'momentum-fill'; // Default
    const isUserTurn = activePlayerRole.value === userPlayerRole.value;
    return [
        'momentum-fill',
        isUserTurn ? 'user-momentum' : 'opponent-momentum'
    ];
});

// --- Old Momentum Computeds (Keep if needed elsewhere, otherwise remove) ---
/*
const totalMomentum = computed(() => Math.max(100, currentMomentumP1.value + currentMomentumP2.value)); 
const userMomentumPercent = computed(() => { ... });
const userMomentumStyle = computed(() => ({ ... }));
const opponentMomentumPercent = computed(() => { ... });
*/

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
          <!-- Momentum Display Panel -->
          <div class="momentum-display panel">
              <div class="momentum-label">MOMENTUM</div>
              <div class="momentum-meter">
                 <div 
                    :class="activeMomentumBarClass" 
                    :style="activeMomentumBarStyle"
                 >
                    <span class="momentum-value">{{ activePlayerMomentumValue }}</span> 
                 </div>
              </div>
          </div>

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
               <div class="panel-title">
                   {{ displayedBattleState.status === 'finished' ? 'BATTLE OVER' : 'CHOOSE ACTION' }}
               </div>

               <!-- Normal Action Area (Hidden when finished) -->
                <div v-if="displayedBattleState.status !== 'finished'">
                    <!-- DESKTOP: Existing Attack Grid -->
                    <div class="action-area-desktop">
                        <div v-if="displayedBattleState.status === 'active' && userPlayer">
                        <AttackGrid 
                                v-if="mySelectedAttacks.length > 0"
                            :attacks="mySelectedAttacks" 
                                :disabled="!canAct || submittingAction"
                                @attackClick="handleGridAttackClick"
                                class="action-grid"
                            />
                            <div v-else-if="!canAct && mySelectedAttacks.length === 0" class="waiting-message">WAITING...</div>
                            <div v-else-if="mySelectedAttacks.length === 0" class="waiting-message">NO ATTACKS?</div>
                    </div>
                        <div v-else class="action-placeholder">
                            <p>...</p>
                        </div>
                    </div>

                    <!-- MOBILE: New Action Area -->
                    <div class="action-area-mobile">
                        <div v-if="displayedBattleState.status === 'active' && userPlayer && canAct">
                            <!-- Mobile: Single Attack Preview Area -->
                            <div class="mobile-attack-preview" :class="{ 'has-preview': selectedAttackPreview }">
                                <AttackCardDisplay
                                    v-if="selectedAttackPreview"
                                    :attack="selectedAttackPreview"
                                    @click="handlePreviewCardClick"
                                    class="preview-card"
                                    :class="{ 'clickable': canAct && !submittingAction }"
                                />
                                <div v-else class="preview-placeholder">Select an attack below</div>
                            </div>

                            <!-- Mobile: Emoji Buttons -->
                            <div class="mobile-emoji-buttons" v-if="mySelectedAttacks.length > 0">
                                <button
                                    v-for="attack in mySelectedAttacks"
                                    :key="attack.key"
                                    @click="handleEmojiClick(attack)"
                                    :disabled="!canAct || submittingAction"
                                    :class="{ 'selected-preview': selectedAttackPreview?.id === attack.id }"
                                    class="emoji-button"
                                >
                                    {{ attack.emoji || '⚔️' }}
                                </button>
                            </div>
                            <div v-else-if="mySelectedAttacks.length === 0" class="waiting-message">NO ATTACKS?</div>

                        </div>
                        <div v-else-if="displayedBattleState.status === 'active' && !canAct" class="waiting-message">WAITING...</div>
                        <div v-else class="action-placeholder">
                            <p>...</p>
                        </div>
                    </div>
                </div>

                <!-- Finished State Content (Shown only when finished) -->
                <div v-if="displayedBattleState.status === 'finished'" class="battle-finished-content">
                    <p v-if="displayedBattleState.winner?.id === currentUser?.id" class="win-message">🎉 You won! 🎉</p>
                    <p v-else-if="displayedBattleState.winner" class="lose-message">😢 {{ displayedBattleState.winner.username }} won! 😢</p>
                    <p v-else class="draw-message">The battle ended unexpectedly.</p>
                    <router-link :to="{ name: 'home' }" class="btn return-home-button">Return Home</router-link>
                </div>
          </div>
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
    background: var(--color-momentum-user); /* Solid color */
    color: var(--color-bg); 
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2);
}
.momentum-fill.opponent-momentum {
    background: var(--color-momentum-opponent); /* Opponent color */
    color: var(--color-bg); 
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2);
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

/* Style for the new content block inside action panel */
.battle-finished-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    flex-grow: 1; /* Take space in the panel */
    padding: 15px 10px;
    gap: 15px;
}
.battle-finished-content p {
    font-size: 1.2em;
    line-height: 1.4;
    margin: 0;
    font-family: var(--font-primary);
}
.battle-finished-content .win-message { color: var(--color-hp-high); }
.battle-finished-content .lose-message { color: var(--color-accent); }
.battle-finished-content .draw-message { color: var(--color-log-system); }
.battle-finished-content .return-home-button { 
    font-size: 1.1em;
    padding: 10px 20px;
}

/* Add this OUTSIDE any media query */
.action-area-mobile {
    display: none;
}

/* --- Remove Old Responsive Styles --- */
/* @media (min-width: 768px) { ... } */
/* @media (max-width: 768px) { ... } */
/* @media (max-width: 480px) { ... } */

/* Ensure the new responsive rules are applied if needed */
@media (max-width: 800px) { 
    /* --- Fullscreen Mobile Layout --- */
    .battle-screen {
        display: flex;
        flex-direction: column;
        height: 100vh; /* Full viewport height */
        /* Consider using 100dvh for better mobile browser handling */
        width: 100%;
        max-width: none;
        margin: 0;
        padding: 0; /* Padding goes inside children now */
        box-sizing: border-box;
        background-color: var(--color-bg); /* Ensure bg covers screen */
        gap: 0; /* Remove gap, manage spacing internally */
    }

    .battle-header {
        order: 0;
        flex-shrink: 0; /* Don't shrink header */
        padding: 5px 8px; /* Inner padding */
        border-bottom: var(--border-width) solid var(--color-border); /* Add separator */
        /* Reset potentially conflicting styles */
        margin: 0;
        text-align: center;
        gap: 3px;
    }
    .battle-header h1 { font-size: 1.1em; }
    .battle-header .btn-concede { font-size: 0.8em; padding: 4px 8px; }

    .main-display {
        order: 1;
        flex-shrink: 0; /* Don't shrink player info area */
        padding: 5px 8px; /* Horizontal padding */
        display: flex;
        flex-direction: column;
        gap: 5px; /* Internal gap for player/momentum */
    }
    /* Ensure player-info order is correct within main-display */
    .main-display .player-info { order: initial; margin: 0; flex-basis: auto; min-width: initial; } /* Reset overrides */
    .main-display .player-info.opponent { order: 1; }
    .main-display .momentum-display { order: 2; padding: 5px; margin: 0; flex-basis: auto; min-width: initial; } /* Reset overrides */
    .main-display .player-info.user { order: 3; }


    /* No longer need specific layout rules for bottom-panels wrapper */
    .bottom-panels { display: contents; } /* Make wrapper 'invisible' to flex layout */

    .battle-log {
        order: 2; /* After main display */
        flex-grow: 1; /* Fill remaining space */
        overflow-y: auto; /* Scroll log content */
        min-height: 0; /* Important for flex-grow to work */
        padding: 8px; /* Inner padding */
        border-top: var(--border-width) solid var(--color-border); 
        border-bottom: var(--border-width) solid var(--color-border); 
        /* Reset potential conflicts */
        flex-basis: auto;
        margin: 0;
    }
    
    .action-select {
        order: 3; /* Last visually */
        flex-shrink: 0; /* Don't shrink action area */
        width: 100%; 
        padding: 8px; /* Inner padding */
        background-color: var(--color-panel-bg); /* Needs own background */
        box-sizing: border-box; 
        /* Reset potential conflicts */
        margin: 0;
        display: flex; /* Ensure title+content stack */
        flex-direction: column;
        min-height: initial; /* Remove min height */
    }

    /* --- Show/Hide Desktop vs Mobile Action Area --- */
    .action-area-desktop { display: none; } 
    .action-area-mobile {
        display: flex; /* Overrides default 'none' */
        flex-direction: column;
        align-items: center;
        gap: 8px; /* Restore slightly larger gap */
        padding: 5px 0 0 0; /* Padding top, remove others */
        width: 100%;
        flex-grow: 1; 
    }

    /* --- Mobile Attack Preview Styling (Restore size slightly) --- */
    .mobile-attack-preview {
        width: 100%;
        max-width: 180px; 
        min-height: 140px; 
        padding: 5px; 
        margin-bottom: 5px; 
         /* Reset border etc. */
        border: 1px dashed var(--color-border);
        box-sizing: border-box;
        display: flex; 
        justify-content: center; 
        align-items: center; 
    }
    .mobile-attack-preview.has-preview { border-color: transparent; padding: 0; }
    .mobile-attack-preview .preview-placeholder { font-size: 0.9em; }
    .mobile-attack-preview .preview-card { min-height: 140px; cursor: default; width: 100%; height: auto;}
    .mobile-attack-preview .preview-card.clickable { cursor: pointer; }
    .mobile-attack-preview .preview-card.clickable:hover > .attack-card-content { 
        /* ... hover styles ... */  
    }

    /* --- Mobile Emoji Button Styling (Restore size slightly) --- */
    .mobile-emoji-buttons {
        display: flex;
        flex-wrap: wrap; 
        justify-content: center;
        gap: 8px; 
        padding: 5px 0;
        width: 100%;
    }
    .emoji-button {
        font-size: 1.8em; 
        padding: 5px;
        min-width: 40px; 
        min-height: 40px;
         /* Reset other styles if needed */
        border: 1px solid var(--color-border);
        background-color: var(--color-panel-bg);
        color: var(--color-text);
        cursor: pointer;
        display: inline-flex;
        justify-content: center;
        align-items: center;
        line-height: 1;
        box-shadow: 1px 1px 0px var(--color-border);
        transition: transform 0.1s ease, box-shadow 0.1s ease, background-color 0.2s ease;
        border-radius: 0; 
    }
    /* ... other emoji button styles ... */

    .action-grid { display: none !important; }

    .action-area-mobile .waiting-message {
        padding: 15px 0; /* Restore some padding */
        font-size: 1em;
         /* ... other styles ... */
        text-align: center;
        flex-grow: 1; 
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* General panel styling */
    .panel { 
        padding: 8px; 
        /* Remove margin/border settings if handled by containers now */
        margin: 0;
        border: none; /* Borders handled by containers */
        box-shadow: none; /* Shadows handled by containers */
        background-color: transparent; /* Use container bg */
    }
     /* Special panel styling for those needing own background/border */
    .player-info.panel,
    .momentum-display.panel {
        background-color: var(--color-panel-bg);
        border: var(--border-width) solid var(--color-border);
        box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
        padding: 8px;
    }
    
    .panel-title {
        font-size: 1em; /* Restore size */
        margin: -8px -8px 8px -8px; /* Adjust for padding */
        padding: 5px 10px; /* Restore padding */
        /* Ensure title styles are suitable */
        border-bottom: var(--border-width) solid var(--color-border);
        text-transform: uppercase;
        background-color: var(--color-border);
        color: var(--color-text);
        box-shadow: inset 0 0 0 1px var(--color-panel-bg);
    }
    /* Remove title from action-select if it looks odd fixed at bottom */
    /* .action-select > .panel-title { display: none; } */

    .battle-finished-content p {
        font-size: 1em;
    }
    .battle-finished-content .return-home-button { 
        font-size: 1em;
        padding: 8px 15px;
    }

    /* Ensure panel overrides apply on mobile too */
    .battle-header.panel,
    .momentum-display.panel {
        background-color: transparent;
        border: none;
        box-shadow: none;
        padding: 5px 8px; /* Consistent padding */
        /* Remove border-bottom added specifically for mobile header if needed */
        border-bottom: none; 
    }

    .main-display .momentum-display {
        /* Remove panel styles inherited from the general mobile rule */
        background-color: transparent !important; /* Use important if needed */
        border: none !important;
        box-shadow: none !important;
        padding: 5px !important; /* Keep specific padding */
    }

    /* Special panel styling for those needing own background/border */
    /* Remove momentum display from this rule */
    .player-info.panel
    /* Removed: ,.momentum-display.panel */
     {
        background-color: var(--color-panel-bg);
        border: var(--border-width) solid var(--color-border);
        box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
        padding: 8px;
    }
}

/* Remove panel styling from header and momentum display */
.battle-header.panel,
.momentum-display.panel {
    background-color: transparent;
    border: none;
    box-shadow: none;
    padding: 5px 8px; /* Adjust padding as needed */
}

/* Adjust title styling if it was relying on panel background */
.battle-header .panel-title, /* Titles within these transparent panels */
.momentum-display .panel-title {
     /* Example: Remove title background if it looks odd */
     /* background-color: transparent; */
     /* border-bottom: none; */ 
     /* Add a margin-bottom if needed */
     /* margin-bottom: 10px; */
     /* Keep existing title text color etc */
}

/* General panel styling for others */
.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding);
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border); 
    border-radius: 0; 
}

</style> 