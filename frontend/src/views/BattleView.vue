<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // Import the new component

const route = useRoute();
const router = useRouter();
const gameStore = useGameStore();
const authStore = useAuthStore();

const battleId = computed(() => parseInt(route.params.id));
const isLoading = ref(false);
const selectedAttackId = ref(null);
const submittingAction = ref(false);
const isConceding = computed(() => gameStore.isConceding);
let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 1000; // Poll every 1 second now

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

// Check if it's user's turn to act (UPDATED for momentum)
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
    // Get the role OPPOSITE to the user
    const opponentRole = userPlayerRole.value === 'player1' ? 'player2' : 'player1'; 
    return battle.value[`stat_stages_${opponentRole}`];
});

// --- Momentum Bar Logic (Updated for Uncertainty Preview) ---
const momentumPreview = ref(null); // { role: 'player1'/'player2', minCost: X, maxCost: Y }

const currentMomentumP1 = computed(() => battle.value?.current_momentum_player1 ?? 0);
const currentMomentumP2 = computed(() => battle.value?.current_momentum_player2 ?? 0);

const MOMENTUM_RESCALE_THRESHOLD = 100; // Rescale if min momentum > 100

// Calculate the offset for rescaling
const rescaleOffset = computed(() => {
  const p1 = currentMomentumP1.value;
  const p2 = currentMomentumP2.value;
  const minMomentum = Math.min(p1, p2);
  if (minMomentum > MOMENTUM_RESCALE_THRESHOLD) {
    return Math.max(0, minMomentum - MOMENTUM_RESCALE_THRESHOLD);
  }
  return 0;
});

// Calculate the values used for the visual bar representation
const visualMomentumP1 = computed(() => Math.max(0, currentMomentumP1.value - rescaleOffset.value));
const visualMomentumP2 = computed(() => Math.max(0, currentMomentumP2.value - rescaleOffset.value));

// Calculate total visual momentum for percentage calculation
const visualTotalMomentum = computed(() => Math.max(1, visualMomentumP1.value + visualMomentumP2.value));

// Calculate P1's percentage based on visual values - USED FOR BAR FILL
const visualP1Percent = computed(() => (visualMomentumP1.value / visualTotalMomentum.value) * 100);

// Calculate PREVIEWED momentum based on MAX gain
const previewedMaxMomentumP1 = computed(() => {
    if (momentumPreview.value?.role === 'player1') {
        return currentMomentumP1.value + momentumPreview.value.maxCost;
    }
    return currentMomentumP1.value;
});
const previewedMaxMomentumP2 = computed(() => {
    if (momentumPreview.value?.role === 'player2') {
        return currentMomentumP2.value + momentumPreview.value.maxCost;
    }
    return currentMomentumP2.value;
});

// Calculate PREVIEWED momentum based on MIN gain
const previewedMinMomentumP1 = computed(() => {
    if (momentumPreview.value?.role === 'player1') {
        return currentMomentumP1.value + momentumPreview.value.minCost;
    }
    return currentMomentumP1.value;
});
const previewedMinMomentumP2 = computed(() => {
    if (momentumPreview.value?.role === 'player2') {
        return currentMomentumP2.value + momentumPreview.value.minCost;
    }
    return currentMomentumP2.value;
});

// Always calculate percentages relative to P1 for visual consistency of the bar itself
const momentumTotalMax = computed(() => Math.max(1, previewedMaxMomentumP1.value + previewedMaxMomentumP2.value)); 
const momentumP1PercentMax = computed(() => (previewedMaxMomentumP1.value / momentumTotalMax.value) * 100);

// --- NEW: Computed properties for Preview positioning (perspective aware) ---
const previewStyle = computed(() => {
    if (!momentumPreview.value) return {}; // No preview active

    const role = momentumPreview.value.role;
    const minGain = momentumPreview.value.minCost;
    const maxGain = momentumPreview.value.maxCost;
    const currentP1 = currentMomentumP1.value;
    const currentP2 = currentMomentumP2.value;

    let previewMinP1, previewMaxP1, previewMinP2, previewMaxP2;

    if (role === 'player1') {
        previewMinP1 = currentP1 + minGain;
        previewMaxP1 = currentP1 + maxGain;
        previewMinP2 = currentP2;
        previewMaxP2 = currentP2;
    } else { // role === 'player2'
        previewMinP1 = currentP1;
        previewMaxP1 = currentP1;
        previewMinP2 = currentP2 + minGain;
        previewMaxP2 = currentP2 + maxGain;
    }

    // Calculate total momentum range for percentage calculation
    const totalMinMomentum = Math.max(1, previewMinP1 + previewMinP2);
    const totalMaxMomentum = Math.max(1, previewMaxP1 + previewMaxP2);

    // Calculate the start and end percentages for P1's visual area
    const previewStartPercent = (previewMinP1 / totalMinMomentum) * 100;
    const previewEndPercent = (previewMaxP1 / totalMaxMomentum) * 100;

    // These vars control the preview overlay position, always based on P1's area
    return {
        '--preview-start-percent': previewStartPercent + '%',
        '--preview-end-percent': previewEndPercent + '%',
    };
});

// Determine which side has momentum advantage (still based on P1 vs P2 absolute values)
// --- UPDATED to return user/opponent advantage ---
const momentumAdvantage = computed(() => {
    const p1Momentum = currentMomentumP1.value;
    const p2Momentum = currentMomentumP2.value;

    if (p1Momentum === p2Momentum) return 'neutral';

    const leadingRole = p1Momentum > p2Momentum ? 'player1' : 'player2';

    if (leadingRole === userPlayerRole.value) {
        return 'user-advantage';
    } else {
        return 'opponent-advantage';
    }
});

// Available actions now come directly from the battle data
const availableActions = computed(() => battle.value?.available_actions || []);

// Update computed to use new field name
const mySelectedAttacks = computed(() => battle.value?.my_selected_attacks || []);

// Hover handlers (Check if gain data exists)
function previewAttackMomentum(action) { 
    if (!canAct.value || !action) {
        clearMomentumPreview(); // Clear if not actionable
        return;
    }
    // Only show preview if gain data is present (meaning it's our turn)
    if (action.calculated_min_gain !== undefined && action.calculated_max_gain !== undefined) {
        momentumPreview.value = {
            role: userPlayerRole.value,
            minCost: action.calculated_min_gain,
            maxCost: action.calculated_max_gain 
        };
    } else {
        clearMomentumPreview(); // Clear if no gain data (not our turn)
    }
}
function clearMomentumPreview() {
    momentumPreview.value = null;
}

const battleLogContainer = ref(null); // Ref for the scrollable container

// NEW: Computed properties for displaying momentum difference
const momentumDifference = computed(() => Math.abs(currentMomentumP1.value - currentMomentumP2.value));

const momentumDisplayP1 = computed(() => {
    return currentMomentumP1.value > currentMomentumP2.value ? `+${momentumDifference.value}` : ' '; // Show difference or empty
});
const momentumDisplayP2 = computed(() => {
    return currentMomentumP2.value > currentMomentumP1.value ? `+${momentumDifference.value}` : ' '; // Show difference or empty
});

// --- Methods ---
async function fetchBattleData() {
    isLoading.value = true;
    try {
        // Use fetchBattleById to ensure we have the correct battle data for this view
        await gameStore.fetchBattleById(battleId.value);
        // Check if battle loaded successfully and matches the route ID
        if (!gameStore.activeBattle || gameStore.activeBattle.id !== battleId.value) {
            console.error('Failed to load correct battle data or battle ended.');
            // Redirect if battle doesn't match or is finished/not found?
            // router.push({ name: 'home' });
        }
    } catch (error) {
        console.error('Error fetching battle data in view:', error);
        // Error message is handled by the store's battleError
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
    // Battle state updates will come via polling or the response
}

async function handleConcede() {
    if (confirm("Are you sure you want to concede the battle?")) {
       await gameStore.concedeBattle(battleId.value);
       // Battle state should update via concedeBattle action setting final state
       // Polling will stop automatically due to status change watcher
    }
}

function startPolling() {
    if (pollingIntervalId) clearInterval(pollingIntervalId); // Clear existing if any
    console.log('Starting battle polling...');
    pollingIntervalId = setInterval(() => {
        if (battle.value && battle.value.status === 'active') {
             console.log('Polling for battle updates...');
             // Use fetchBattleById to refresh the specific battle data
             gameStore.fetchBattleById(battleId.value).catch(err => {
                 console.error("Polling error:", err);
                 // Stop polling if battle fetch fails repeatedly?
                 // clearInterval(pollingIntervalId);
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
function selectAttack(attack) {
    if (!submittingAction.value && canAct.value) {
        selectedAttackId.value = attack.id;
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
  await fetchBattleData(); // Initial fetch
  // Start polling only if the battle is active after initial fetch
  if (battle.value && battle.value.status === 'active') {
      startPolling();
  }
  scrollLogToBottom(); // Scroll down on initial load
});

onUnmounted(() => {
  stopPolling(); // Clean up interval
  gameStore.clearMessages(); // Clear battle messages when leaving
});

// Watch for changes in the summary length to scroll down
watch(() => battle.value?.last_turn_summary?.length, (newLength, oldLength) => {
  if (newLength > oldLength) { // Only scroll if new messages were added
    scrollLogToBottom();
  }
});

// Watch for status changes
watch(() => battle.value?.status, (newStatus) => {
    if (newStatus === 'finished' || newStatus === 'declined') {
        stopPolling();
        scrollLogToBottom(); // Scroll down to see final message
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
      
      <!-- Player Info Display (Layout Updated) -->
      <div class="players-display">
          <!-- User Card -->
          <div class="player-card user">
              <h3>{{ userPlayer?.username }} (You)</h3>
              <!-- Stat Badges Below Name -->
              <div class="stat-badges-container">
                  <span class="stat-badges"> 
                     <template v-for="(stage, stat) in userStatStages" :key="stat">
                         <span v-if="stage !== 0" :class="['stat-badge', `badge-${stat}`]">
                             {{ stat.toUpperCase() }} {{ stage > 0 ? '+' : '' }}{{ stage }}
                         </span>
                     </template>
                  </span>
              </div>
              <!-- HP Text and Bar on Same Line -->
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
               <!-- Stat Badges Below Name -->
               <div class="stat-badges-container">
                   <span class="stat-badges">
                        <template v-for="(stage, stat) in opponentStatStages" :key="stat">
                           <span v-if="stage !== 0" :class="['stat-badge', `badge-${stat}`]">
                               {{ stat.toUpperCase() }} {{ stage > 0 ? '+' : '' }}{{ stage }}
                           </span>
                       </template>
                   </span>
               </div>
                <!-- HP Text and Bar on Same Line -->
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

      <!-- Momentum Bar (Perspective Aware) -->
      <div 
          class="momentum-bar-container" 
          :class="userPlayerRole === 'player2' ? 'perspective-player2' : 'perspective-player1'"
      >
          <div class="momentum-labels">
              <!-- Labels might need conditional flipping too? Or leave as P1/P2 -->
              <span class="label-p1">{{ momentumDisplayP1 }}</span>
              <span class="label-title" :class="momentumAdvantage">Momentum</span> 
              <span class="label-p2">{{ momentumDisplayP2 }}</span>
          </div>
          <div class="momentum-bar">
              <!-- FILL uses VISUAL percentage -->
              <div class="momentum-bar-fill" :style="{ width: visualP1Percent + '%' }"></div> 
              <!-- Marker uses ABSOLUTE advantage -->
              <div class="momentum-bar-marker" :class="momentumAdvantage"></div>
              <!-- Preview Overlay uses ABSOLUTE calculations via previewStyle -->
              <div 
                 v-if="momentumPreview" 
                 class="momentum-preview" 
                 :class="momentumPreview.role"
                 :style="previewStyle" 
              ></div>
          </div>
      </div>

       <!-- Messages and Turn Summary -->
      <div class="messages" ref="battleLogContainer">
            <p v-if="battleMessage" class="battle-message">{{ battleMessage }}</p>
            <p v-if="battleError" class="error-message">Error: {{ battleError }}</p>
            
            <!-- Display structured log -->
            <div v-if="battle.last_turn_summary && battle.last_turn_summary.length" class="turn-summary">
                <ul>
                    <li 
                        v-for="(entry, index) in battle.last_turn_summary" 
                        :key="battle.id + '- ' + index" 
                        :class="[
                            'log-entry-container', 
                            { 
                                'log-user': entry.source === userPlayerRole, 
                                'log-opponent': entry.source !== userPlayerRole && entry.source !== 'system',
                                'log-system': entry.source === 'system'
                            }
                        ]"
                    >
                        <span 
                           :class="[
                               'log-bubble', 
                               `bubble-effect-${entry.effect_type}`,
                               entry.effect_details?.stat ? `bubble-stat-${entry.effect_details.stat}` : ''
                           ]"
                        >
                            <!-- Display Emoji for 'action' type -->
                            <span v-if="entry.effect_type === 'action' && entry.effect_details?.emoji" class="log-emoji">{{ entry.effect_details.emoji }}</span>
                            
                            <!-- Add arrow for stat changes -->
                            <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0" class="stat-arrow up">▲</span>
                            <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0" class="stat-arrow down">▼</span>
                            
                            {{ entry.text }}
                        </span>
                    </li>
                </ul>
            </div>
            <!-- Add a placeholder/spacer at the bottom if needed -->
             <div style="height: 1px;"></div> 
      </div>

       <!-- Action Selection -->
       <div v-if="battle.status === 'active' && userPlayer" class="action-selection">
            <!-- REMOVED v-if="canAct" wrapper -->
            <h3>Choose your Attack:</h3>
            <!-- Iterate over my_selected_attacks -->
            <!-- Ensure disabled overlay class is still applied -->
           <ul class="attacks-grid battle-attacks" :class="{ 'disabled-overlay': !canAct }">
             <li 
                v-for="action in mySelectedAttacks" 
                :key="action.id" 
                class="attack-card" 
                :class="{ 
                    selected: selectedAttackId === action.id && canAct,
                    disabled: !canAct || submittingAction 
                 }" 
                @click="canAct && selectAttack(action)" 
                @mouseenter="previewAttackMomentum(action)" 
                @mouseleave="clearMomentumPreview"
                role="button" 
                :aria-pressed="selectedAttackId === action.id && canAct"
                :tabindex="!canAct || submittingAction ? -1 : 0"
             >
               <AttackCardDisplay :attack="action"></AttackCardDisplay> 
             </li>
           </ul>
            <!-- Always render the list, rely on CSS for disabled state -->
           <p v-if="!mySelectedAttacks.length" class="no-items-message">No attacks selected or available.</p>
           <!-- REMOVED v-else waiting message -->

           <button 
                @click="submitAction"
                :disabled="!canAct || !selectedAttackId || submittingAction"
                class="submit-action-button button button-primary"
            >
               <!-- Button text still correctly reflects canAct -->
               <span v-if="!canAct">Waiting for {{ opponentPlayer?.username }}...</span>
               <span v-else-if="submittingAction">Submitting...</span>
               <span v-else>Confirm Attack</span>
           </button>
       </div>

      <!-- Finished State -->
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
  max-width: 1800px; /* Increased width further */
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
    min-height: 150px; 
    max-height: 250px; 
    background-color: var(--color-background); /* Change background to main background */
    border: 1px solid var(--color-border);
    border-radius: 6px;
    display: flex; 
    flex-direction: column;
    overflow-y: auto; 
}

.battle-message,
.error-message {
    padding: 0 0.5rem; /* Add horizontal padding to messages */
    margin-bottom: 0.5rem;
    flex-shrink: 0; /* Prevent messages from shrinking */
}

.turn-summary {
    flex-grow: 1; 
    display: flex;
    flex-direction: column;
    /* overflow-y: auto; -> Moved to parent .messages */
    padding: 0 0.5rem; /* Add padding for scrollbar */
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

/* Default alignment (for system messages) */
.log-system {
   justify-content: center;
}

/* Align user bubbles left */
.log-user {
   justify-content: flex-start;
}

/* Align opponent bubbles right */
.log-opponent {
    justify-content: flex-end;
}

/* The bubble itself */
.log-bubble {
    padding: 0.4rem 0.8rem; 
    border-radius: 15px; 
    max-width: 70%; 
    word-wrap: break-word; 
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); /* Keep subtle shadow */
    line-height: 1.3; /* Ensure text fits well */
    display: inline-flex; /* Use flex for icon + text */
    align-items: center;
    gap: 0.3em;
}

/* User bubble style */
.log-user .log-bubble {
    background-color: var(--vt-c-indigo); /* Changed to indigo */
    color: white; 
    border-bottom-left-radius: 3px; 
}

/* Opponent bubble style */
.log-opponent .log-bubble {
    background-color: var(--vt-c-indigo); /* Already indigo, confirming */
    color: white;
    border-bottom-right-radius: 3px; 
}

/* System message style */
.log-system .log-bubble {
    color: var(--color-text-mute);
    font-style: italic;
    background-color: transparent; 
    box-shadow: none; /* Remove shadow for system messages */
    max-width: 90%; /* Allow system messages to be wider */
    text-align: center; /* Ensure text inside bubble is centered */
    border-radius: 0; /* No rounding for system messages */
    padding: 0.1rem 0.5rem; /* Less padding for system */
}

.action-selection {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--color-border);
}

.attacks-grid.battle-attacks {
    display: grid;
    /* Adjust columns based on available space, maybe fewer than 3 */
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); 
    gap: 0.8rem;
    list-style: none;
    padding: 0;
    margin: 0 0 1.5rem 0; /* Add bottom margin */
}

.attack-card {
    background-color: var(--color-background);
    border: 1px solid var(--color-border-hover);
    border-radius: 8px;
    padding: 0.8rem; /* Keep padding on the li */
    text-align: center;
    min-height: 110px; 
    display: flex; 
    flex-direction: column; 
    justify-content: center; 
    align-items: center; 
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
}

/* Keep hover, selected, disabled styles on the parent li */
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

/* ... (rest of styles) ... */

.submit-action-button {
    /* Base styles inherited from .button */
    padding: 0.8rem 1.5rem; 
    font-size: 1em;
    display: block; 
    margin: 1.5rem auto 0 auto; /* Adjust margin */
    min-width: 180px;
}

/* Override disabled state if needed (optional, .button:disabled might be sufficient) */
.submit-action-button:disabled {
    background-color: var(--color-background-mute); 
    border-color: var(--color-border); 
    color: var(--color-text-mute);
    cursor: not-allowed;
    opacity: 0.7;
    animation: none;
    box-shadow: none;
}

/* Ensure vt-c-green-rgb is defined if not already */
:root {
  /* Add other RGB values if needed */
  --vt-c-green-rgb: 66, 184, 131; /* Example for Vue Green */
}

.error-message {
    color: var(--vt-c-red);
    margin-bottom: 1rem;
}

.header-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem; /* Add some space below */
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
    min-height: 20px; /* Ensure space even if no badges */
}

.stat-badges {
    display: flex; /* Changed to flex */
    flex-wrap: wrap; /* Allow wrapping */
    gap: 0.4rem; 
    /* Removed margin-left */
}

.hp-display {
    display: flex; 
    align-items: center; 
    gap: 0.75rem; 
    margin-top: auto; 
}

/* Style for Momentum Display */
.momentum-display {
    font-size: 0.9em;
    color: var(--color-text-mute);
    text-align: right; /* Match HP text alignment */
    font-weight: bold;
    margin-bottom: 0.5rem; /* Space before HP */
}

/* --- Momentum Bar Styles (Updated for Uncertainty Preview) --- */
.momentum-bar-container {
    margin: 0.5rem 0 1.5rem 0; /* Adjust spacing */
    padding: 0.5rem 0;
}

.momentum-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.9em;
    color: var(--color-text-mute);
    margin-bottom: 0.3rem;
    padding: 0 5px; /* Align with bar padding */
    align-items: center; /* Vertically center labels */
}
.momentum-labels .label-title {
    font-weight: bold;
    color: var(--color-heading); /* Default/Neutral color */
    transition: color 0.3s ease;
}
/* --- UPDATED Advantage Classes --- */
.momentum-labels .label-title.user-advantage {
    color: var(--vt-c-blue);
}
.momentum-labels .label-title.opponent-advantage {
    color: var(--vt-c-red);
}
.momentum-labels .label-p1,
.momentum-labels .label-p2 {
    /* Make difference display less prominent? Or keep bold? */
    min-width: 2em; /* Add some min width to prevent layout shift */
    text-align: center;
}

.momentum-bar {
    height: 10px; 
    background-color: var(--vt-c-red); /* Bolder opponent side */
    border-radius: 5px;
    position: relative;
    overflow: hidden; /* Hide overflow of fill/preview */
    border: 1px solid var(--color-border);
}

.momentum-bar-fill {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: var(--fill-width, 50%); /* Default to 50% if no momentum */
    background-color: var(--vt-c-blue); /* Bolder user side */
    transition: width 0.4s ease-out;
}

.momentum-bar-marker {
    position: absolute;
    top: -3px; /* Position slightly above */
    bottom: -3px;
    width: 4px;
    background-color: var(--vt-c-white); /* White marker */
    left: 50%; 
    transform: translateX(-50%);
    border-radius: 2px;
    box-shadow: 0 0 3px rgba(0,0,0,0.5);
    transition: background-color 0.3s ease;
}

/* --- UPDATED Marker Advantage Classes --- */
.momentum-bar-marker.user-advantage {
    background-color: var(--vt-c-blue-dark); /* Darker blue for advantage */
}
.momentum-bar-marker.opponent-advantage {
    background-color: var(--vt-c-red-dark); /* Darker red for advantage */
}
/* Keep white for neutral */

.momentum-preview {
    position: absolute;
    top: 0; bottom: 0;
    background-color: rgba(255, 255, 255, 0.3);
    transition: left 0.2s ease-out, width 0.2s ease-out;
    pointer-events: none; 
    border: none; 
    /* Remove generic left/width - apply based on player class */
    /* left: var(--preview-start-percent, 50%); */ 
    /* width: calc(var(--preview-end-percent, 50%) - var(--preview-start-percent, 50%)); */
    border-left: 2px solid rgba(255, 255, 255, 0.5);
    border-right: 2px solid rgba(255, 255, 255, 0.5);
}

/* Preview positioning when Player 1 acts */
.momentum-preview.player1 {
    left: var(--preview-start-percent, 50%); 
    width: calc(var(--preview-end-percent, 50%) - var(--preview-start-percent, 50%));
}

/* Preview positioning when Player 2 acts */
.momentum-preview.player2 {
    left: var(--preview-end-percent, 50%); /* Start at the lower percentage */
    width: calc(var(--preview-start-percent, 50%) - var(--preview-end-percent, 50%)); /* Width is difference (start - end) */
}

/* --- Perspective Flipping --- */

/* Flip the entire bar visually for Player 2 */
.perspective-player2 .momentum-bar {
    transform: scaleX(-1);
    /* Background should represent User (P2 = blue) */
    background-color: var(--vt-c-blue);
}

/* Fill color should represent Opponent (P1 = red) */
.perspective-player2 .momentum-bar-fill {
    background-color: var(--vt-c-red);
}

/* Flip the content *back* so it's not mirrored */
.perspective-player2 .momentum-bar > *:not(.momentum-bar-fill) { 
    transform: scaleX(-1);
}
.perspective-player2 .momentum-bar-fill {
    transform: scaleX(-1);
}

/* Optional: Flip labels as well if desired */
/* ... */

/* --- End Perspective Flipping --- */

/* --- ADDED BACK: Stat Badge Colors --- */
.stat-badge {
    /* Keep existing badge styles */
    display: inline-block;
    padding: 0.2rem 0.5rem;
    font-size: 0.75em;
    font-weight: bold;
    border-radius: 8px; 
    color: white; 
    text-transform: uppercase;
    line-height: 1.1; 
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); 
}
.badge-attack {
    background-color: var(--vt-c-red); 
}
.badge-defense {
     background-color: var(--vt-c-blue); 
}
.badge-speed {
     background-color: var(--vt-c-yellow-darker); 
     color: white; /* Ensure text stays white */
}
/* ------------------------------------ */

/* Optional: Add overlay effect to the grid when disabled */
.attacks-grid.disabled-overlay::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.1); /* Subtle dark overlay */
    border-radius: 8px; /* Match grid container if it has one */
    pointer-events: none; /* Ensure clicks go through to disabled elements if needed */
    z-index: 1; /* Place above cards but below potential popups */
}
.attacks-grid {
    position: relative; /* Needed for absolute positioning of overlay */
}

.waiting-message {
    /* Remove this style block if no longer needed */
    text-align: center;
    padding: 2rem 0;
    color: var(--color-text-mute);
    font-style: italic;
}

</style> 