<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import AttackGrid from '@/components/AttackGrid.vue';

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

const battleLogContainer = ref(null);

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
    await gameStore.submitBattleAction(battle.value.id, selectedAttackId.value);
    selectedAttackId.value = null; // Reset selection after submitting
    submittingAction.value = false;
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

// Function to scroll log to bottom
function scrollLogToBottom() {
  nextTick(() => {
    const container = battleLogContainer.value;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
}

// Function to handle attack selection from card click
function selectAttack(attackId) {
    if (!submittingAction.value && canAct.value) {
        selectedAttackId.value = attackId;
    }
}

// Helper function for HP bar class
function getHpBarClass(currentHp, maxHp, playerType) {
    if (maxHp <= 0 || currentHp <= 0) return playerType === 'user' ? 'hp-bar-user' : 'hp-bar-opponent'; // Default if no HP
    const percentage = (currentHp / maxHp) * 100;
    let colorClass = 'hp-high';
    if (percentage <= 50) colorClass = 'hp-medium';
    if (percentage <= 20) colorClass = 'hp-low';
    
    const baseClass = playerType === 'user' ? 'hp-bar-user' : 'hp-bar-opponent';
    return [baseClass, colorClass];
}

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchBattleData(); 
  if (battle.value) {
       scrollLogToBottom();
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
watch(() => battle.value?.last_turn_summary, (newLog, oldLog) => {
    scrollLogToBottom();
}, { deep: true }); 

watch(() => battle.value?.status, (newStatus) => {
    if (newStatus === 'finished' || newStatus === 'declined') {
        stopPolling();
        scrollLogToBottom(); 
    }
});

// --- Formatting Helpers ---
function formatStage(stage) {
  return stage > 0 ? `+${stage}` : `${stage}`;
}
function getStatClass(stage) {
  if (stage > 0) return 'stat-up';
  if (stage < 0) return 'stat-down';
  return '';
}

// --- NEW: Hashing and Color Generation for Statuses ---
function stringToHashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

function getStatusColorStyle(statusName) {
  const hash = stringToHashCode(statusName);
  const hue = hash % 360; // Hue based on hash
  const saturation = 60 + (hash % 21); // Saturation between 60-80%
  const lightness = 45 + (hash % 11); // Lightness between 45-55%
  
  const backgroundColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  // Simple contrast check: if lightness is high, use dark text, else light text
  const textColor = lightness > 50 ? '#111' : '#fff'; 
  
  return {
    backgroundColor: backgroundColor,
    color: textColor,
    borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 15}%)` // Slightly darker border
  };
}
// --- END NEW ---

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
      
      <!-- Player Info Display (Unchanged) -->
      <div class="players-display">
          <!-- User Card -->
          <div class="player-card user">
              <h3>{{ userPlayer?.username }} (You)</h3>
              <div class="stat-badges-container">
                  <span class="stat-badges"> 
                     <template v-for="(stage, stat) in userStatStages" :key="stat">
                         <span v-if="stage !== 0" :class="[
                             'stat-badge',
                             getStatClass(stage)
                         ]">
                             {{ stat.toUpperCase() }} {{ formatStage(stage) }}
                         </span>
                     </template>
                  </span>
                  <!-- Ensure Custom Statuses display exists -->
                  <span class="custom-statuses"> 
                     <template v-for="(value, name) in userCustomStatuses" :key="name">
                         <span v-if="value" 
                               class="custom-status-badge" 
                               :style="getStatusColorStyle(name)">
                             {{ name.replace(/_/g, ' ').toUpperCase() }} {{ typeof value === 'number' ? '(' + value + ')' : '' }} 
                         </span>
                     </template>
                  </span>
              </div>
              <div class="hp-display">
                 <p>HP: {{ userCurrentHp }} / {{ userPlayer?.hp }}</p>
                 <progress 
                    :value="userCurrentHp" 
                    :max="userPlayer?.hp"
                    :class="getHpBarClass(userCurrentHp, userPlayer?.hp, 'user')"
                ></progress>
              </div>
          </div>
           <div class="vs-separator">VS</div>
           <!-- Opponent Card -->
          <div class="player-card opponent">
               <h3>{{ opponentPlayer?.username }}</h3>
               <div class="stat-badges-container">
                   <span class="stat-badges">
                        <template v-for="(stage, stat) in opponentStatStages" :key="stat">
                           <span v-if="stage !== 0" :class="[
                               'stat-badge',
                               getStatClass(stage)
                           ]">
                               {{ stat.toUpperCase() }} {{ formatStage(stage) }}
                           </span>
                       </template>
                   </span>
                    <!-- Ensure Custom Statuses display exists -->
                   <span class="custom-statuses"> 
                      <template v-for="(value, name) in opponentCustomStatuses" :key="name">
                          <span v-if="value" 
                                class="custom-status-badge" 
                                :style="getStatusColorStyle(name)">
                              {{ name.replace(/_/g, ' ').toUpperCase() }} {{ typeof value === 'number' ? '(' + value + ')' : '' }} 
                          </span>
                      </template>
                   </span>
               </div>
               <div class="hp-display">
                  <p>HP: {{ opponentCurrentHp }} / {{ opponentPlayer?.hp }}</p>
                  <progress 
                    :value="opponentCurrentHp" 
                    :max="opponentPlayer?.hp"
                    :class="getHpBarClass(opponentCurrentHp, opponentPlayer?.hp, 'opponent')"
                 ></progress>
               </div>
          </div>
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

       <!-- Messages and Turn Summary -->
      <div class="messages" ref="battleLogContainer">
            <p v-if="battleMessage" class="battle-message">{{ battleMessage }}</p>
            <p v-if="battleError" class="error-message">Error: {{ battleError }}</p>
            <div v-if="battle.last_turn_summary && battle.last_turn_summary.length" class="turn-summary">
                <ul>
                    <template v-for="(entry, index) in battle.last_turn_summary" :key="battle.id + '-entry-' + index">
                        <!-- ADDED: Turn Separator Line -->
                        <li v-if="entry.effect_type === 'turnchange'" class="log-turn-separator" aria-hidden="true"></li>
                        
                        <!-- Existing Log Entry List Item -->
                        <li 
                            :class="{
                                'log-entry-container': true,
                                [`source-${entry.source || 'unknown'}`]: true, /* Use computed property name */
                                'log-user': entry.source === userPlayerRole,
                                'log-opponent': entry.source !== userPlayerRole && entry.source !== 'system' && entry.source !== 'script' && entry.source !== 'debug',
                                'log-system': entry.source === 'system' || entry.source === 'script' || entry.source === 'debug'
                                // 'log-entry-turnchange': entry.effect_type === 'turnchange' /* Keep commented */
                            }"
                        >
                            <span
                               :class="[
                                   'log-bubble',
                                   `effect-${entry.effect_type || 'info'}`,
                                   entry.effect_details?.stat ? `bubble-stat-${entry.effect_details.stat}` : '',
                                   entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0 ? 'stat-arrow-up' : '',
                                   entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0 ? 'stat-arrow-down' : ''
                               ]"
                            >
                                <span v-if="entry.effect_type === 'action' && entry.effect_details?.emoji" class="log-emoji">{{ entry.effect_details.emoji }}</span>
                                <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0" class="stat-arrow up">▲</span>
                                <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0" class="stat-arrow down">▼</span>
                                {{ entry.text }}
                            </span>
                        </li>
                    </template>
                </ul>
            </div>
             <div style="height: 1px;"></div> 
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

.player-card {
    min-width: 280px;
    flex: 1; 
    padding: 1rem 1.5rem;
    border: 1px solid var(--color-border);
    border-radius: 8px; /* Slightly more rounded */
    background-color: var(--color-background-mute);
    display: flex; 
    flex-direction: column; 
    gap: 0.6rem; /* Adjust gap between elements */
}

.player-card.user { border-left: 4px solid var(--vt-c-blue); }
.player-card.opponent { border-left: 4px solid var(--vt-c-red); }

.player-card h3 {
    margin: 0;
    color: var(--color-heading);
    font-size: 1.3em; /* Slightly larger name */
    font-weight: 600;
    line-height: 1.2;
    /* Removed flex from h3 */
}

.player-card p { /* HP Text */
    margin: 0;
    text-align: right; /* Align text right within its space */
    font-size: 0.9em;
    color: var(--color-text);
    font-weight: 500;
    white-space: nowrap; 
    flex-shrink: 0; 
    max-width: 80px; /* Give text a max width */
}

.player-card progress {
    width: auto; /* Let flex-grow handle the width */
    height: 12px; 
    flex-grow: 1; /* Make progress bar fill available space */
    /* Appearance styles */
    -webkit-appearance: none;
    appearance: none; 
    background-color: var(--color-background-soft); 
    border: 1px solid var(--color-border); 
    border-radius: 6px; 
    overflow: hidden; 
}

/* Webkit progress bar track */
progress::-webkit-progress-bar {
    background-color: var(--color-background-soft); /* Match overall progress background */
    border-radius: 6px;
}

/* Webkit progress bar value (the fill) */
progress::-webkit-progress-value {
    border-radius: 6px; 
    transition: width 0.5s ease-in-out; /* Apply animation */
}

/* Mozilla progress bar */
progress::-moz-progress-bar { 
    border-radius: 6px;
    transition: width 0.5s ease-in-out; /* Apply animation */
}

/* Color classes for HP Bar value */
.hp-bar-user::-webkit-progress-value,
.hp-bar-user::-moz-progress-bar {
    background-color: var(--vt-c-blue); /* Default user color */
}
.hp-bar-opponent::-webkit-progress-value,
.hp-bar-opponent::-moz-progress-bar {
    background-color: var(--vt-c-red); /* Default opponent color */
}

/* Conditional Colors */
progress.hp-high::-webkit-progress-value,
progress.hp-high::-moz-progress-bar {
    /* Keep default user/opponent color for high HP */
}

progress.hp-medium::-webkit-progress-value,
progress.hp-medium::-moz-progress-bar {
    background-color: var(--vt-c-yellow-darker); 
}

progress.hp-low::-webkit-progress-value,
progress.hp-low::-moz-progress-bar {
    background-color: var(--vt-c-red-dark); 
}

/* Ensure opponent low hp is also dark red */
.hp-bar-opponent.hp-low::-webkit-progress-value,
.hp-bar-opponent.hp-low::-moz-progress-bar {
     background-color: var(--vt-c-red-dark); 
}

.vs-separator { /* Changed class name */
    font-size: 1.5em;
    font-weight: bold;
    align-self: center;
    padding: 0 1rem;
    color: var(--color-text-mute);
}

.messages {
    margin: 1.5rem 0;
    padding: 0.5rem; 
    min-height: 200px;
    max-height: 400px;
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    display: flex; 
    flex-direction: column;
    overflow-y: auto; 
}

.battle-message,
.error-message {
    padding: 0 0.5rem;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
}

.turn-summary {
    flex-grow: 1; 
    display: flex;
    flex-direction: column;
    padding: 0 0.5rem;
}

.turn-summary ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

/* Container for each log line - uses Flex */
.log-entry-container {
    margin-bottom: 0.5rem;
    display: flex; 
}

/* --- Alignment by Source --- */
.log-entry-container.log-user {
   justify-content: flex-start;
}
.log-entry-container.log-opponent {
    justify-content: flex-end;
}
.log-entry-container.log-system {
   justify-content: center;
}

/* The bubble itself */
.log-bubble {
    padding: 0.4rem 0.8rem; 
    border-radius: 15px; 
    max-width: 70%; 
    word-wrap: break-word; 
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); 
    line-height: 1.3; 
    display: inline-flex; 
    align-items: center;
    gap: 0.3em;
    border: 1px solid transparent;
    transition: background-color 0.2s ease, color 0.2s ease;
}

/* --- Log Bubble Styling by Source --- */
.log-entry-container.source-player1 .log-bubble,
.log-entry-container.source-player2 .log-bubble {
    background-color: var(--vt-c-indigo); 
    color: white; 
    border-bottom-left-radius: 3px;
}
.log-entry-container.log-opponent .log-bubble {
     border-bottom-right-radius: 3px; 
     border-bottom-left-radius: 15px;
}

.log-entry-container.source-script .log-bubble {
    background-color: #5a5f89;
    color: white;
}

.log-entry-container.source-system .log-bubble {
    color: var(--color-text-mute);
    background-color: transparent;
    box-shadow: none;
    font-style: italic;
    border: none;
    padding: 0.1rem 0.5rem;
}

.log-entry-container.source-debug .log-bubble {
    color: #666; 
    background-color: transparent;
    box-shadow: none;
    font-style: italic;
    opacity: 0.6;
    font-size: 0.85em;
    padding: 0.1rem 0.5rem;
    border: none;
}

/* --- Log Bubble Styling by Effect Type --- */
.log-bubble.effect-action {
    /* Keep player/script background */
}

/* NEW: Turn Change Separator Style */
.log-turn-separator {
    list-style: none; /* Remove potential bullet point */
    height: 1px;
    background-color: var(--color-border-hover);
    margin: 1rem 0.5rem; /* Add vertical spacing */
    flex-basis: 100%; /* Ensure it takes full width within flex context if needed */
}

/* NEW: Optional style to make turn change messages less prominent if desired */
/* 
.log-bubble.effect-turnchange {
    background-color: transparent;
    color: var(--color-text-mute);
    font-style: italic;
    font-size: 0.9em;
    box-shadow: none;
    border: none;
    text-align: center; 
    padding: 0.2rem 0.5rem;
} 
*/

.log-bubble.effect-damage {
    background-color: var(--vt-c-red-soft);
    color: var(--vt-c-red-dark);
    border-color: var(--vt-c-red);
}

.log-bubble.effect-heal {
    background-color: var(--vt-c-green-soft);
    color: var(--vt-c-green-dark);
    border-color: var(--vt-c-green);
}

.log-bubble.effect-stat_change {
    /* Style based on arrow */
}

.log-bubble.effect-status_apply,
.log-bubble.effect-status_remove,
.log-bubble.effect-status_effect {
     background-color: var(--color-background-mute);
     color: var(--color-text);
     border-style: dashed;
     border-color: var(--color-border-hover);
}

.log-bubble.effect-info {
    /* Keep neutral, source styles will apply */
    color: var(--color-text);
}
/* Override for system/script info */
.log-entry-container.source-system .log-bubble.effect-info,
.log-entry-container.source-script .log-bubble.effect-info {
     color: var(--color-text-mute); 
     background-color: transparent;
     box-shadow: none;
}

.log-bubble.effect-error {
    background-color: var(--vt-c-red-dark);
    color: white;
    font-weight: bold;
    border: none;
}

.log-bubble.effect-debug {
    /* Style already handled by source-debug */
}

/* --- Icon/Arrow Styles --- */
.stat-arrow { display: inline-block; margin-right: 0.2em; font-weight: bold; }
.stat-arrow.up { color: var(--vt-c-green); }
.stat-arrow.down { color: var(--vt-c-red); }
.log-emoji { margin-right: 0.3em; font-size: 1.1em; line-height: 1; }

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

.stat-badges-container {
    min-height: 20px;
}

.stat-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem; 
}

.hp-display {
    display: flex; 
    align-items: center; 
    gap: 0.75rem; 
    margin-top: auto; 
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

.stat-badge {
    display: inline-block;
    padding: 0.2em 0.5em;
    font-size: 0.8em;
    font-weight: 600;
    border-radius: 4px;
    color: var(--vt-c-white-soft);
    text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
}

.stat-badge.badge-attack {
    background-color: var(--vt-c-red-dark);
}
.stat-badge.badge-defense {
    background-color: var(--vt-c-blue-dark);
}
.stat-badge.badge-speed {
    background-color: var(--vt-c-yellow-darker);
}

.custom-statuses {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem; 
    margin-top: 0.4rem;
}

.custom-status-badge {
    display: inline-block;
    padding: 0.2em 0.5em;
    font-size: 0.8em;
    font-weight: 500;
    border-radius: 4px;
    text-transform: capitalize;
    border: 1px solid transparent;
}

.player-panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

.stat-stages, .custom-statuses {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.4rem;
    margin-bottom: 0.5rem;
    min-height: 20px;
}

.stat-badge, .status-badge {
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid transparent;
}

.stat-badge.stat-up {
    background-color: rgba(76, 175, 80, 0.2);
    color: #388E3C;
    border-color: #388E3C;
}

.stat-badge.stat-down {
    background-color: rgba(244, 67, 54, 0.2);
    color: #D32F2F;
    border-color: #D32F2F;
}

.status-badge.status-custom {
    background-color: rgba(158, 158, 158, 0.2);
    color: #616161;
    border-color: #616161;
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