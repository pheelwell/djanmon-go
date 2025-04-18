<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router'; // Import useRouter
import { useAuthStore } from '@/stores/auth';
import { useGameStore } from '@/stores/game'; // Import the game store
import MovesetManager from '@/components/MovesetManager.vue';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue';

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
    <div v-if="user" class="user-panel panel">
      <h2>{{ user.username }}\'s Quarters</h2>
      
      <!-- Display Booster Credits -->
      <div class="user-currency">
        <span class="label">💰 Credits:</span>
        <span class="value">{{ user.booster_credits ?? 0 }}</span>
      </div>

      <!-- Basic Info Display (Stats bars removed) -->
       <div class="user-basic-info">
          <div class="stat-level">
              <span class="label">LVL</span>
              <!-- Assuming level is still a concept, adjust if not -->
              <span class="value">{{ user.level || '1' }}</span> 
          </div>
      </div>

      <!-- Embed Stats Editor directly -->
      <UserProfileStatsEditor />

    </div>
    <div v-else class="panel">
      <p>Loading user profile...</p>
    </div>

    <!-- Integrated Moveset Manager -->
    <div v-if="user" class="moveset-manager-panel panel">
        <MovesetManager />
    </div>

    <!-- Actions Panel (remains the same) -->
    <div class="actions-panel panel">
        <h2>Command Center</h2>
         <!-- Action Feedback -->
        <div class="action-feedback">
            <p v-if="actionError" class="error-message">⚠️ {{ actionError }}</p>
            <p v-if="actionSuccessMessage" class="success-message">✅ {{ actionSuccessMessage }}</p>
        </div>

        <!-- === REDESIGNED COMMAND CENTER === -->

        <!-- 1. Active Battle takes priority -->
        <div v-if="isLoadingActiveBattle" class="loading-placeholder">
            Checking battle status...
        </div>
        <div v-else-if="activeBattle && opponent" class="active-battle-display subsection">
            <h3>Active Battle</h3>
            <p>You are currently battling {{ opponent.username }}.</p>
            <button 
                @click="goToBattle(activeBattle.id)" 
                class="button button-primary resume-button"
            >
                Resume Battle
            </button>
        </div>

        <!-- 2. If NO active battle, show Challenges & Player List -->
        <div v-else class="no-active-battle-layout">
            
            <!-- Incoming Challenges Section -->
            <div v-if="isLoadingPendingBattles && !pendingBattles.length" class="loading-placeholder">
                 Loading incoming challenges...
            </div>
             <div v-else-if="pendingBattles.length > 0" class="incoming-challenges subsection">
                <h3>Incoming Challenges ({{ pendingBattles.length }})</h3>
                <ul class="simple-list challenges-list"> 
                     <li v-for="battle in pendingBattles" :key="battle.id" class="list-item-simple challenge-item">
                        <span><strong>{{ battle.player1.username }}</strong> (Lvl {{ battle.player1.level || '1' }})</span>
                        <div class="button-group">
                            <button
                                @click="handleResponse(battle.id, 'accept')"
                                :disabled="respondingBattleId === battle.id"
                                class="button button-accept button-small"
                            >
                                {{ respondingBattleId === battle.id ? '...' : 'Accept' }}
                             </button>
                            <button
                                @click="handleResponse(battle.id, 'decline')"
                                :disabled="respondingBattleId === battle.id"
                                 class="button button-decline button-small"
                            >
                                 {{ respondingBattleId === battle.id ? '...' : 'Decline' }}
                            </button>
                        </div>
                    </li>
                </ul>
            </div>
            <div v-else class="subsection no-items-placeholder">
                No incoming challenges.
            </div>

            <!-- Available Players Section -->
            <div v-if="isLoadingUsers && !availableUsers.length" class="loading-placeholder">
                Loading available players...
            </div>
             <div v-else-if="availableUsers.length > 0" class="available-players subsection">
                <h3>Challenge a Player</h3>
                <ul class="simple-list players-list">
                    <li v-for="player in availableUsers" :key="player.id" class="list-item-simple player-item">
                        <span>{{ player.username }} (Lvl {{ player.level || '1' }})</span>
                        <button
                            @click="handleChallenge(player.id)"
                            :disabled="challengingUserId === player.id"
                            class="button button-secondary button-small challenge-button"
                         >
                            {{ challengingUserId === player.id ? 'Sending...' : 'Challenge' }}
                        </button>
                    </li>
                </ul>
            </div>
             <div v-else class="subsection no-items-placeholder">
                No other players available to challenge.
            </div>

        </div>
        <!-- === END REDESIGNED COMMAND CENTER === -->

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
  .user-panel { grid-area: user; }
  /* .stats-editor-panel removed */
  .moveset-manager-panel { grid-area: moveset; }
  .actions-panel { grid-area: actions; }
}

.panel { /* ... existing styles ... */ }
.user-panel { /* ... existing styles ... */
    position: relative; /* For positioning logout button */
}
.actions-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem; /* Space between title, feedback, and content */
}

.actions-panel h2 {
    margin-bottom: 0; /* Reduce default bottom margin */
}

.action-feedback {
     margin-bottom: 0; /* Remove extra bottom margin */
     order: -1; /* Keep feedback at top */
}

/* Styles for the redesigned sections */
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
    margin-top: 1rem; /* Add some space */
}

.active-battle-display {
    text-align: center;
    background-color: var(--color-primary-soft); /* Highlight active battle */
    border-color: var(--color-primary);
}

.active-battle-display h3 {
    color: var(--color-primary-dark);
    border-bottom: none;
    margin-bottom: 0.5rem;
}

.active-battle-display p {
    margin: 0 0 1rem 0;
    color: var(--color-text);
}

.resume-button {
    width: auto; /* Don't force full width */
    display: inline-block;
}

.no-active-battle-layout {
    display: flex;
    flex-direction: column;
    gap: 1.5rem; /* Space between challenges and players */
}

.incoming-challenges {
    /* Optional: slightly different background/border if desired */
    /* background-color: var(--color-background-soft); */
}

.available-players {
     /* Optional: slightly different background/border if desired */
}

/* List styles */
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
   padding: 0.6rem 0.2rem; /* Adjust padding */
   margin-bottom: 0.3rem;
   border-bottom: 1px solid var(--color-border-hover);
}
.list-item-simple:last-child {
    border-bottom: none;
}

.list-item-simple span strong {
    color: var(--color-heading);
}

.list-item-simple .button-group {
     display: flex;
     gap: 0.5rem;
}

/* NEW Style for fixed logout button */
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
