<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router'; // Import useRoute, watch
import { useAuthStore } from '@/stores/auth';
import { useGameStore } from '@/stores/game'; // Import the game store
import MovesetManager from '@/components/MovesetManager.vue';
// import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // Likely unused here now
// import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue'; // Now inside UserProfilePanel
import UserProfilePanel from '@/components/UserProfilePanel.vue'; // <-- Import
import ActiveBattleDisplay from '@/components/ActiveBattleDisplay.vue'; // <-- Import
import IncomingChallengesList from '@/components/IncomingChallengesList.vue'; // <-- Import
import AvailablePlayersList from '@/components/AvailablePlayersList.vue'; // <-- Import
import LeaderboardView from '@/views/LeaderboardView.vue'; // <-- Import Leaderboard
import AttackCreatorView from '@/views/AttackCreatorView.vue'; // <-- Import Attack Creator

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();
const route = useRoute();

const user = computed(() => authStore.currentUser);

const availableUsers = computed(() => gameStore.users);
const pendingBattles = computed(() => gameStore.pendingBattles);
const activeBattle = computed(() => gameStore.activeBattle);
const isLoadingUsers = computed(() => gameStore.isLoadingUsers);
const isLoadingPendingBattles = computed(() => gameStore.isLoadingPendingBattles);
const isLoadingActiveBattle = computed(() => gameStore.isLoadingActiveBattle);
const actionError = computed(() => gameStore.actionError);
const actionSuccessMessage = computed(() => gameStore.actionSuccessMessage);

const activeSection = ref('command'); // State for active tab, default to command center

const challengingUserId = ref(null);
const respondingBattleId = ref(null);
let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 1000;

// Renamed ref, handles both internal sections and routes
const activeDisplay = ref('command'); // Default view

// Map route paths to activeDisplay values
const routeToDisplayMap = {
  '/': 'command', // Or 'profile' if preferred as default for root
  '/leaderboard': 'leaderboard',
  '/attack-creator': 'attack-creator'
};

// Function to set the active display based on route
function updateActiveDisplayFromRoute() {
  const path = route.path;
  activeDisplay.value = routeToDisplayMap[path] || 'command'; // Fallback
}

// Watch for route changes to update the active display
watch(route, updateActiveDisplayFromRoute);

// Helper computed properties
const isInternalSection = computed(() => {
  return ['profile', 'moveset', 'command'].includes(activeDisplay.value);
});
const isRouterViewSection = computed(() => {
  return ['leaderboard', 'attack-creator'].includes(activeDisplay.value);
});

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

  updateActiveDisplayFromRoute(); // Set initial display based on current route

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

// --- Action Handlers (Modified for Navigation) ---

function navigateTo(section) {
  if (['profile', 'moveset', 'command'].includes(section)) {
    activeDisplay.value = section;
    // Navigate to root path if not already there
    if (route.path !== '/') {
      router.push('/');
    }
  } else if (section === 'leaderboard') {
    activeDisplay.value = 'leaderboard';
    router.push('/leaderboard');
  } else if (section === 'attack-creator') {
    activeDisplay.value = 'attack-creator';
    router.push('/attack-creator');
  }
}

function setActiveSection(sectionName) {
  activeSection.value = sectionName;
}

async function handleChallenge(challengeData) {
    const { opponentId, fightAsBot } = challengeData;
    challengingUserId.value = opponentId;
    const result = await gameStore.challengeUser(opponentId, fightAsBot);
    challengingUserId.value = null;

    if (result && result.battleStarted && result.battle) {
      goToBattle(result.battle.id);
    }
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
    <!-- Section Navigation -->
    <nav class="section-nav">
      <button 
        @click="setActiveSection('profile')"
        :class="{ 'active': activeSection === 'profile' }"
        :disabled="!user"
      >
        Profile
      </button>
      <button 
        @click="setActiveSection('moveset')"
        :class="{ 'active': activeSection === 'moveset' }"
        :disabled="!user"
      >
        Moveset
      </button>
      <button 
        @click="setActiveSection('command')"
        :class="{ 'active': activeSection === 'command' }"
        :disabled="!user"
      >
        Command Center
      </button>
       <button 
        @click="setActiveSection('leaderboard')"
        :class="{ 'active': activeSection === 'leaderboard' }"
      >
        Leaderboard
      </button>
       <button 
        @click="setActiveSection('attack-creator')"
        :class="{ 'active': activeSection === 'attack-creator' }"
      >
        Attack Creator
      </button>
    </nav>

    <!-- Conditionally Displayed Sections -->
    <div class="section-content">
      <!-- UserProfilePanel or loading state -->
      <template v-if="activeSection === 'profile'">
        <UserProfilePanel v-if="user" :user="user" />
        <div v-else class="panel">
          <p>Loading user profile...</p>
        </div>
      </template>

      <!-- Integrated Moveset Manager -->
      <div v-if="activeSection === 'moveset' && user" class="moveset-manager-panel panel">
        <MovesetManager />
      </div>

      <!-- Actions Panel (Command Center) -->
      <div v-if="activeSection === 'command' && user" class="actions-panel panel">
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

      <!-- Leaderboard View -->
      <LeaderboardView v-if="activeSection === 'leaderboard'" class="panel" />

      <!-- Attack Creator View -->
      <AttackCreatorView v-if="activeSection === 'attack-creator'" class="panel" />

    </div>
  </main>
</template>

<style scoped>
/* Remove grid layout, use flex column layout */
.home-view {
  display: flex; 
  flex-direction: column;
  gap: 1.5rem; /* Space between nav and content */
  padding: 1rem; /* Adjusted padding */
  max-width: 900px; /* Adjust max-width as needed */
  margin: 1rem auto;
}

/* Remove old grid media query */
@media (min-width: 1200px) {
  .home-view {
    max-width: 1000px; /* Maybe slightly wider on large screens */
  }
}

/* Style for the section navigation (similar to App nav) */
.section-nav {
  display: flex;
  justify-content: center;
  gap: 0.5rem; /* Keep some gap */
  margin-bottom: 1rem; /* Space below nav */
  flex-wrap: wrap; /* Allow buttons to wrap on small screens */
  border-bottom: 1px solid var(--color-border); /* Add bottom border */
  padding-bottom: 1rem; /* Add padding below buttons */
}

.section-nav button {
  padding: 0 1rem; /* Match horizontal padding */
  background-color: transparent; /* No background */
  border: none; /* No border */
  cursor: pointer;
  font-size: 1rem; /* Match font size */
  color: var(--color-text); /* Use default text color */
  opacity: 0.7; /* Slightly faded non-active */
  transition: opacity 0.2s ease;
  font-weight: normal; /* Reset font weight */
}

.section-nav button:hover:not(:disabled) {
  opacity: 1; /* Full opacity on hover */
  background-color: transparent; /* Ensure no background on hover */
}

.section-nav button.active {
  font-weight: bold; /* Bold active link */
  color: var(--color-text); /* Ensure active uses main text color */
  opacity: 1; /* Full opacity */
}

.section-nav button:disabled {
   opacity: 0.4; /* Dim disabled buttons more */
   cursor: not-allowed;
}

/* Container for the active section */
.section-content {
  /* Ensure it can grow */
  flex-grow: 1;
  /* Give children panels consistent styling if they don't have it */
  & > .panel { /* Target direct children with .panel class */
     margin-bottom: 1rem; /* Add some space below if multiple panels could show (though v-if prevents this now) */
  }
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

/* Base button styles (ensure these exist or copy from other components if needed) */
.button {
    display: inline-block;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    text-align: center;
    font-weight: 600;
    transition: background-color 0.2s ease, opacity 0.2s ease;
    line-height: 1.2;
}
.button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* Danger button style */
.button-danger {
  background-color: var(--vt-c-red); /* Use CSS variable for red */
  color: white;
  border: 1px solid var(--vt-c-red-dark); /* Optional darker border */
}

.button-danger:hover:not(:disabled) {
  background-color: var(--vt-c-red-dark); /* Darken on hover */
  border-color: var(--vt-c-red-darker); /* Even darker border on hover */
}

/* Keep fixed logout button style */
.logout-button-fixed {
    position: fixed;
    top: 1.5rem; /* Adjust spacing from top */
    right: 1.5rem; /* Adjust spacing from right */
    z-index: 1000; /* Ensure it stays on top */
}

/* Adjust logout button padding on very small screens */
@media (max-width: 480px) {
  .logout-button-fixed {
    top: 0.8rem;
    right: 0.8rem;
    padding: 0.6rem 1rem; /* Slightly smaller button */
  }
}

</style>
