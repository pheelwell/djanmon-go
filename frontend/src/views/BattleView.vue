<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import AttackGrid from '@/components/AttackGrid.vue';
import PlayerInfoCard from '@/components/PlayerInfoCard.vue';
import BattleLog from '@/components/BattleLog.vue';

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
const selectedAttackId = ref(null);
const submittingAction = ref(false);
const isConceding = computed(() => gameStore.isConceding);
let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 1000;
const MOMENTUM_THRESHOLD = 50; // Threshold for pendulum swing based on current turn momentum

// --- Computed properties from Stores ---
const battle = computed(() => gameStore.activeBattle);
const currentUser = computed(() => authStore.currentUser);
const battleError = computed(() => gameStore.battleError);
const battleMessage = computed(() => gameStore.battleMessage);
const battleLogEntries = computed(() => battle.value?.last_turn_summary || []);

// Determine player roles and opponent
const userPlayerRole = computed(() => {
    if (!battle.value || !currentUser.value) return null;
    if (battle.value.player1.id === currentUser.value.id) return 'player1';
    if (battle.value.player2.id === currentUser.value.id) return 'player2';
    return null;
});

const userPlayer = computed(() => {
    if (!userPlayerRole.value || !battle.value) return null;
    return battle.value[userPlayerRole.value];
});

const opponentPlayer = computed(() => {
    if (!userPlayerRole.value || !battle.value) return null;
    return userPlayerRole.value === 'player1' ? battle.value.player2 : battle.value.player1;
});

const userCurrentHp = computed(() => {
    if (!userPlayerRole.value || !battle.value) return 0;
    return userPlayerRole.value === 'player1' ? battle.value.current_hp_player1 : battle.value.current_hp_player2;
});

const opponentCurrentHp = computed(() => {
    if (!userPlayerRole.value || !battle.value) return 0;
    return userPlayerRole.value === 'player1' ? battle.value.current_hp_player2 : battle.value.current_hp_player1;
});

// Check if it's user's turn to act
const canAct = computed(() => {
    if (!battle.value || battle.value.status !== 'active' || !userPlayerRole.value) return false;
    // Check the whose_turn field directly
    return battle.value.whose_turn === userPlayerRole.value;
});

// --- Computed: Stat Stages ---
const userStatStages = computed(() => {
    if (!userPlayerRole.value || !battle.value) return {};
    return userPlayerRole.value === 'player1' 
        ? battle.value.stat_stages_player1 
        : battle.value.stat_stages_player2;
});

const opponentStatStages = computed(() => {
    if (!userPlayerRole.value || !battle.value) return {};
    const opponentRole = userPlayerRole.value === 'player1' ? 'player2' : 'player1';
    return battle.value[`stat_stages_${opponentRole}`];
});

// --- Computed: Custom Statuses (Ensure these exist) ---
const userCustomStatuses = computed(() => {
    if (!userPlayerRole.value || !battle.value) return {};
    // CORRECT: Get statuses directly from battle object based on role
    const fieldName = `custom_statuses_${userPlayerRole.value}`;
    return battle.value[fieldName] || {}; 
});

const opponentCustomStatuses = computed(() => {
    if (!userPlayerRole.value || !battle.value) return {};
    const opponentRole = userPlayerRole.value === 'player1' ? 'player2' : 'player1';
    // CORRECT: Get statuses directly from battle object based on role
    const fieldName = `custom_statuses_${opponentRole}`;
    return battle.value[fieldName] || {};
});

// --- Momentum Calculation --- (REWORKED for Pendulum)
const currentMomentumP1 = computed(() => battle.value?.current_momentum_player1 ?? 0);
const currentMomentumP2 = computed(() => battle.value?.current_momentum_player2 ?? 0);
const totalMomentum = computed(() => Math.max(1, currentMomentumP1.value + currentMomentumP2.value)); // Avoid division by zero

// Normalized value [0, 1] where 1 means P1 has all momentum
const normalizedMomentumP1 = computed(() => currentMomentumP1.value / totalMomentum.value);

// Determine pendulum angle/position based on normalized value
// Range: e.g., -90 degrees (all P2) to +90 degrees (all P1)
const PENDULUM_MAX_ANGLE = 75; // Max tilt angle

// Calculate angle based on the *current acting player's* momentum
const pendulumAngle = computed(() => {
    if (!battle.value || !battle.value.whose_turn) return 0;
    
    const turnRole = battle.value.whose_turn;
    const currentMomentum = turnRole === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
    
    // Scale momentum more directly - let higher momentum swing further
    // We might need a reference max momentum, but let's assume MOMENTUM_THRESHOLD represents the 'full swing' point for now.
    // Allow swing beyond the threshold visually up to the max angle.
    const scaledMomentum = currentMomentum / MOMENTUM_THRESHOLD; // Can exceed 1
    const angleScale = clamp(scaledMomentum, 0, 1.5); // Allow some overswing visually, clamped at 1.5x threshold? Adjust as needed.

    // Base angle: Positive if P1 turn, Negative if P2 turn
    let angle = angleScale * PENDULUM_MAX_ANGLE * (turnRole === 'player1' ? 1 : -1);
    // Clamp the final angle to the max physical swing
    angle = clamp(angle, -PENDULUM_MAX_ANGLE, PENDULUM_MAX_ANGLE);

    // Perspective inversion for viewer
    if (userPlayerRole.value === 'player2') {
        angle = -angle;
    }
    
    return angle;
});

// Style object for the pendulum element
const pendulumStyle = computed(() => ({
  transform: `rotate(${pendulumAngle.value}deg)`
}));

// Determine whose side the pendulum is leaning towards for styling
const pendulumSide = computed(() => {
    if (!battle.value || !battle.value.whose_turn) return 'center';
    return battle.value.whose_turn === userPlayerRole.value ? 'user' : 'opponent';
});

// Available actions now come directly from the battle data
const mySelectedAttacks = computed(() => {
    // Filter attacks to only show those the user has enough momentum for?
    // Or just display cost and let user try? Let's just display for now.
    return battle.value?.my_selected_attacks || [];
});

// --- Ghost Preview State ---
const hoveredAttackCost = ref(null); // { min: X, max: Y }
const ghostMinAngle = ref(0);
const ghostMaxAngle = ref(0);
const ghostMinMomentumValue = ref(0); // Momentum value for the player *after* min cost
const ghostMaxMomentumValue = ref(0); // Momentum value for the player *after* max cost
const ghostMinTurnSwitch = ref(false); // Will turn switch if min cost applied?
const ghostMaxTurnSwitch = ref(false); // Will turn switch if max cost applied?

// Calculate ghost states when hovering
function calculateGhostState(cost) {
    const turnRole = userPlayerRole.value; // Calculate based on user trying the action
    const currentMomentum = turnRole === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
    const opponentRole = turnRole === 'player1' ? 'player2' : 'player1';
    const opponentMomentum = opponentRole === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;

    let resultingMomentum, resultingOpponentMomentum, turnWillSwitch;
    let nextTurnRole;

    if (currentMomentum >= cost) {
        resultingMomentum = currentMomentum - cost;
        resultingOpponentMomentum = opponentMomentum;
        turnWillSwitch = false;
        nextTurnRole = turnRole; // Turn stays with current player
    } else {
        const overflow = cost - currentMomentum;
        resultingMomentum = 0;
        resultingOpponentMomentum = opponentMomentum + overflow;
        turnWillSwitch = true;
        nextTurnRole = opponentRole; // Turn switches to opponent
    }

    // Calculate angle based on the player whose turn it *would* be
    const momentumForAngle = turnWillSwitch ? resultingOpponentMomentum : resultingMomentum;
    const scaledMomentum = clamp(momentumForAngle / MOMENTUM_THRESHOLD, 0, 1.2);
    let angleRaw = scaledMomentum * PENDULUM_MAX_ANGLE * (nextTurnRole === 'player1' ? 1 : -1);

    // Apply perspective inversion
    let finalAngle = (userPlayerRole.value === 'player2') ? -angleRaw : angleRaw;

    return { 
        angle: finalAngle,
        resultingMomentum: turnWillSwitch ? resultingOpponentMomentum : resultingMomentum, // Momentum of player whose turn it becomes
        turnSwitch: turnWillSwitch 
    };
}

// Update hover state
function previewAttackCost(action) { 
    if (!canAct.value || !action || action.calculated_min_cost === undefined) {
        clearAttackCostPreview();
        return;
    }
    
    hoveredAttackCost.value = {
        min: action.calculated_min_cost,
        max: action.calculated_max_cost,
        attackId: action.id // Store ID to match tooltip
    };

    // Calculate ghost states
    const minState = calculateGhostState(hoveredAttackCost.value.min);
    const maxState = calculateGhostState(hoveredAttackCost.value.max);

    ghostMinAngle.value = minState.angle;
    ghostMinMomentumValue.value = minState.resultingMomentum;
    ghostMinTurnSwitch.value = minState.turnSwitch;

    ghostMaxAngle.value = maxState.angle;
    ghostMaxMomentumValue.value = maxState.resultingMomentum;
    ghostMaxTurnSwitch.value = maxState.turnSwitch;
}

function clearAttackCostPreview() {
    hoveredAttackCost.value = null;
}

// Helper computed styles for ghosts
const ghostMinStyle = computed(() => ({ transform: `rotate(${ghostMinAngle.value}deg)` }));
const ghostMaxStyle = computed(() => ({ transform: `rotate(${ghostMaxAngle.value}deg)` }));

// Display value for main pendulum
const currentTurnMomentum = computed(() => {
     if (!battle.value || !battle.value.whose_turn) return 0;
     return battle.value.whose_turn === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
});

// --- END Pendulum Logic ---

// Helper delay function
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// --- Methods ---
async function fetchBattleData() {
    isLoading.value = true;
    try {
        await gameStore.fetchBattleById(battleId.value);
        if (!gameStore.activeBattle || gameStore.activeBattle.id !== battleId.value) {
            console.error('Failed to load correct battle data or battle ended.');
            // router.push({ name: 'home' });
        }
    } catch (error) {
        console.error('Error fetching battle data in view:', error);
    } finally {
        isLoading.value = false;
    }
}

async function submitAction() {
    if (!selectedAttackId.value || !battle.value || !canAct.value) return;
    
    submittingAction.value = true;
    const initialPlayerRole = userPlayerRole.value; // Store who acted
    const opponentIsBot = opponentPlayer.value?.is_bot;

    try {
        // The store action handles updating the battle state
        await gameStore.submitBattleAction(battle.value.id, selectedAttackId.value);

        // Check the state *after* the action is complete
        const finalBattleState = gameStore.activeBattle; // Get the updated state

        // --- Add Delay Logic ---
        // Check if the opponent is a bot AND either:
        // 1. The turn switched away from the initial player 
        //    (meaning the opponent, the bot, potentially took a turn)
        // 2. The battle ended (meaning the bot might have taken the final turn)
        const turnSwitched = finalBattleState && finalBattleState.whose_turn !== initialPlayerRole;
        const battleEnded = finalBattleState && finalBattleState.status === 'finished';

        if (opponentIsBot && (turnSwitched || battleEnded)) {
            console.log('Bot acted, adding frontend delay...');
            await delay(2000); // Wait for 2 seconds
        }
        // --- End Delay Logic ---

    } catch (error) {
        // Error is already handled by the store, just log maybe
        console.error("Error during battle action submission:", error);
    } finally {
        selectedAttackId.value = null; // Reset selection
        submittingAction.value = false; // Re-enable controls
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
        if (battle.value && battle.value.status === 'active') {
             console.log('Polling for battle updates...');
             gameStore.fetchBattleById(battleId.value).catch(err => {
                 console.error("Polling error:", err);
             });
        } else {
             console.log('Stopping polling, battle not active.');
             clearInterval(pollingIntervalId);
             pollingIntervalId = null;
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

// Function to handle attack selection from card click
function selectAttack(attackId) {
    if (!submittingAction.value && canAct.value) {
        selectedAttackId.value = attackId;
    }
}

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchBattleData(); 
  if (battle.value) {
       if (battle.value.status === 'active') {
           startPolling();
       }
  }
});

onUnmounted(() => {
  stopPolling();
  gameStore.clearMessages();
});

// --- Watchers ---
watch(() => battle.value?.status, (newStatus) => {
    if (newStatus === 'finished' || newStatus === 'declined') {
        stopPolling();
    }
});

</script>

<template>
  <div class="battle-container">
    <div v-if="isLoading && !battle">
      <p>Loading Battle...</p>
    </div>
    <div v-else-if="battleError && !battle">
       <p class="error-message">Error: {{ battleError }}</p>
       <router-link :to="{ name: 'home' }">Return Home</router-link>
    </div>
    <div v-else-if="battle">
      <div class="header-controls">
        <p>Status: <span :class="`status-${battle.status}`">{{ battle.status }}</span></p>
         <button 
            v-if="battle.status === 'active'" 
            @click="handleConcede"
            :disabled="isConceding || submittingAction"
            class="concede-button"
         >
            {{ isConceding ? 'Conceding...' : 'Concede' }}
         </button>
      </div>
      
      <!-- Player Info Display (UPDATED) -->
      <div class="players-display">
          <!-- User Card -->
          <PlayerInfoCard
              v-if="userPlayer"
              :player="userPlayer"
              :currentHp="userCurrentHp"
              :statStages="userStatStages"
              :customStatuses="userCustomStatuses"
              playerType="user"
              :isCurrentUser="true"
          />
          <div v-else class="player-card placeholder">Loading...</div>

           <div class="vs-separator">VS</div>

           <!-- Opponent Card -->
           <PlayerInfoCard
              v-if="opponentPlayer"
              :player="opponentPlayer"
              :currentHp="opponentCurrentHp"
              :statStages="opponentStatStages"
              :customStatuses="opponentCustomStatuses"
              playerType="opponent"
          />
           <div v-else class="player-card placeholder">Loading...</div>
      </div>

      <!-- === UPDATED Pendulum Display === -->
      <div class="momentum-pendulum-container">
          <div class="pendulum-pivot"></div>
          <!-- Dotted Center Line -->
          <div class="pendulum-center-line"></div> 
           <!-- Ghost Pendulum (Max Cost) -->
           <div v-if="hoveredAttackCost" class="pendulum-arm ghost" :style="ghostMaxStyle" :class="ghostMaxTurnSwitch ? (pendulumSide === 'user' ? 'opponent' : 'user') : pendulumSide">
              <div class="pendulum-weight ghost-weight">
                 <span class="momentum-value">{{ Math.round(ghostMaxMomentumValue) }}</span>
             </div>
          </div>
          <!-- Ghost Pendulum (Min Cost) -->
           <div v-if="hoveredAttackCost" class="pendulum-arm ghost" :style="ghostMinStyle" :class="ghostMinTurnSwitch ? (pendulumSide === 'user' ? 'opponent' : 'user') : pendulumSide">
              <div class="pendulum-weight ghost-weight">
                 <span class="momentum-value">{{ Math.round(ghostMinMomentumValue) }}</span>
              </div>
          </div>
          <!-- Main Pendulum Arm -->
          <div class="pendulum-arm" :style="pendulumStyle" :class="pendulumSide">
              <div class="pendulum-weight">
                  <span class="momentum-value">{{ Math.round(currentTurnMomentum) }}</span>
              </div>
          </div>
          <div class="pendulum-base"></div>
          <div class="pendulum-labels">
             <span class="pendulum-label user-label">{{ userPlayer?.username }}</span>
             <span class="pendulum-label opponent-label">{{ opponentPlayer?.username }}</span>
          </div>
      </div>
      <!-- === End Pendulum Display === -->

       <!-- Messages and Turn Summary (UPDATED) -->
      <div class="messages-section">
            <p v-if="battleMessage" class="battle-message">{{ battleMessage }}</p>
            <p v-if="battleError" class="error-message">Error: {{ battleError }}</p>
            <BattleLog
                :logEntries="battleLogEntries"
                :userPlayerRole="userPlayerRole"
                :battleId="battleId"
            />
      </div>

       <!-- Action Selection (Update hover display) -->
       <div v-if="battle.status === 'active' && userPlayer" class="action-selection">
            <h3>Choose your Attack:</h3>
            <!-- Use AttackGrid for action selection -->
            <AttackGrid
                :attacks="mySelectedAttacks"
                mode="select" 
                :selectedIds="selectedAttackId ? [selectedAttackId] : []" 
                :maxSelectable="1"
                @update:selectedIds="(ids) => { selectedAttackId = ids.length > 0 ? ids[0] : null }"
                :class="{ 'disabled-overlay': !canAct || submittingAction }" 
                class="battle-action-grid"
            >
                <template #empty>No attacks available.</template>
            </AttackGrid>
           <!-- Removed old ul.attacks-grid -->
           <!-- <p v-if="!mySelectedAttacks.length" class="no-items-message">No attacks selected or available.</p> -->

           <button 
                @click="submitAction"
                :disabled="!canAct || !selectedAttackId || submittingAction"
                class="submit-action-button button button-primary"
            >
               <span v-if="!canAct">Waiting for {{ opponentPlayer?.username }}...</span>
               <span v-else-if="submittingAction">Submitting...</span>
               <span v-else>Confirm Attack</span>
           </button>
       </div>

      <!-- Finished State (Unchanged) -->
      <div v-if="battle.status === 'finished'">
          <h2>Battle Over!</h2>
          <p v-if="battle.winner?.id === currentUser?.id">You won!</p>
          <p v-else-if="battle.winner">{{ battle.winner.username }} won!</p>
          <p v-else>The battle ended unexpectedly.</p>
          <router-link :to="{ name: 'home' }">Return Home</router-link>
      </div>

    </div>
    <div v-else>
        <p>Could not load battle information.</p>
         <router-link :to="{ name: 'home' }">Return Home</router-link>
    </div>
  </div>
</template>

<style scoped>
.battle-container {
  padding: 1rem 2rem 2rem 2rem;
  max-width: 1200px; /* Adjusted width */
  margin: 1rem auto;
  background-color: var(--color-background-soft);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

h1 {
    text-align: center;
    margin-bottom: 1.5rem;
}

.status-active { color: var(--vt-c-green); font-weight: bold; }
.status-pending { color: var(--vt-c-yellow); }
.status-finished { color: var(--vt-c-text-dark-2); }
.status-declined { color: var(--vt-c-red); }

.players-display {
    display: flex;
    justify-content: space-between;
    align-items: flex-start; /* Align cards top */
    gap: 1rem;
    margin: 1.5rem 0;
}

/* REMOVED: .player-card styles */
/* REMOVED: .player-card h3 styles */
/* REMOVED: .player-card p styles */
/* REMOVED: .player-card progress styles */
/* REMOVED: progress::-webkit-progress-bar styles */
/* REMOVED: progress::-webkit-progress-value styles */
/* REMOVED: progress::-moz-progress-bar styles */
/* REMOVED: .hp-bar-* color styles */
/* REMOVED: .hp-high, .hp-medium, .hp-low styles */

.vs-separator { /* Keep this */
    font-size: 1.5em;
    font-weight: bold;
    align-self: center;
    padding: 0 1rem;
    color: var(--color-text-mute);
}

/* Keep placeholder style if needed */
.player-card.placeholder {
    min-width: 280px;
    flex: 1;
    padding: 1rem 1.5rem;
    border: 1px dashed var(--color-border);
    border-radius: 8px;
    background-color: var(--color-background-mute);
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--color-text-muted);
    font-style: italic;
}

/* UPDATED: Wrapper for log section */
.messages-section {
    margin: 1.5rem 0;
}

/* REMOVED: .messages styles (now in BattleLog) */
/* REMOVED: .battle-message, .error-message positioning (handled by messages-section) */
/* REMOVED: .turn-summary styles */
/* REMOVED: .turn-summary ul styles */
/* REMOVED: .log-entry-container styles */
/* REMOVED: .log-bubble styles */
/* REMOVED: Log source alignment styles */
/* REMOVED: Log effect type styles */
/* REMOVED: .log-turn-separator styles */
/* REMOVED: .stat-arrow styles */
/* REMOVED: .log-emoji styles */

.action-selection {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--color-border);
}

.attacks-grid.battle-attacks {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); 
    gap: 0.8rem;
    list-style: none;
    padding: 0;
    margin: 0 0 1.5rem 0;
}

.attack-card {
    background-color: var(--color-background);
    border: 1px solid var(--color-border-hover);
    border-radius: 8px;
    padding: 0.8rem;
    text-align: center;
    min-height: 110px; 
    display: flex; 
    flex-direction: column; 
    justify-content: center; 
    align-items: center; 
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
}

.attack-card:hover:not(.disabled) {
    transform: translateY(-3px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    border-color: var(--vt-c-indigo); 
}

.attack-card.selected {
    border-color: var(--vt-c-green);
    box-shadow: 0 0 8px rgba(var(--vt-c-green-rgb), 0.5);
    background-color: var(--vt-c-green-soft);
}

.attack-card.disabled {
    cursor: not-allowed;
    opacity: 0.5; 
    transform: none;
    box-shadow: none;
    pointer-events: none; 
}

.submit-action-button {
    padding: 0.8rem 1.5rem; 
    font-size: 1em;
    display: block; 
    margin: 1.5rem auto 0 auto;
    min-width: 180px;
}

.submit-action-button:disabled {
    background-color: var(--color-background-mute); 
    border-color: var(--color-border); 
    color: var(--color-text-mute);
    cursor: not-allowed;
    opacity: 0.7;
    animation: none;
    box-shadow: none;
}

.error-message {
    color: var(--vt-c-red);
    margin-bottom: 1rem;
}

.header-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.concede-button {
    padding: 0.5rem 1rem;
    background-color: var(--vt-c-red-soft);
    color: var(--vt-c-red-dark);
    border: 1px solid var(--vt-c-red);
    font-size: 0.9em;
}

.concede-button:hover:not(:disabled) {
    background-color: var(--vt-c-red);
    color: var(--vt-c-white);
}

.concede-button:disabled {
     opacity: 0.7;
     cursor: not-allowed;
}

.momentum-pendulum-container {
    position: relative;
    height: 100px;
    margin: 1rem auto 2rem auto;
    width: 200px;
}

.pendulum-pivot {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 10px;
    height: 10px;
    background-color: var(--color-border-hover);
    border-radius: 50%;
    z-index: 3;
}

.pendulum-arm {
    position: absolute;
    bottom: 20px;
    left: 50%; 
    width: 4px;
    height: 80px;
    background-color: var(--color-text-mute);
    border-radius: 2px;
    transform-origin: top center;
    transition: transform 0.5s cubic-bezier(0.68, -0.55, 0.27, 1.55);
    z-index: 2;
}

.pendulum-arm.user {
    background-color: var(--vt-c-blue);
}
.pendulum-arm.opponent {
    background-color: var(--vt-c-red);
}

.pendulum-weight {
    position: absolute;
    bottom: -8px;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 20px;
    background-color: inherit; 
    border-radius: 50%;
    border: 2px solid var(--color-background-soft);
    display: flex;
    justify-content: center;
    align-items: center;
}

.momentum-value {
    color: white;
    font-size: 0.7em;
    font-weight: bold;
    text-shadow: 0 0 2px black;
}

.pendulum-arm.ghost {
    opacity: 0.3;
    z-index: 1;
    background-color: grey;
    transition: transform 0.3s ease-out;
}
.pendulum-arm.ghost.user {
     background-color: var(--vt-c-blue-light);
}
.pendulum-arm.ghost.opponent {
     background-color: var(--vt-c-red-light);
}
.ghost-weight .momentum-value {
    opacity: 0.8;
}

.pendulum-weight.ghost-weight {
    border-color: transparent;
    background-color: inherit;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: none;
}

.pendulum-base {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 20px;
    background: linear-gradient(to right, var(--vt-c-blue-soft), var(--color-background-mute), var(--vt-c-red-soft));
    border-radius: 5px;
    border: 1px solid var(--color-border);
    z-index: 0;
}

.pendulum-labels {
    position: absolute;
    bottom: 2px;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-between;
    padding: 0 10px;
    font-size: 0.8em;
    font-weight: bold;
    z-index: 1;
}

.pendulum-label.user-label {
    color: var(--vt-c-blue-dark);
}

.pendulum-label.opponent-label {
    color: var(--vt-c-red-dark);
}

.pendulum-center-line {
    position: absolute;
    top: 10px;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    border-left: 2px dotted var(--color-border-hover);
    width: 0;
    z-index: 0;
}

.battle-action-grid {
    margin-bottom: 1.5rem; 
    position: relative; 
}

.battle-action-grid.disabled-overlay::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(50, 50, 50, 0.4);
    z-index: 5;
    border-radius: 8px;
    cursor: not-allowed;
}
</style> 