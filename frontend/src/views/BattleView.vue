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
const POLLING_INTERVAL_MS = 5000;
const MOMENTUM_THRESHOLD = 50; // Threshold for pendulum swing

// State for the previewed attack card
const selectedAttackPreview = ref(null); 
const previewedMinCost = ref(null);
const previewedMaxCost = ref(null);

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

// --- Computed: Detailed Registered Scripts (for easier filtering) ---
const detailedRegisteredScripts = computed(() => {
    return displayedBattleState.value?.detailed_registered_scripts || [];
});

const userTargetedScripts = computed(() => {
    if (!userPlayerRole.value) return [];
    return detailedRegisteredScripts.value.filter(script => {
        const triggerWho = script.trigger_who;
        const originalAttacker = script.original_attacker_role;
        // Primarily target user if: Trigger was ME and user was original attacker OR Trigger was ENEMY and user was original target
        return (triggerWho === 'ME' && originalAttacker === userPlayerRole.value) || 
               (triggerWho === 'ENEMY' && originalAttacker !== userPlayerRole.value); // Assuming binary player roles
    });
});

const opponentTargetedScripts = computed(() => {
    if (!userPlayerRole.value) return [];
    return detailedRegisteredScripts.value.filter(script => {
        const triggerWho = script.trigger_who;
        const originalAttacker = script.original_attacker_role;
        // Primarily target opponent if: Trigger was ME and user was NOT original attacker OR Trigger was ENEMY and user WAS original attacker
        return (triggerWho === 'ME' && originalAttacker !== userPlayerRole.value) || 
               (triggerWho === 'ENEMY' && originalAttacker === userPlayerRole.value);
    });
});

const anyTargetedScripts = computed(() => {
    return detailedRegisteredScripts.value.filter(script => script.trigger_who === 'ANY');
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
    if (!activePlayerRole.value) return ['momentum-fill']; // Default
    const isUserTurn = activePlayerRole.value === userPlayerRole.value;
    return [
        'momentum-fill',
        isUserTurn ? 'user-momentum' : 'opponent-momentum',
        isUserTurn ? 'fill-left' : 'fill-right' // <-- Add alignment class
    ];
});

// Available actions now come directly from the displayed battle data
const mySelectedAttacks = computed(() => {
    // Ensure attacks have unique keys if IDs might not be enough (though they should be)
    return (displayedBattleState.value?.my_selected_attacks || []).map((attack, index) => ({
        ...attack,
        key: `${attack.id}-${index}` // Simple unique key
    }));
});

// --- Client-side Stat Calculation Helpers ---
// Simple stat stage modifier calculation (matches basic backend logic)
function calculateStatModifier(stage) {
  stage = clamp(stage, -6, 6);
  if (stage >= 0) {
    return (2 + stage) / 2;
    } else {
    return 2 / (2 - stage);
  }
}

// Client-side version for previewing momentum cost
// NOTE: This is simplified and might not perfectly match complex backend edge cases
function calculateMomentumCostClientSide(baseCost, userStats, userStages) {
    const speedStage = userStages?.speed ?? 0;
    const speedModifier = calculateStatModifier(speedStage);
    const effectiveSpeed = Math.max(1, (userStats?.speed ?? 50) * speedModifier);

    // Simplified cost calculation based on speed ranges
    let costMultiplier = 1.0;
    if (effectiveSpeed >= 100) costMultiplier = 0.75; // Faster = cheaper
    else if (effectiveSpeed <= 25) costMultiplier = 1.25; // Slower = costlier
    
    // Example: Introduce slight randomness or range
    const calculatedCost = Math.round(baseCost * costMultiplier);
    const minCost = Math.round(calculatedCost * 0.9); 
    const maxCost = Math.round(calculatedCost * 1.1);

    // Clamp results to sensible bounds
    const finalMin = clamp(minCost, 0, 100);
    const finalMax = clamp(maxCost, 0, 100);

    return [Math.min(finalMin, finalMax), finalMax]; 
}
// --- End Client-side Helpers ---

// Computed for preview visibility
const isPreviewActive = computed(() => 
    canAct.value && 
    previewedMinCost.value !== null && 
    previewedMaxCost.value !== null
);

// NEW: Computed style for the cost preview block
const costPreviewStyle = computed(() => {
  if (!isPreviewActive.value) return {}; // Return empty if not active

  const currentPercent = activePlayerMomentumPercent.value;
  const minCostPercent = clamp(previewedMinCost.value ?? 0, 0, 100);
  const maxCostPercent = clamp(previewedMaxCost.value ?? 0, 0, 100);

  // Calculate start and end points of the preview block (remaining momentum)
  const previewEndPercent = clamp(currentPercent - minCostPercent, 0, currentPercent);
  const previewStartPercent = clamp(currentPercent - maxCostPercent, 0, currentPercent);

  const calculatedWidth = Math.max(0, previewEndPercent - previewStartPercent); // Ensure width is not negative

   console.log(`[Preview Style] Current: ${currentPercent}, MinCost: ${minCostPercent}, MaxCost: ${maxCostPercent}, Start: ${previewStartPercent}, End: ${previewEndPercent}, Width: ${calculatedWidth}`);

  return {
    left: `${previewStartPercent}%`,
    width: `${calculatedWidth}%`
  };
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

// Function to calculate and show preview cost
function previewAttackCost(attack) {
    console.log('[Preview] Attack:', JSON.parse(JSON.stringify(attack || {})));
    if (!attack || !currentUser.value) {
        console.log('[Preview] No attack or user, clearing.');
        clearAttackCostPreview();
        return;
    }
    // Use pre-calculated if available (from mobile click data)
    if (attack.calculated_min_cost !== undefined && attack.calculated_max_cost !== undefined) {
         previewedMinCost.value = attack.calculated_min_cost;
         previewedMaxCost.value = attack.calculated_max_cost;
         console.log(`[Preview] Using pre-calculated: min=${previewedMinCost.value}, max=${previewedMaxCost.value}`);
    } else {
         // Calculate client-side (for desktop hover or if data missing)
         console.log('[Preview] Calculating client-side...');
         const userStats = {
            hp: currentUser.value.hp,
            attack: currentUser.value.attack,
            defense: currentUser.value.defense,
            speed: currentUser.value.speed
         };
         console.log('[Preview] User Stats:', userStats);
         console.log('[Preview] User Stages:', JSON.parse(JSON.stringify(userStatStages.value || {})));
         const [minCost, maxCost] = calculateMomentumCostClientSide(
             attack.momentum_cost,
             userStats,
             userStatStages.value // Use the computed user stages
         );
         previewedMinCost.value = minCost;
         previewedMaxCost.value = maxCost;
         console.log(`[Preview] Calculated client-side: min=${previewedMinCost.value}, max=${previewedMaxCost.value}`);
    }
}

// Function to clear preview cost
function clearAttackCostPreview() {
    console.log('[Preview] Clearing preview costs.');
    previewedMinCost.value = null;
    previewedMaxCost.value = null;
}

// --- Update Event Handlers ---

// Desktop Grid Click Handler
function handleGridAttackClick(attack) {
    clearAttackCostPreview(); // Clear preview on click before submitting
    if (!submittingAction.value && canAct.value && attack?.id) {
        submitAction(attack.id);
    }
}

// MODIFY: submitAction
async function submitAction(attackIdToSubmit) {
    if (!attackIdToSubmit || !displayedBattleState.value || !canAct.value || submittingAction.value) return;
    
    submittingAction.value = true;
    selectedAttackPreview.value = null; 
    clearAttackCostPreview(); // <-- Clear preview here too
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
        // Check displayed state status
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

// Mobile Emoji Button Click Handler
function handleEmojiClick(attack) {
    if (!submittingAction.value && attack) {
        selectedAttackPreview.value = attack;
        previewAttackCost(attack); // Show preview for the selected attack
    }
}

// Mobile Preview Card Click Handler
function handlePreviewCardClick() {
    if (selectedAttackPreview.value && canAct.value && !submittingAction.value) {
        // Submit action first, which already clears preview
        submitAction(selectedAttackPreview.value.id);
    } else {
        // If not clickable, just clear the preview
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

// --- Update Watchers --- 
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
    
    // Clear preview if it's no longer the user's turn or preview is active
    if (newBattleState?.whose_turn !== userPlayerRole.value && isPreviewActive.value) {
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
          <div class="player-display-wrapper user-side">
              <div class="player-avatar-large">
                   <img 
                      v-if="userPlayer?.profile_picture_base64" 
                      :src="'data:image/png;base64,' + userPlayer.profile_picture_base64" 
                      alt="Profile Picture" 
                      class="player-avatar-img"
                   />
                   <div v-else class="player-avatar-placeholder">?</div>
              </div>
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

          <!-- Momentum Display Panel -->
          <div class="momentum-display panel">
              <div class="momentum-label">MOMENTUM</div>
              <div class="momentum-meter">
                 <!-- Main Fill Bar -->
                 <div 
                    :class="activeMomentumBarClass" 
                    :style="activeMomentumBarStyle"
                 >
                    <span class="momentum-value">{{ activePlayerMomentumValue }}</span> 
                 </div>
                 <!-- Cost Preview Block -->
                 <div v-if="isPreviewActive" class="momentum-cost-preview" :style="costPreviewStyle"></div>
              </div>
              <!-- NEW: Registered Scripts Display -->
              <div class="registered-scripts-display">
                  <div class="scripts-user-side">
                     <span v-for="script in userTargetedScripts" 
                            :key="script.registration_id" 
                            class="script-icon-wrapper" 
                            :data-tooltip="script.tooltip_description">
                          {{ script.icon_emoji || '⚙️' }}
                      </span>
                  </div>
                  <div class="scripts-shared-side">
                     <span v-for="script in anyTargetedScripts" 
                            :key="script.registration_id" 
                            class="script-icon-wrapper" 
                            :data-tooltip="script.tooltip_description">
                          {{ script.icon_emoji || '⚙️' }}
                      </span>
                  </div>
                  <div class="scripts-opponent-side">
                     <span v-for="script in opponentTargetedScripts" 
                            :key="script.registration_id" 
                            class="script-icon-wrapper" 
                            :data-tooltip="script.tooltip_description">
                          {{ script.icon_emoji || '⚙️' }}
                      </span>
                  </div>
              </div>
              <!-- END: Registered Scripts Display -->
          </div>

          <!-- Opponent Info Panel -->
           <div class="player-display-wrapper opponent-side">
              <div class="player-avatar-large">
                   <img 
                      v-if="opponentPlayer?.profile_picture_base64" 
                      :src="'data:image/png;base64,' + opponentPlayer.profile_picture_base64" 
                      alt="Profile Picture" 
                      class="player-avatar-img"
                   />
                   <div v-else class="player-avatar-placeholder">?</div>
              </div>
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
                                @mouseover.native="previewAttackCost($event.target.__vueParentComponent.ctx.attack)" 
                                @mouseleave.native="clearAttackCostPreview"
                            />
                            <!-- NOTE: Need to enhance AttackGrid or handle hover differently -->
                            <!-- The above @mouseover/@mouseleave might not work directly on component -->
                            <!-- Alternative: Add handlers in AttackGrid's #item slot -->
                            <div v-else-if="!canAct && mySelectedAttacks.length === 0" class="waiting-message">WAITING...</div>
                            <div v-else-if="mySelectedAttacks.length === 0" class="waiting-message">NO ATTACKS?</div>
                </div>
                        <div v-else class="action-placeholder">
                            <p>...</p>
                        </div>
                    </div>

                    <!-- MOBILE: New Action Area -->
                    <div class="action-area-mobile">
                        <div v-if="displayedBattleState.status === 'active' && userPlayer">
                            <!-- Mobile: Single Attack Preview Area -->
                            <div class="mobile-attack-preview" :class="{ 'has-preview': selectedAttackPreview }">
                                <AttackCardDisplay
                                    v-if="selectedAttackPreview"
                                    :attack="selectedAttackPreview"
                                    @click="handlePreviewCardClick"
                                    class="preview-card"
                                    :class="{ 'clickable': canAct && !submittingAction }"
                                />
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
           <!-- Finished State Content -->
                <div v-if="displayedBattleState.status === 'finished'" class="battle-finished-content">
          <p v-if="displayedBattleState.winner?.id === currentUser?.id" class="win-message">🎉 You won! 🎉</p>
          <p v-else-if="displayedBattleState.winner" class="lose-message">😢 {{ displayedBattleState.winner.username }} won! 😢</p>
          <p v-else class="draw-message">The battle ended unexpectedly.</p>
                    <router-link :to="{ name: 'home' }" class="btn return-home-button">Return Home</router-link>
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
    max-width: 1200px;
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
    padding: 6px 12px;
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
    align-items: stretch; /* Change alignment */
    gap: calc(var(--element-gap) * 1); /* Reduce gap slightly */
    margin-top: var(--element-gap);
    margin-bottom: var(--element-gap);
}

/* NEW: Player Display Wrapper */
.player-display-wrapper {
    display: flex;
    align-items: flex-start; /* Align items to the top */
    gap: 10px;
    flex: 1 1 35%; /* Adjust flex basis */
    min-width: 220px; /* Increase min-width */
}

/* NEW: Styles for the large avatar */
.player-avatar-large {
    width: 80px; /* Much larger size */
    height: 80px;
    flex-shrink: 0; /* Don't shrink the avatar */
    background-color: var(--color-background-mute);
    border: var(--border-width) solid var(--color-border);
    box-shadow: 2px 2px 0px var(--color-border); /* Pixel shadow */
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
}

.player-avatar-img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
}

.player-avatar-placeholder {
    font-size: 3em; /* Larger placeholder */
    color: var(--color-text-muted);
    font-family: var(--font-primary);
}

.player-info {
    flex: 1; /* Allow card to take remaining space */
    /* Removed min-width from here as wrapper handles it */
}

/* Adjust opponent wrapper order if needed */
.player-display-wrapper.opponent-side {
    flex-direction: row-reverse; /* Place avatar on the right */
}

.momentum-display {
    flex: 1 1 20%; /* Adjust flex basis */
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: flex-start; /* Align content to top */
    min-width: 150px;
    gap: 8px;
    padding-top: 10px; /* Add padding to align vertically */
    padding-bottom: 10px;
}

.momentum-label {
    font-size: 1em;
    color: var(--color-text);
    text-transform: uppercase;
}
.momentum-meter {
    height: 25px; 
    background-color: #333;
    border: 1px solid var(--color-border);
    position: relative; /* Changed from relative */
    overflow: hidden; 
    padding: 1px; 
    box-shadow: inset 1px 1px 0px rgba(0,0,0,0.5); 
}
.momentum-fill {
    position: absolute; /* Changed to absolute */
    top: 1px;
    bottom: 1px;
    width: var(--momentum-percent, 0%); /* Width set by inline style */
    transition: width 0.5s ease-in-out, left 0.3s ease, right 0.3s ease; /* Add transitions */
    display: flex;
    align-items: center;
    justify-content: center; 
}
/* Alignment classes */
.momentum-fill.fill-left {
    left: 1px;
    right: auto;
}
.momentum-fill.fill-right {
    right: 1px;
    left: auto;
}
/* Color classes (unchanged) */
.momentum-fill.user-momentum {
    background: var(--color-momentum-user); 
    color: var(--color-bg); 
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2);
}
.momentum-fill.opponent-momentum {
    background: var(--color-momentum-opponent); 
    color: var(--color-bg); 
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2);
}
.momentum-value {
    font-size: 0.9em;
    font-weight: normal; 
    color: black;
}

/* NEW: Cost Preview Block Style */
.momentum-cost-preview {
    position: absolute;
    top: 1px; /* Match fill bar positioning */
    bottom: 1px;
    /* left and width are set by inline style */
    background-color: rgba(255, 255, 0, 0.4); /* Yellowish, more transparent */
    z-index: 5; /* Below fill bar text (if it has higher z-index), above meter background */
    transition: left 0.2s ease-out, width 0.2s ease-out; /* Smooth transition */
    pointer-events: none; 
    border-left: 1px solid rgba(255, 255, 0, 0.7);
    border-right: 1px solid rgba(255, 255, 0, 0.7);
    box-sizing: border-box;
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
    .battle-log-container {
        padding: 5px; /* Reduced padding */
        min-height: none; /* Adjusted min height */
        height: 400px;
}

/* Ensure the new responsive rules are applied if needed */
@media (max-width: 800px) { 
    
    .battle-log-container {
        padding: 5px; /* Reduced padding */
        min-height: 1000px; /* Adjusted min height */
        max-height: none;
        height:none;
    }
    /* --- NEW Fullscreen Mobile Layout --- */
    .battle-screen {
    display: flex;
        flex-direction: column;
        height: 100vh; /* Or 100dvh */
        width: 100%;
        max-width: none;
        margin: 0;
        padding: 0; 
        box-sizing: border-box;
        background-color: var(--color-bg);
        gap: 0; 
    }

    /* --- Mobile Header Styling --- */
    .battle-header {
        order: 0; /* Very first element */
        position: sticky;
        top: 0;
        z-index: 30; /* Above player bar */
        flex-shrink: 0; 
        padding: 2px 8px; /* Very compact padding */
        background-color: var(--color-panel-bg); /* Give it background */
        border-bottom: var(--border-width) solid var(--color-border);
        display: flex; /* Ensure flex properties apply */
        justify-content: space-between;
        align-items: center;
        gap: 5px;
    }
    .battle-header h1 {
        font-size: 1em; /* Smaller title */
        margin: 0;
    }
    .battle-header .battle-status {
        font-size: 0.8em;
    }
    .battle-header .btn-concede {
        font-size: 0.7em;
        padding: 2px 5px; /* Smaller button */
    }

    /* --- Hide Desktop Elements --- */
    /* .battle-header, REMOVED from hide rule */ 
    /* .momentum-display, REMOVED from hide rule */ 
    .action-area-desktop,
    .battle-log > .panel-title, /* Hide original log title */
    .action-select > .panel-title /* Hide original action title */
     { 
        display: none !important; 
    }

    /* --- Sticky Top Bar (Repurposing .main-display) --- */
    .main-display {
        order: 1; /* Position at top */
        position: sticky;
        top: 30px; /* ADJUSTED - Approx height of mobile header */
        z-index: 20; /* Ensure above content */
        display: flex;
        flex-direction: column; /* STACK VERTICALLY */
        align-items: stretch; /* Stretch items horizontally */
        flex-shrink: 0;
        margin: -1;
        padding: 4px 8px; /* Consistent padding */
        gap: 4px; /* Gap between stacked items */
        background-color: var(--color-panel-bg); 
        border-bottom: var(--border-width) solid var(--color-border);
        margin: 0;
    }

    /* Remove horizontal flex sizing/basis from children */
    .main-display > * { 
        flex-basis: auto !important; 
        min-width: initial !important;
        flex: initial !important; /* Remove flex grow/shrink */
    }
    
    /* Set order for stacking */
    .main-display .player-display-wrapper.opponent-side {
         order: 1; /* Opponent first */
         flex-direction: row-reverse; /* Keep avatar right */
    }
    .main-display .momentum-display {
         order: 2; /* Momentum second */
         /* Keep compact styling */
         padding: 2px 4px;
         border: none; 
         box-shadow: none;
         background: transparent;
         gap: 2px; 
         /* Add a slight border top/bottom for separation? */
         border-top: 1px solid var(--color-border-light);
         border-bottom: 1px solid var(--color-border-light);
         margin: 2px 0;
    }
    .main-display .player-display-wrapper.user-side {
         order: 3; /* User last */
         flex-direction: row; /* Ensure user avatar is left */
        margin-bottom: 8;
    }

    /* Adjust player wrappers for vertical stacking */
    .main-display .player-display-wrapper {
        display: flex;
        align-items: center;
        gap: 8px; /* Restore slightly larger gap */
    }
    
    /* Keep avatar size moderate */
    .main-display .player-avatar-large {
        width: 60px; /* INCREASED size */
        height: 60px; /* INCREASED size */
        box-shadow: none; 
        border: 1px solid var(--color-border);
    }
     .main-display .player-avatar-placeholder {
        font-size: 1.8em; /* INCREASED size */
    }
    
     /* Revert some PlayerInfoCard shrinking, but keep somewhat compact */
    .main-display .player-info.panel {
        padding: 4px; 
        background: transparent; 
        font-size: 1em; /* Slightly larger than before */
    }
    .main-display .player-info.panel .player-name {
        font-size: 1em; /* Normal size */
    }
    .main-display .player-info.panel .hp-bar-container {
        height: 10px; /* Slightly thicker bar */
        margin-bottom: 3px;
    }
     .main-display .player-info.panel .hp-value {
         font-size: 1em;
     }
    .main-display .player-info.panel .status-indicators {
        gap: 3px; 
        margin-top: 3px;
    }
    .main-display .player-info.panel .status-icon,
    .main-display .player-info.panel .stat-stage-indicator {
        font-size: 1em; 
        padding: 1px 3px; 
        border-width: 1px;
    }

    /* Keep momentum compact */
    .main-display .momentum-label {
        font-size: 1em; /* Keep small */
        margin-bottom: 1px;
    }
    .main-display .momentum-meter {
        height: 12px; /* Keep thin */
        box-shadow: none;
        border: 1px solid var(--color-border);
    }
     .main-display .momentum-value { display: none; }
    .main-display .registered-scripts-display {
        min-height: 18px; 
        margin-top: 2px;
        padding: 0 2px;
    }
    .main-display .script-icon-wrapper { font-size: 0.9em; }
     .main-display .script-icon-wrapper::before { display: none; }


    /* --- Main Content Area (Repurposing .bottom-panels) --- */
    .bottom-panels {
        order: 2; /* Position after top bar */
        display: flex; /* Changed back to flex to allow log to grow */
        flex-direction: column;
        flex-grow: 1; 
        overflow: hidden; /* Contains scrolling */
        min-height: 0; 
        /* Removed padding/border etc. - it's just a container */
    }

    /* --- Scrollable Log Area --- */
    .battle-log {
        order: 1; /* Takes precedence within bottom-panels (only child now) */
        flex-grow: 1; /* Take available space */
        overflow-y: auto; 
        min-height: 0; 
        padding: 8px; /* Restore some padding */
        border: none;
        margin: 0;
        max-height: none; 
        font-size: 0.9em; 
        line-height: 1.4;
        position: static;
        transition: none; 
    }
     
    /* --- Sticky Bottom Action Bar --- */
    .action-select { /* Now a direct child of .battle-screen */
        order: 3; /* Position last */
        position: sticky;
        bottom: 0;
        z-index: 20; /* Ensure above content */
        flex-shrink: 0; 
        width: 100%; 
        padding: 5px 8px; /* Tighter padding */
        background-color: var(--color-panel-bg); 
        border-top: var(--border-width) solid var(--color-border);
        box-sizing: border-box; 
        margin: 0;
        display: flex; 
        flex-direction: column;
        min-height: auto;
        /* Panel reset applies, no need for extra bg/border removal */
    }

    /* Ensure mobile action area is shown and centered */
    .action-area-mobile {
        display: flex; 
        flex-direction: column;
        align-items: center;
        gap: 5px; /* Reduced gap */
        padding: 5px 0; /* Add some padding */
        width: 100%;
        /* flex-grow: 1; Remove grow if container shouldn't expand */
    }

    /* Adjust mobile preview/buttons if needed */
    .mobile-attack-preview {
        /* min-height: 140px; Maybe reduce? */
        height: 140px;
        width: 250px;
        margin-bottom: 3px;
         /* Reset border etc. */
        border: 1px dashed var(--color-border);
        box-sizing: border-box;
        display: flex; 
        justify-content: center; 
        align-items: center; 
        background-color: transparent; /* CHANGED from default/implied */
        color: var(--color-text-muted); /* Ensure placeholder text is visible */
    }
    .mobile-attack-preview.has-preview { 
        border-color: transparent; 
        padding: 0; 
        background-color: transparent; /* Ensure it stays transparent */
    }
    .mobile-attack-preview .preview-placeholder { font-size: 0.9em; }
    .mobile-emoji-buttons {
        display: flex; /* Ensure flex is still applied */
        flex-wrap: wrap; 
        justify-content: space-around; /* CHANGED from center */
        gap: 5px;
        padding: 3px 0;
        width: 100%;
    }
    .emoji-button {
        font-size: 1.6em; 
        padding: 4px;
        min-width: 35px; 
        min-height: 35px;
    }
    
    /* --- General / Cleanup --- */
    .panel { 
        /* Reset general panel styles used previously */
        padding: 0;
        margin: 0;
    }
    
    /* Adjust finished content for new layout */
    .battle-finished-content {
         /* Contained within action-select now */
         padding: 10px;
         gap: 10px;
    }
    .battle-finished-content .return-home-button { 
        font-size: 0.9em;
        padding: 6px 12px;
    }

}

/* NEW: Add fixed width only for desktop */
@media (min-width: 801px) {
    .battle-header {
        width: 1000px;
    }
}

/* ... rest of the styles ... */
/* Hide toggle button by default (desktop) - Already defined outside media query */
/* ... existing code ... */
</style> 