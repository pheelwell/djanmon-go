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
import TutorialView from '@/views/TutorialView.vue'; // <-- Import Tutorial View
import BattleHubView from '@/views/BattleHubView.vue'; // <-- Import Battle Hub View

// Import components for Tutorial examples
import PlayerInfoCard from '@/components/PlayerInfoCard.vue';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();
const route = useRoute();

const user = computed(() => authStore.currentUser);

const activeSection = ref('profile'); // Default to combined profile/moveset view

let pollingIntervalId = null;
const POLLING_INTERVAL_MS = 5000;

// Ref to control which main section is displayed
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
  return ['profile', 'moveset', 'command', 'tutorial'].includes(activeDisplay.value);
});
const isRouterViewSection = computed(() => {
  return ['leaderboard', 'attack-creator'].includes(activeDisplay.value);
});

onMounted(() => {
  console.log("[HomeView onMounted] Fetching initial data...");
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

function setActiveSection(sectionName) {
  activeSection.value = sectionName;
}

function handleLogout() {
    authStore.logout();
    router.push({ name: 'login' });
}

// --- Handle Navigation from TutorialView ---
function handleTutorialNavigation(sectionName) {
  setActiveSection(sectionName);
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
      <!-- Combined Profile/Moveset -->
      <button 
        id="nav-profile"
        @click="setActiveSection('profile')"
        :class="{ 'active': activeSection === 'profile' }"
        :disabled="!user"
        title="Profile & Moveset"
      >
        👤 Profile
      </button>
      <!-- Attack Creator -->
      <button 
        id="nav-creator"
        @click="setActiveSection('attack-creator')"
        :class="{ 'active': activeSection === 'attack-creator' }"
        title="Attack Creator"
      >
        ✨ Creator
      </button>
      <!-- Battle (Formerly Command Center) -->
      <button 
        id="nav-battle"
        @click="setActiveSection('battle')" 
        :class="{ 'active': activeSection === 'battle' }"
        :disabled="!user"
        title="Battle Hub"
      >
        ⚔️ Battle
      </button>
      <!-- Tutorial -->
      <button 
        id="nav-tutorial"
        @click="setActiveSection('tutorial')" 
        :class="{ 'active': activeSection === 'tutorial' }"
        title="Tutorial"
      >
        ❓ Tutorial
      </button>
      <!-- Leaderboard -->
       <button 
        id="nav-leaderboard"
        @click="setActiveSection('leaderboard')"
        :class="{ 'active': activeSection === 'leaderboard' }"
        title="Leaderboard"
      >
        🏆 Leaderboard
      </button>
    </nav>

    <!-- Conditionally Displayed Sections -->
    <div class="section-content">
      <!-- Combined Profile/Moveset Section -->
      <template v-if="activeSection === 'profile'">
        <div v-if="user" class="profile-moveset-container">
             <UserProfilePanel :user="user" />
             <div class="moveset-manager-panel panel">
                <MovesetManager />
             </div>
        </div>
        <div v-else class="panel">
          <p>Loading user profile...</p>
        </div>
      </template>

      <!-- Attack Creator View -->
      <AttackCreatorView v-if="activeSection === 'attack-creator'" class="panel" />

      <!-- Battle Panel (Now uses BattleHubView component) -->
      <BattleHubView v-if="activeSection === 'battle' && user" />

      <!-- Tutorial Section (Now uses TutorialView component) -->
      <TutorialView 
        v-if="activeSection === 'tutorial'" 
        @navigate-section="handleTutorialNavigation"
      />

      <!-- Leaderboard View -->
      <LeaderboardView v-if="activeSection === 'leaderboard'" class="panel" />

    </div>
  </main>
</template>

<style scoped>
/* Apply base font */
.home-view {
  position: relative; /* REMOVE THIS if not needed elsewhere */
  display: flex; 
  flex-direction: column;
  gap: 1rem; /* Keep gap, use theme var if defined or pixel value */
  padding: 10px; /* Use pixel padding */
  max-width: 900px; 
  margin: 10px auto;
  font-family: var(--font-primary);
}

/* Style for the section navigation */
.section-nav {
  display: flex;
  justify-content: center;
  gap: 8px; 
  margin-bottom: 10px; 
  flex-wrap: wrap; 
  border-bottom: var(--border-width) solid var(--color-border);
  padding-bottom: 10px; 
}

.section-nav button {
  /* Inherit .btn styles from main.css? Or define here? */
  /* Assuming inheritance or global .btn style matching theme */
  background-color: transparent;
  border: 2px solid transparent; /* Border for spacing, transparent */
  color: var(--color-text);
  opacity: 0.7; 
  transition: opacity 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  padding: 4px 10px; 
  font-size: 1.1em; /* Increased font size */
  text-transform: uppercase;
  box-shadow: none; /* Remove base btn shadow */
  /* Add display flex for better alignment */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px; /* Add gap between emoji and text */
}

.section-nav button:hover:not(:disabled) {
  opacity: 1;
  color: var(--color-accent-secondary);
  background-color: transparent; /* No bg change on hover */
}

.section-nav button.active {
  opacity: 1; 
  color: var(--color-accent-secondary);
  border-bottom-color: var(--color-accent-secondary); /* Underline effect */
}

.section-nav button:disabled {
   opacity: 0.4;
   cursor: not-allowed;
}

/* Container for the active section */
.section-content {
  flex-grow: 1;
  & > .panel {
     margin-bottom: 10px; 
  }
}

/* Retro Panel Style Override (Applies to panels created directly in HomeView or if needed for children) */
.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding);
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
    border-radius: 0;
    margin-bottom: var(--element-gap); /* Consistent spacing */
}

.actions-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem; /* Keep gap */
}

.actions-panel h2 { /* Assuming titles exist in children */
    /* Delegate title styling to child components or apply .panel-title style if needed */
    margin-top: 0;
    margin-bottom: 0;
}

.action-feedback {
     /* Feedback messages styling */
     margin-bottom: 0;
     order: -1;
}

.error-message, .success-message { 
    padding: 8px 10px;
    border-radius: 0;
    font-weight: normal;
    text-align: center;
    margin-bottom: 10px; 
    border: 1px solid;
    font-size: 0.9em;
}
.error-message {
  background-color: rgba(233, 69, 96, 0.1); /* Use theme colors */
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.success-message {
  background-color: rgba(53, 208, 104, 0.1);
  color: var(--color-hp-high);
  border-color: var(--color-hp-high);
}

/* Generic Loading Placeholder style */
.loading-placeholder {
    padding: 20px;
    text-align: center;
    color: var(--color-log-system);
    font-style: italic;
    border-radius: 0;
    border: 1px dashed var(--color-border);
    background-color: var(--color-bg); /* Match inner bg */
    text-transform: uppercase;
}

.no-active-battle-layout {
    display: flex;
    flex-direction: column;
    gap: 1rem; 
}

/* --- Button Styles (Ensure consistency with global styles) --- */
/* Assuming .button class exists globally and matches theme */

/* Danger button style override if needed */
.button-danger {
  background-color: var(--color-accent); /* Use theme accent */
  color: var(--color-text); /* Ensure contrast */
  border-color: var(--color-border);
}

.button-danger:hover:not(:disabled) {
  background-color: #c0392b; /* Darker red */
  border-color: var(--color-border);
  color: var(--color-text);
}

/* Keep fixed logout button style */
.logout-button-fixed {
    position: fixed;
    top: 10px; /* Adjust spacing */
    right: 10px; 
    z-index: 1000; 
    /* Apply btn styles directly or use class */
    font-family: var(--font-primary);
    font-size: 0.8em;
    padding: 6px 10px;
    border: var(--border-width) solid var(--color-border);
    background-color: var(--color-accent);
    color: var(--color-text);
    cursor: pointer;
    text-align: center;
    transition: background-color 0.2s ease, color 0.2s ease, transform 0.1s ease;
    box-shadow: 2px 2px 0px var(--color-border);
    text-transform: uppercase;
    border-radius: 0;
}
.logout-button-fixed:hover {
    background-color: #c0392b; /* Darker red */
}
.logout-button-fixed:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px var(--color-border);
}

/* Adjust logout button padding on very small screens */
@media (max-width: 480px) {
  .logout-button-fixed {
    top: 5px;
    right: 5px;
    padding: 4px 8px;
  }
}

/* Ensure child components inherit font */
.moveset-manager-panel,
.actions-panel,
.leaderboard-view,
.attack-creator-view {
    font-family: var(--font-primary);
}

/* Style for the combined profile/moveset container */
.profile-moveset-container {
    display: flex;
    flex-direction: column;
    gap: 1rem; /* Space between profile and moveset panels */
}

/* --- Responsive Display Toggle --- */
/* ... rest of styles ... */

</style>
