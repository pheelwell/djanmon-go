<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router'; // Import useRouter
import { useAuthStore } from '@/stores/auth';
import { useGameStore } from '@/stores/game'; // Import the game store
import MovesetManager from '@/components/MovesetManager.vue';
// import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // Likely unused here now
// import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue'; // Now inside UserProfilePanel
import UserProfilePanel from '@/components/UserProfilePanel.vue'; // <-- Import
import ActiveBattleDisplay from '@/components/ActiveBattleDisplay.vue'; // <-- Import
import IncomingChallengesList from '@/components/IncomingChallengesList.vue'; // <-- Import
import AvailablePlayersList from '@/components/AvailablePlayersList.vue'; // <-- Import

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();

const user = computed(() => authStore.currentUser);

const availableUsers = computed(() => gameStore.users);
const pendingBattles = computed(() => gameStore.pendingBattles);
const activeBattle = computed(() => gameStore.activeBattle);
const isLoadingUsers = computed(() => gameStore.isLoadingUsers);
const isLoadingPendingBattles = computed(() => gameStore.isLoadingPendingBattles);
const isLoadingActiveBattle = computed(() => gameStore.isLoadingActiveBattle);
const actionError = computed(() => gameStore.actionError);
const actionSuccessMessage = computed(() => gameStore.actionSuccessMessage);

const challengingUserId = ref(null);
const respondingBattleId = ref(null);
let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 1000;

const opponent = computed(() => {
    if (!activeBattle.value || !user.value) return null;
    return activeBattle.value.player1.id === user.value.id 
        ? activeBattle.value.player2 
        : activeBattle.value.player1;
});

onMounted(() => {
  gameStore.fetchUsers();
  gameStore.fetchPendingBattles();
  gameStore.fetchActiveBattle();
  gameStore.clearMessages(); 
  pollingIntervalId = setInterval(() => {
      // console.log('Polling for updates...'); 
      gameStore.fetchUsers(true);
      gameStore.fetchPendingBattles(true);
      gameStore.fetchActiveBattle(true);
  }, POLLING_INTERVAL_MS);
});

onUnmounted(() => {
  if (pollingIntervalId) {
    clearInterval(pollingIntervalId);
  }
});

// --- Action Handlers ---
async function handleChallenge(opponentId) {
    challengingUserId.value = opponentId;
    await gameStore.challengeUser(opponentId);
    challengingUserId.value = null;
}

async function handleResponse(battleId, responseAction) {
    respondingBattleId.value = battleId;
    const result = await gameStore.respondToBattle(battleId, responseAction);
    respondingBattleId.value = null;
    if (result.accepted && result.battle) {
        goToBattle(result.battle.id);
    }
}

function goToBattle(battleId) {
    router.push({ name: 'battle', params: { id: battleId } });
}

function handleLogout() {
    authStore.logout();
    router.push({ name: 'login' });
}

</script>

<template>
  <!-- Fixed Logout Button -->
  <button 
    v-if="user" 
    @click="handleLogout" 
    class="button button-danger logout-button-fixed"
  >
    Logout
  </button>

  <main class="home-view">
    <!-- UserProfilePanel or loading state -->
    <UserProfilePanel v-if="user" :user="user" />
    <div v-else class="panel">
      <p>Loading user profile...</p>
    </div>

    <!-- Integrated Moveset Manager -->
    <div v-if="user" class="moveset-manager-panel panel">
        <MovesetManager />
    </div>

    <!-- Actions Panel (UPDATED) -->
    <div class="actions-panel panel">
        <h2>Command Center</h2>
         <!-- Action Feedback -->
        <div class="action-feedback">
            <p v-if="actionError" class="error-message">⚠️ {{ actionError }}</p>
            <p v-if="actionSuccessMessage" class="success-message">✅ {{ actionSuccessMessage }}</p>
        </div>

        <!-- === UPDATED COMMAND CENTER Structure === -->

        <!-- 1. Loading state for active battle check -->
        <div v-if="isLoadingActiveBattle" class="loading-placeholder">
            Checking battle status...
        </div>
        
        <!-- 2. Active Battle Display -->
        <ActiveBattleDisplay
            v-else-if="activeBattle && opponent" 
            :activeBattle="activeBattle"
            :opponent="opponent"
            @goToBattle="goToBattle"
        />

        <!-- 3. If NO active battle AND NOT loading, show Challenges & Player List -->
        <div v-else class="no-active-battle-layout"> 

            <!-- Incoming Challenges Section - Use Component -->
            <IncomingChallengesList
                :isLoading="isLoadingPendingBattles"
                :battles="pendingBattles"
                :respondingBattleId="respondingBattleId"
                @respond="handleResponse"
            />

            <!-- Available Players Section - Use Component -->
            <AvailablePlayersList
                :isLoading="isLoadingUsers"
                :players="availableUsers"
                :challengingUserId="challengingUserId"
                @challenge="handleChallenge"
            />

        </div>
        <!-- === END UPDATED COMMAND CENTER === -->

    </div>
    
    <!-- Modals Removed -->

  </main>
</template>

<style scoped>
/* Adjust grid layout if necessary for new panels */
.home-view {
  display: grid;
  /* Example: Keep 2 columns, maybe adjust widths */
  /* grid-template-columns: minmax(400px, 450px) 1fr; */
  grid-template-columns: 1fr; /* Start with single column */
  gap: 2rem;
  padding: 2rem;
  max-width: 1400px; /* Allow wider view */
  margin: 1rem auto;
}

/* Example for wider screens */
@media (min-width: 1200px) {
  .home-view {
    /* Revert to fixed width first column, flexible second */
    grid-template-columns: 450px 1fr;
    /* Updated rows/areas: user panel now contains stats, moveset spans bottom */
    grid-template-rows: auto auto; /* Row 1: user/actions, Row 2: moveset */
    grid-template-areas:
      "user actions"
      "moveset moveset"; /* Moveset spans both columns */
  }
  .user-panel-component { grid-area: user; }
  /* .stats-editor-panel removed */
  .moveset-manager-panel { grid-area: moveset; }
  .actions-panel { grid-area: actions; }
}

.panel { /* Keep general panel styles */
    background-color: var(--color-background-soft);
    padding: 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.actions-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem; /* Space between title, feedback, and content */
}

.actions-panel h2 {
    margin-top: 0; /* Added to reset */
    margin-bottom: 0; /* Reduce default bottom margin */
}

.action-feedback {
     margin-bottom: 0; /* Remove extra bottom margin */
     order: -1; /* Keep feedback at top */
}

.error-message, .success-message { /* Basic styling for feedback messages */
    padding: 0.8rem 1rem;
    border-radius: 6px;
    font-weight: 500;
    text-align: center;
    margin-bottom: 1rem; /* Space below message if present */
}
.error-message {
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
  border: 1px solid var(--vt-c-red);
}
.success-message {
  background-color: var(--vt-c-green-soft);
  color: var(--vt-c-green-dark);
  border: 1px solid var(--vt-c-green);
}

/* Generic Loading Placeholder style */
.loading-placeholder {
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-mute);
    font-style: italic;
    border-radius: 8px;
    border: 1px dashed var(--color-border);
    /* margin-top: 1rem; Removed */
}

.no-active-battle-layout {
    display: flex;
    flex-direction: column;
    gap: 1.5rem; /* Space between challenges and players */
}

/* Keep fixed logout button style */
.logout-button-fixed {
    position: fixed;
    top: 1.5rem; /* Adjust spacing from top */
    right: 1.5rem; /* Adjust spacing from right */
    z-index: 1000; /* Ensure it stays on top */
}

/* Remove modal styles */
/* .modal-overlay { ... } */
/* .modal-content { ... } */
/* .close-button { ... } */

/* Other existing styles for actions panel, lists, buttons etc. */
/* ... */

</style>
