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
const totalMomentum = computed(() => Math.max(1, currentMomentumP1.value + currentMomentumP2.value)); // Avoid division by zero

// Normalized value [0, 1] where 1 means P1 has all momentum
const normalizedMomentumP1 = computed(() => currentMomentumP1.value / totalMomentum.value);

// Determine pendulum angle/position based on normalized value (Uses displayed state)
const PENDULUM_MAX_ANGLE = 75; // Max tilt angle

// Calculate angle based on the *current acting player's* momentum (Uses displayed state)
const pendulumAngle = computed(() => {
    if (!displayedBattleState.value || !displayedBattleState.value.whose_turn) return 0;
    
    const turnRole = displayedBattleState.value.whose_turn;
    // Use computed momentum values derived from displayed state
    const currentMomentum = turnRole === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
    
    const scaledMomentum = currentMomentum / MOMENTUM_THRESHOLD; 
    const angleScale = clamp(scaledMomentum, 0, 1.5); 

    // Base angle: Positive if P1 turn, Negative if P2 turn
    let angle = angleScale * PENDULUM_MAX_ANGLE * (turnRole === 'player1' ? 1 : -1);
    angle = clamp(angle, -PENDULUM_MAX_ANGLE, PENDULUM_MAX_ANGLE);

    // Perspective inversion for viewer
    if (userPlayerRole.value === 'player2') {
        angle = -angle;
    }
    
    return angle;
});

// Style object for the pendulum element (Uses pendulumAngle computed)
const pendulumStyle = computed(() => ({
  transform: `rotate(${pendulumAngle.value}deg)`
}));

// Determine whose side the pendulum is leaning towards for styling (Uses displayed state)
const pendulumSide = computed(() => {
    if (!displayedBattleState.value || !displayedBattleState.value.whose_turn) return 'center';
    return displayedBattleState.value.whose_turn === userPlayerRole.value ? 'user' : 'opponent';
});

// Available actions now come directly from the displayed battle data
const mySelectedAttacks = computed(() => {
    // Ensure attacks have unique keys if IDs might not be enough (though they should be)
    return (displayedBattleState.value?.my_selected_attacks || []).map((attack, index) => ({
        ...attack,
        key: `${attack.id}-${index}` // Simple unique key
    }));
});

// --- Ghost Preview State (Uses displayed state for calculation) ---
const hoveredAttackCost = ref(null); // { min: X, max: Y }
const ghostMinAngle = ref(0);
const ghostMaxAngle = ref(0);
const ghostMinMomentumValue = ref(0); // Momentum value for the player *after* min cost
const ghostMaxMomentumValue = ref(0); // Momentum value for the player *after* max cost
const ghostMinTurnSwitch = ref(false); // Will turn switch if min cost applied?
const ghostMaxTurnSwitch = ref(false); // Will turn switch if max cost applied?
const hoveredAttackId = ref(null); // Track ID for hover styling

// Calculate ghost states when hovering (Modify to use displayed state)
function calculateGhostState(cost) {
    const turnRole = userPlayerRole.value; // This is based on displayed state
    // Get momentum from computed properties (already based on displayed state)
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

// Update hover state for pendulum preview
function previewAttackCost(action) { 
    console.log("Hover detected on AttackGrid item:", action);
    if (!canAct.value) {
        console.log("Preview aborted: Not user's turn.");
        clearAttackCostPreview();
        return;
    }
    if (!action || action.calculated_min_cost === undefined) {
        console.log("Preview aborted: Action missing or cost data undefined.");
        clearAttackCostPreview();
        return;
    }
    
    console.log("Activating pendulum preview.");
    hoveredAttackId.value = action.id; // Track hovered ID
    hoveredAttackCost.value = {
        min: action.calculated_min_cost,
        max: action.calculated_max_cost,
        attackId: action.id // Store ID to match tooltip
    };

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
    console.log("Clearing pendulum preview.");
    hoveredAttackId.value = null;
    hoveredAttackCost.value = null;
}

// Helper computed styles for ghosts (Unchanged)
const ghostMinStyle = computed(() => ({ transform: `rotate(${ghostMinAngle.value}deg)` }));
const ghostMaxStyle = computed(() => ({ transform: `rotate(${ghostMaxAngle.value}deg)` }));

// Display value for main pendulum (Uses displayed state via computed)
const currentTurnMomentum = computed(() => {
     if (!displayedBattleState.value || !displayedBattleState.value.whose_turn) return 0;
     return displayedBattleState.value.whose_turn === 'player1' ? currentMomentumP1.value : currentMomentumP2.value;
});

// --- END Pendulum Logic ---

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
function handleGridAttackClick(attackId) {
    if (!submittingAction.value && canAct.value && attackId) {
        submitAction(attackId);
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
  <div class="battle-view-container">
    <div v-if="isLoading && !displayedBattleState" class="loading-message">
      <p>Loading Battle...</p>
    </div>
    <div v-else-if="battleError && !displayedBattleState" class="error-container">
       <p class="error-message">Error: {{ battleError }}</p>
       <router-link :to="{ name: 'home' }" class="button button-secondary">Return Home</router-link>
    </div>
    <div v-else-if="displayedBattleState" class="battle-interface">

      <!-- NEW: Header with Status and Concede -->
      <div class="battle-header">
          <p class="battle-status">Status: <span :class="`status-${displayedBattleState.status}`">{{ displayedBattleState.status }}</span></p>
          <button 
            v-if="displayedBattleState.status === 'active'" 
            @click="handleConcede"
            :disabled="isConceding || submittingAction"
            class="button concede-button-header"
          >
            {{ isConceding ? 'Conceding...' : 'Concede' }}
          </button>
      </div>

      <!-- NEW: Top Row Container -->
      <div class="battle-top-row">
          <!-- Opponent Info -->
          <PlayerInfoCard
              :player="opponentPlayer"
              :currentHp="opponentCurrentHp"
              :statStages="opponentStatStages"
              :customStatuses="opponentCustomStatuses"
              playerType="opponent"
              class="opponent-card"
          />

          <!-- Momentum Pendulum -->
          <div class="momentum-pendulum-container">
              <div class="pendulum-pivot"></div>
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
              <!-- Labels are removed for cleaner mobile look, info is in player cards -->
          </div>

          <!-- User Info -->
           <PlayerInfoCard
                :player="userPlayer"
                :currentHp="userCurrentHp"
                :statStages="userStatStages"
                :customStatuses="userCustomStatuses"
                playerType="user"
                :isCurrentUser="true"
                class="user-card"
            />
      </div> <!-- End Top Row Container -->
      
       <!-- NEW: Bottom Area Container -->
      <div class="battle-bottom-area">
          <!-- Battle Log -->
           <div class="battle-log-area">
               <BattleLog
                   :logEntries="displayedLogEntries"
                   :userPlayerRole="userPlayerRole"
                   :battleId="battleId"
               />
           </div>

            <!-- Action Area (Responsive) -->
            <div class="action-area-container">
               <!-- Desktop Action Area (Attack Grid) -->
               <div class="action-display-desktop">
                    <div v-if="displayedBattleState.status === 'active' && userPlayer" class="desktop-action-selection">
                        <h3>Choose your Attack:</h3>
                        <AttackGrid 
                           v-if="canAct && mySelectedAttacks.length > 0" 
                           :attacks="mySelectedAttacks" 
                           mode="select"
                           :isSubmitting="submittingAction" 
                           @update:selectedIds="handleGridAttackClick($event[0])"
                           class="battle-attack-grid"
                           @attackHover="previewAttackCost"
                           @attackHoverEnd="clearAttackCostPreview"
                        />
                        <div v-else-if="!canAct" class="waiting-message">Waiting for opponent...</div>
                        <div v-else class="waiting-message">No attacks available?</div>
                    </div>
                    <div v-else class="desktop-action-placeholder">
                         <!-- Placeholder for non-active state on desktop -->
                    </div>
               </div>

               <!-- Mobile Action Area (Preview + Emojis) -->
               <div class="action-display-mobile">
                    <!-- Attack Preview Area -->
                   <div class="attack-preview-area" :class="{ 'visible': selectedAttackPreview }">
                        <AttackCardDisplay 
                           v-if="selectedAttackPreview"
                           :attack="selectedAttackPreview" 
                           :isClickable="canAct && !submittingAction"
                           @click="handlePreviewCardClick"
                           class="preview-card"
                           :disabled="!canAct || submittingAction"
                        />
                        <div v-else class="preview-placeholder">
                            <span v-if="canAct">Tap an emoji below to preview attack</span>
                            <span v-else>Waiting for opponent...</span>
                        </div>
                   </div>
                    <!-- Emoji Action Bar -->
                   <div class="emoji-action-bar" v-if="displayedBattleState.status === 'active'">
                       <button 
                           v-for="attack in mySelectedAttacks" 
                           :key="attack.key" 
                           @click="handleEmojiClick(attack)"
                           @mouseenter="previewAttackCost(attack)" 
                           @mouseleave="clearAttackCostPreview"
                           :disabled="!canAct || submittingAction"
                           class="emoji-button"
                           :class="{ 
                               'selected': selectedAttackPreview?.id === attack.id,
                               'hovered': hoveredAttackId === attack.id
                           }"
                           :title="`${attack.name} (Cost: ${attack.calculated_min_cost ?? '?'} - ${attack.calculated_max_cost ?? '?'})`" 
                        >
                           {{ attack.emoji }}
                       </button>
                   </div>
                   <div v-else class="action-bar-placeholder">
                       <!-- Placeholder for non-active state on mobile -->
                   </div>
               </div>
           </div>
      </div> <!-- End Bottom Area Container -->

       <!-- Finished State Overlay -->
       <div v-if="displayedBattleState.status === 'finished'" class="battle-finished-overlay">
          <h2>Battle Over!</h2>
          <p v-if="displayedBattleState.winner?.id === currentUser?.id" class="win-message">🎉 You won! 🎉</p>
          <p v-else-if="displayedBattleState.winner" class="lose-message">😢 {{ displayedBattleState.winner.username }} won! 😢</p>
          <p v-else class="draw-message">The battle ended unexpectedly.</p>
          <router-link :to="{ name: 'home' }" class="button button-secondary return-home-button">Return Home</router-link>
       </div>

    </div>
    <div v-else class="loading-message">
        <p>Could not load battle information.</p>
         <router-link :to="{ name: 'home' }" class="button button-secondary">Return Home</router-link>
    </div>
  </div>
</template>


<style scoped>
.battle-view-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Full viewport height */
  width: 100%;
  overflow: hidden; /* Prevent scrolling of the main container */
  background-color: var(--color-background-soft);
  position: relative; /* For overlay positioning */
}

.loading-message, .error-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    padding: 2rem;
    text-align: center;
}

.battle-interface {
    flex-grow: 1; /* Allow interface to take up remaining space */
    display: flex;
    flex-direction: column;
    padding: 0.5rem; /* Reduced padding */
    overflow: hidden; /* Prevent internal scrolling unless specified */
    gap: 0.5rem; /* Space between main sections */
}

/* Player cards positioning */
.opponent-card {
    /* Positioned at the top */
    flex-shrink: 0; /* Prevent shrinking */
}

.user-card {
    /* Positioned above log/preview */
     flex-shrink: 0; /* Prevent shrinking */
}

/* Pendulum */
.momentum-pendulum-container {
    position: relative;
    height: 80px; /* Reduced height */
    margin: 0.5rem auto; /* Reduced margin */
    width: 150px; /* Reduced width */
    flex-shrink: 0; /* Prevent shrinking */
}

.pendulum-pivot { top: 0; left: 50%; transform: translateX(-50%); width: 8px; height: 8px; background-color: var(--color-border-hover); border-radius: 50%; z-index: 3; position: absolute; }
.pendulum-center-line { position: absolute; top: 8px; bottom: 15px; left: 50%; transform: translateX(-50%); border-left: 1px dotted var(--color-border-hover); width: 0; z-index: 0; }
.pendulum-arm { position: absolute; bottom: 15px; left: 50%; width: 3px; height: 60px; background-color: var(--color-text-mute); border-radius: 1.5px; transform-origin: top center; transition: transform 0.5s cubic-bezier(0.68, -0.55, 0.27, 1.55); z-index: 2; }
.pendulum-arm.user { background-color: var(--vt-c-blue); }
.pendulum-arm.opponent { background-color: var(--vt-c-red); }
.pendulum-weight { position: absolute; bottom: -7px; left: 50%; transform: translateX(-50%); width: 16px; height: 16px; background-color: inherit; border-radius: 50%; border: 2px solid var(--color-background-soft); display: flex; justify-content: center; align-items: center; }
.momentum-value { color: white; font-size: 0.6em; font-weight: bold; text-shadow: 0 0 1px black; }
.pendulum-arm.ghost { opacity: 0.3; z-index: 1; background-color: grey; transition: transform 0.3s ease-out; }
.pendulum-arm.ghost.user { background-color: var(--vt-c-blue-light); }
.pendulum-arm.ghost.opponent { background-color: var(--vt-c-red-light); }
.pendulum-weight.ghost-weight { border-color: transparent; background-color: inherit; width: 14px; height: 14px; border-radius: 50%; border: none; }
.ghost-weight .momentum-value { opacity: 0.8; }
.pendulum-base { position: absolute; bottom: 0; left: 0; right: 0; height: 15px; background: linear-gradient(to right, var(--vt-c-blue-soft), var(--color-background-mute), var(--vt-c-red-soft)); border-radius: 3px; border: 1px solid var(--color-border); z-index: 0; }
/* Removed labels */

/* Battle Log Area */
.battle-log-area {
    flex-grow: 1; /* Takes up available space */
    overflow-y: auto; /* Allow vertical scrolling */
    border: 1px solid var(--color-border);
    border-radius: 4px; /* Less rounding */
    background-color: var(--color-background);
    padding: 0.5rem;
    margin-bottom: 0.5rem; /* Space before preview */
    min-height: 0; /* Crucial for flexbox scrolling children */
}

/* Attack Preview Area */
.attack-preview-area {
    height: 140px; /* Fixed height for the preview card */
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 0.5rem; /* Space before emoji bar */
    flex-shrink: 0; /* Prevent shrinking */
    transition: opacity 0.3s ease;
    opacity: 1; /* Always visible, content changes */
}

.attack-preview-area .preview-placeholder {
    color: var(--color-text-mute);
    font-style: italic;
    font-size: 0.9em;
    text-align: center;
}

.attack-preview-area .preview-card {
   max-width: 300px; /* Limit width */
   width: 90%;
   height: 100%; /* Fill the container height */
   cursor: pointer;
   transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.attack-preview-area .preview-card:hover:not(.disabled) {
    transform: scale(1.03);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.attack-preview-area .preview-card.disabled {
    cursor: not-allowed;
    opacity: 0.6;
}


/* Emoji Action Bar */
.emoji-action-bar {
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 0.5rem 0.2rem;
    background-color: var(--color-background-mute);
    border-top: 1px solid var(--color-border);
    flex-shrink: 0; /* Prevent shrinking */
}

.emoji-button {
    font-size: 1.8rem; /* Larger emojis */
    background: none;
    border: 2px solid transparent; /* Border for selection/hover */
    border-radius: 8px; /* Slightly more rounding for buttons */
    cursor: pointer;
    padding: 0.3rem;
    line-height: 1;
    transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.1s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 45px; /* Fixed size */
    height: 45px;
}

.emoji-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background-color: transparent !important; /* Ensure disabled look */
}

.emoji-button:not(:disabled):hover,
.emoji-button.hovered:not(:disabled) { /* Style for mouse hover */
    background-color: var(--color-background-soft);
    border-color: var(--color-border-hover);
    transform: scale(1.1);
}

.emoji-button.selected:not(:disabled) { /* Style for click selection */
    background-color: var(--vt-c-indigo-soft);
    border-color: var(--vt-c-indigo);
    transform: scale(1.05);
}

.emoji-button.concede-button {
    font-size: 1.5rem; /* Slightly smaller for flag */
    border-color: var(--vt-c-red-soft);
}
.emoji-button.concede-button:hover:not(:disabled) {
     background-color: var(--vt-c-red-soft);
     border-color: var(--vt-c-red);
}


.action-bar-placeholder {
    height: 60px; /* Match approx height of emoji bar */
    flex-shrink: 0;
}

/* Battle Finished Overlay Styles */
.battle-finished-overlay {
  position: absolute; /* Cover the entire view */
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 2rem;
  background-color: var(--color-background); /* Use solid background color */
  z-index: 10; /* Ensure it's on top */
}

.battle-finished-overlay h2 { font-size: 2em; margin-bottom: 1rem; color: var(--color-heading); }
.battle-finished-overlay p { font-size: 1.2em; margin-bottom: 1.5rem; }
.battle-finished-overlay .win-message { color: var(--vt-c-green-dark); font-weight: bold; }
.battle-finished-overlay .lose-message { color: var(--vt-c-red-dark); font-weight: bold; }
.battle-finished-overlay .draw-message { color: var(--color-text-muted); }
.return-home-button { 
    font-size: 1em; 
    padding: 0.7rem 1.5rem; 
    /* Inherit button styles */
    display: inline-block; border: none; border-radius: 4px; cursor: pointer; text-align: center; font-weight: 600; transition: background-color 0.2s ease, opacity 0.2s ease, border-color 0.2s ease; line-height: 1.2; text-decoration: none; background-color: var(--color-background-mute); color: var(--color-text); border: 1px solid var(--color-border-hover); 
}
.return-home-button:hover { background-color: var(--color-background-soft); border-color: var(--color-text-mute); }

/* --- Responsive Display Toggle for Action Areas --- */
.action-display-mobile {
    display: flex; /* Use flex for internal mobile layout */
    flex-direction: column;
}

.action-display-desktop {
    display: none; /* Hidden by default */
}

@media (min-width: 768px) { /* Or your preferred desktop breakpoint */
    /* --- Desktop Layout Overrides --- */
    .battle-interface {
        /* Revert to default or set specific height if needed */
        /* height: auto; */ 
        /* Use Grid for overall desktop layout */
        display: grid;
        grid-template-rows: auto 1fr; /* Top row auto height, bottom row takes rest */
        grid-template-columns: 1fr; /* Single column for rows */
        gap: 1rem; 
        padding: 1rem; /* Restore some padding */
        max-width: 1400px; /* Wider max width for desktop */
        margin: 1rem auto;
    }

    .battle-top-row {
        display: grid;
        grid-template-columns: 1fr auto 1fr; /* Player | Pendulum | Player */
        align-items: flex-start; /* Align cards to top */
        gap: 1rem;
    }

    .battle-bottom-area {
        display: grid;
        grid-template-columns: 1fr 1fr; /* Log | Actions */
        gap: 1rem;
        overflow: hidden; /* Prevent overflow issues */
        min-height: 300px; /* Give bottom area some minimum height */
    }

    .battle-log-area {
        /* Already setup for scrolling */
        min-height: 0; /* Still needed for flex/grid context */
        max-height: 60vh; /* Limit max height if needed */
        padding: 0.75rem;
    }

    .action-area-container {
        /* Container for the desktop grid */
        margin-top: 0; /* Reset margin from mobile */
    }

    /* --- Action Area Display Toggle --- */
    .action-display-desktop {
        display: block; /* Show desktop grid */
        height: 100%; /* Allow grid to fill space */
        display: flex;
        flex-direction: column;
    }
    .desktop-action-selection {
        flex-grow: 1; /* Allow grid container to grow */
        display: flex;
        flex-direction: column;
    }
    .battle-attack-grid {
         flex-grow: 1; /* Allow grid itself to fill space */
    }

    .action-display-mobile {
        display: none; /* Hide mobile controls */
    }

    /* --- Component Size Adjustments --- */
    .momentum-pendulum-container {
         width: 150px; /* Slightly smaller pendulum is fine */
         height: 100px;
         margin: 0 auto; /* Center pendulum in its grid cell */
         align-self: center; /* Vertically center pendulum */
    }
    .pendulum-arm { height: 80px; width: 4px; }
    .pendulum-pivot { width: 10px; height: 10px; }
    .pendulum-center-line { top: 10px; bottom: 20px; }
    .pendulum-base { height: 20px; }
    .pendulum-weight { width: 20px; height: 20px; }
    .pendulum-weight.ghost-weight { width: 18px; height: 18px; }
    .momentum-value { font-size: 0.7em; }
    
    .desktop-action-selection h3 {
        margin-bottom: 0.8rem;
        text-align: center;
    }

    /* Ensure player cards don't stretch excessively */
    .opponent-card, .user-card {
        max-width: 400px; /* Limit card width */
        margin: 0 auto; /* Center cards in their grid areas */
    }

}

/* NEW: Battle Header Styles */
.battle-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.2rem 0.5rem; /* Minimal padding */
    margin-bottom: 0.5rem;
    flex-shrink: 0;
}

.battle-status {
    font-weight: bold;
    margin: 0;
}
.status-active { color: var(--vt-c-green); }
.status-pending { color: var(--vt-c-yellow); }
.status-finished { color: var(--color-text-mute); }
.status-declined { color: var(--vt-c-red); }

.concede-button-header {
    padding: 0.4rem 0.8rem;
    font-size: 0.85em;
    /* Inherit general button styles */
    background-color: var(--vt-c-red-soft);
    color: var(--vt-c-red-dark);
    border: 1px solid var(--vt-c-red);
    border-radius: 4px;
}

.concede-button-header:hover:not(:disabled) {
    background-color: var(--vt-c-red);
    color: var(--vt-c-white);
}

.concede-button-header:disabled {
     opacity: 0.6;
     cursor: not-allowed;
}
/* --- END Battle Header Styles --- */

</style> 