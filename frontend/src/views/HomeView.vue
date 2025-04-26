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

// --- NEW: Import components for Tutorial ---
import PlayerInfoCard from '@/components/PlayerInfoCard.vue';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
// --- END Tutorial Imports ---

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
  return ['profile', 'moveset', 'command', 'tutorial'].includes(activeDisplay.value);
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

// --- NEW: Sample Data for Tutorial Components ---
const tutorialSamplePlayer = ref({
  id: 999,
  username: 'Tutorial Dummy',
  hp: 120, // Base Max HP
  attack: 60,
  defense: 55,
  speed: 70,
  // No current HP needed here, PlayerInfoCard uses maxHp
});

const tutorialSampleStages = ref({
  attack: 1,
  defense: -1,
  speed: 0,
});

const tutorialSampleStatuses = ref({
  'Inspired': 2, // Example status with duration
  'Shielded': true,
  'Chilled': 1
});

const tutorialSampleAttack = ref({
  id: 1001,
  name: 'Tutorial Zap',
  description: 'Deals moderate electric damage. May Paralyze the target (lowers Speed by 1 stage).',
  emoji: '⚡',
  momentum_cost: 30,
  previewCost: { min: 25, max: 35 } // Add potential cost range for preview
});

const tutorialSampleStatusAttack = ref({
  id: 1002,
  name: 'Toxic Spikes',
  description: 'Applies Poisoned status (3 turns) to the target. Deals small damage.',
  emoji: '☠️',
  momentum_cost: 25,
  previewCost: { min: 20, max: 30 } // Add potential cost range for preview
});

const tutorialSampleMomentum = ref(75);
// Refs for the *currently previewed* cost range
const tutorialPreviewCostMin = ref(null); 
const tutorialPreviewCostMax = ref(null);
const isTutorialPreviewActive = computed(() => 
    tutorialPreviewCostMin.value !== null && tutorialPreviewCostMax.value !== null
);
// --- END Sample Data ---

// --- NEW: Tutorial Interaction Handlers ---
function previewTutorialAttackCost(attack) {
    if (attack?.previewCost) {
        tutorialPreviewCostMin.value = attack.previewCost.min;
        tutorialPreviewCostMax.value = attack.previewCost.max;
    }
}

function clearTutorialPreview() {
    tutorialPreviewCostMin.value = null;
    tutorialPreviewCostMax.value = null;
}
// --- END Tutorial Interaction Handlers ---

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
  if (['profile', 'moveset', 'command', 'tutorial'].includes(section)) {
    activeSection.value = section;
    // Navigate to root path if not already there
    // if (route.path !== '/') { 
    //   router.push('/'); 
    // }
  } else if (section === 'leaderboard') {
    activeSection.value = 'leaderboard';
    router.push('/leaderboard');
  } else if (section === 'attack-creator') {
    activeSection.value = 'attack-creator';
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
        @click="setActiveSection('tutorial')" 
        :class="{ 'active': activeSection === 'tutorial' }"
      >
        Tutorial
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
        <UserProfilePanel :key="'profile-panel'" v-if="user" :user="user" />
        <div :key="'profile-loading'" v-else class="panel">
          <p>Loading user profile...</p>
        </div>
      </template>

      <!-- Integrated Moveset Manager -->
      <div :key="'moveset-panel'" v-if="activeSection === 'moveset' && user" class="moveset-manager-panel panel">
        <MovesetManager />
      </div>

      <!-- Actions Panel (Command Center) -->
      <div :key="'command-panel'" v-if="activeSection === 'command' && user" class="actions-panel panel">
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

      <!-- UPDATED: Tutorial Section -->
      <div :key="'tutorial-panel'" v-if="activeSection === 'tutorial'" class="tutorial-panel panel">
        <h2>Game Tutorial</h2>

        <section class="tutorial-section">
          <h3>Core Stats & Statuses</h3>
          <p>Your battle status is shown on cards like this:</p>
             <PlayerInfoCard
                :player="tutorialSamplePlayer"
                :currentHp="85" 
                :maxHp="tutorialSamplePlayer.hp"
                :statStages="tutorialSampleStages"
                :customStatuses="tutorialSampleStatuses"
                playerType="user" 
                :isCurrentUser="true"
                class="tutorial-player-card"
             />
          <p>Key elements include:</p>
          <ul>
            <li><strong>Stat Badges:</strong> Temporary buffs/debuffs appear like 
                <span class="tutorial-stat-badge stat-up">ATTACK +1</span> or 
                <span class="tutorial-stat-badge stat-down">DEFENSE -1</span>. 
                These modify your base Attack, Defense, or Speed.
            </li>
            <li><strong>Status Badges:</strong> Special conditions like 
                <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(200, 70%, 50%)', color: '#fff', borderColor: 'hsl(200, 70%, 35%)'}">INSPIRED (2)</span> or 
                <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(120, 70%, 50%)', color: '#fff', borderColor: 'hsl(120, 70%, 35%)'}">SHIELDED</span> 
                .
            </li>
          </ul>
        </section>

        <section class="tutorial-section">
          <h3>Momentum & Turns</h3>
          <p>The Momentum Bar determines who acts and the energy needed.</p>
          <div class="tutorial-component-wrapper tutorial-momentum-wrapper">
              <div class="momentum-label">MOMENTUM</div>
              <div class="momentum-meter tutorial-meter">
                 <div 
                    class="momentum-fill user-momentum fill-left" 
                    :style="{ width: tutorialSampleMomentum + '%' }"
                 >
                    <!-- Number positioned absolutely within the fill -->
                    <span class="momentum-value">{{ tutorialSampleMomentum }}</span> 
                 </div>
                 <!-- Cost Preview Block -->
                 <div 
                    :class="['momentum-cost-preview', 'tutorial-preview', { 'active-preview': isTutorialPreviewActive }]" 
                    :style="{
                      left: Math.max(0, tutorialSampleMomentum - (tutorialPreviewCostMax ?? 0)) + '%',
                      width: Math.max(0, (tutorialPreviewCostMax ?? 0) - (tutorialPreviewCostMin ?? 0)) + '%'
                    }"
                 ></div>
              </div>
              <p class="tutorial-explanation">
                Current Momentum: <strong>{{ tutorialSampleMomentum }}</strong>. Hover over an attack below to see its potential cost.
                 <span v-if="isTutorialPreviewActive">
                   The attack could cost between <strong>{{ tutorialPreviewCostMin }}</strong> and <strong>{{ tutorialPreviewCostMax }}</strong> Momentum.
                 </span>
              </p>
               <!-- Attack Cards for Preview -->
              <div class="tutorial-attack-preview-area">
                  <div 
                    class="tutorial-attack-card-wrapper"
                    @mouseover="previewTutorialAttackCost(tutorialSampleAttack)"
                    @mouseleave="clearTutorialPreview"
                  >
                    <AttackCardDisplay 
                        :attack="tutorialSampleAttack" 
                        class="tutorial-attack-card small"
                    />
                  </div>
                   <div 
                    class="tutorial-attack-card-wrapper"
                    @mouseover="previewTutorialAttackCost(tutorialSampleStatusAttack)"
                    @mouseleave="clearTutorialPreview"
                  >
                    <AttackCardDisplay 
                        :attack="tutorialSampleStatusAttack" 
                        class="tutorial-attack-card small"
                    />
                  </div>
              </div>
              <p class="tutorial-explanation bottom">
                 <strong>Success:</strong> If you have enough Momentum to cover the attack's actual cost, you spend the Momentum and immediately get another turn!
                 <br>
                 <strong>Failure:</strong> If you don't have enough Momentum for the attack's actual cost, your Momentum drops to 0, the turn passes to the opponent, and they gain Momentum equal to the amount you couldn't pay (the "overflow").
              </p>
          </div>
        </section>

        <section class="tutorial-section">
          <h3>Speed & Momentum Cost</h3>
          <p>Your <strong>Speed</strong> stat directly affects how much Momentum your attacks actually cost.</p>
          <ul>
              <li>Every attack has a base Momentum Cost (⚡).</li>
              <li><span class="tutorial-stat-badge stat-up">Speed +X</span> makes the actual cost <em>lower</em> than the base cost (down to a minimum multiplier, e.g., 0.5x).</li>
              <li><span class="tutorial-stat-badge stat-down">Speed -X</span> makes the actual cost <em>higher</em> than the base cost (up to a maximum multiplier, e.g., 1.5x).</li>
              <li>A baseline speed (e.g., 100) results in a cost multiplier of 1.0.</li>
              <li>There's also a small random variance (+/- 15%) applied to the final calculated cost, which is why you see a cost *range* previewed.</li>
          </ul>
          <p>Faster players can use attacks more frequently before needing to build Momentum!</p>
        </section>

        <section class="tutorial-section">
          <h3>Damage Calculation</h3>
          <p>The damage an attack deals is primarily based on three things:</p>
           <ul>
              <li>The inherent <strong>Power</strong> of the attack itself.</li>
              <li>The attacker's current <strong>Attack</strong> stat (including stage modifiers). Higher Attack means more damage.</li>
              <li>The target's current <strong>Defense</strong> stat (including stage modifiers). Higher Defense means less damage taken.</li>
           </ul>
           <p>Think of it like this: Damage is roughly proportional to <span class="inline-code">Attack Power * (Your Attack / Opponent's Defense)</span>.</p>
           <p>Raising your Attack or lowering the opponent's Defense are key ways to increase damage output.</p>
        </section>

        <section class="tutorial-section">
          <h3>Custom Statuses Explained</h3>
          <p>Attacks can apply Custom Statuses, shown as badges:</p>
          <div class="tutorial-component-wrapper tutorial-status-examples">
               <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(200, 70%, 50%)', color: '#fff', borderColor: 'hsl(200, 70%, 35%)'}">INSPIRED (2)</span> 
               <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(120, 70%, 50%)', color: '#fff', borderColor: 'hsl(120, 70%, 35%)'}">SHIELDED</span> 
               <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(50, 70%, 50%)', color: '#111', borderColor: 'hsl(50, 70%, 35%)'}">CONFUSED</span> 
               <span class="tutorial-custom-status-badge" :style="{backgroundColor: 'hsl(0, 70%, 50%)', color: '#fff', borderColor: 'hsl(0, 70%, 35%)'}">BLEEDING (1)</span> 
          </div>
          <ul>
            <li>These statuses usually have effects handled by other scripts (like damage over time) or enable attack combos.</li>
            <li>They often have a duration (number in parentheses) or might be permanent until removed.</li>
            <li>Look for attacks that apply statuses and others that interact with them!</li>
          </ul>
        </section>

        <section class="tutorial-section">
          <h3>Attack Creator & Synergy</h3>
          <p>Generate new, unique attacks in the <strong>Attack Creator</strong> tab!</p>
          <ul>
            <li>Provide a theme (e.g., "Fire and Ice", "Healing Aura", "Momentum Drain").</li>
            <li>Optionally select favorite attacks you own to guide the AI towards synergistic mechanics based on their code.</li>
            <li>Build a powerful Moveset where your attacks complement each other!</li>
          </ul>
        </section>

      </div>
      <!-- END Tutorial Section -->

      <!-- Leaderboard View -->
      <LeaderboardView :key="'leaderboard-view'" v-if="activeSection === 'leaderboard'" class="panel" />

      <!-- Attack Creator View -->
      <AttackCreatorView :key="'attack-creator-view'" v-if="activeSection === 'attack-creator'" class="panel" />

    </div>
  </main>
</template>

<style scoped>
/* Apply base font */
.home-view {
  display: flex; 
  flex-direction: column;
  gap: 1rem; /* Keep gap, use theme var if defined or pixel value */
  padding: 10px; /* Use pixel padding */
  max-width: 900px; 
  margin: 10px auto;
  font-family: var(--font-primary);
}

/* Remove old grid media query if not needed */
/* @media (min-width: 1200px) { ... } */

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
  padding: 4px 8px; /* Adjust padding */
  font-size: 0.9em; /* Adjust size */
  text-transform: uppercase;
  box-shadow: none; /* Remove base btn shadow */
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

/* Styles for Tutorial Panel */
.tutorial-panel {
  text-align: left;
  line-height: 1.5;
  font-family: 'Roboto', sans-serif; /* More readable font */
  color: var(--color-text);
}

.tutorial-panel h2 {
  /* Use panel-title styling */
  font-family: var(--font-primary); /* Keep title font */
  font-size: 1.3em; 
  color: var(--color-text);
  margin: -15px -15px 15px -15px; 
  padding: 8px 15px;
  text-align: center;
  border-bottom: var(--border-width) solid var(--color-border);
  text-transform: uppercase;
  background-color: var(--color-border); 
  font-weight: normal;
  box-shadow: inset 0 0 0 1px var(--color-panel-bg);
}

.tutorial-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px dashed var(--color-border);
}

.tutorial-section:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
}

.tutorial-section h3 {
  font-family: var(--font-primary);
  font-size: 1.1em;
  color: var(--color-accent-secondary);
  margin-bottom: 1rem; /* Increased space */
  text-transform: uppercase;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 4px;
}

.tutorial-section p {
  margin-bottom: 0.75rem;
  font-size: 0.95em;
}

.tutorial-section ul {
  list-style: disc;
  margin-left: 20px;
  padding-left: 10px;
  font-size: 0.9em;
}

.tutorial-section li {
  margin-bottom: 0.5rem;
}

.tutorial-section strong {
  color: var(--color-accent-secondary);
  font-weight: normal;
}

/* Wrapper for embedded components */
.tutorial-component-wrapper {
  margin: 1rem 0;
  padding: 10px;
  background-color: rgba(0,0,0,0.1);
  border: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

.tutorial-player-card {
  max-width: 350px; /* Allow slightly larger player card */
  width: 100%;
  margin: 0 auto; 
  transform: scale(0.95); /* Less aggressive scaling */
  transform-origin: center top;
}

.tutorial-explanation {
  font-size: 0.85em !important;
  font-style: italic;
  margin-top: 10px !important;
  text-align: center;
  color: var(--color-log-system);
  max-width: 90%; /* Prevent text getting too wide */
}
.tutorial-explanation.bottom {
    margin-top: 15px !important;
}

/* --- Stat Badge Replication --- */
.tutorial-stat-badge {
    display: inline-block;
    padding: 1px 3px; /* Slightly adjust padding for arrows */
    font-size: 0.8em;
    font-weight: normal;
    border-radius: 0;
    border: 1px solid;
    line-height: 1.1;
    text-transform: uppercase;
    font-family: var(--font-primary);
    margin: 0 2px;
    vertical-align: middle; /* Align arrows better with text */
}
.tutorial-stat-badge.stat-up {
    color: var(--color-stat-up);
    border-color: var(--color-stat-up);
    background-color: rgba(83, 189, 235, 0.1); 
}
.tutorial-stat-badge.stat-down {
    color: var(--color-stat-down);
    border-color: var(--color-stat-down);
    background-color: rgba(233, 69, 96, 0.1);
}

/* --- Custom Status Badge Replication --- */
.tutorial-custom-status-badge {
    display: inline-block;
    padding: 1px 5px;
    font-size: 0.8em;
    font-weight: normal;
    border-radius: 0;
    border: 1px solid;
    line-height: 1.1;
    text-transform: uppercase;
    font-family: var(--font-primary);
    margin: 2px; /* Add margin for wrapping */
    /* Colors applied via inline :style in template */
}
.tutorial-status-examples {
    flex-direction: row; /* Allow badges to wrap */
    flex-wrap: wrap;
    gap: 5px;
}

/* --- Momentum Bar Replication --- */
.tutorial-momentum-wrapper {
    width: 100%;
    max-width: 600px;
    padding: 15px;
}
.momentum-label { /* Shared styles ok */
  font-family: var(--font-primary);
  font-size: 1em;
  color: var(--color-text);
  text-transform: uppercase;
  margin-bottom: 8px;
}
.tutorial-meter { 
  height: 25px; 
  background-color: #333;
  border: 1px solid var(--color-border);
  position: relative; /* Ensure relative positioning */
  overflow: hidden; 
  padding: 1px; 
  box-shadow: inset 1px 1px 0px rgba(0,0,0,0.5); 
  width: 300px;
  margin-left: auto; /* Center the fixed-width bar */
  margin-right: auto;
}
.momentum-fill { 
  position: absolute; 
  top: 1px;
  bottom: 1px;
  height: calc(100% - 2px); 
  transition: width 0.5s ease-in-out, left 0.3s ease, right 0.3s ease;
  min-width: 0; 
  overflow: hidden; 
}
.momentum-fill.fill-left { left: 1px; right: auto; }
.momentum-fill.user-momentum { background: var(--color-momentum-user); }

.momentum-value { 
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.9em; 
  font-weight: normal; 
  color: black; 
  z-index: 10; 
  white-space: nowrap;
}

.tutorial-preview { 
  position: absolute; 
  top: 1px;
  bottom: 1px;
  height: calc(100% - 2px); /* Explicit height */
  background-color: rgba(255, 255, 0, 0.4);
  z-index: 5;
  transition: left 0.2s ease-out, width 0.2s ease-out, opacity 0.2s ease-out;
  pointer-events: none; 
  border-left: 1px solid rgba(255, 255, 0, 0.7);
  border-right: 1px solid rgba(255, 255, 0, 0.7);
  box-sizing: border-box;
  opacity: 0;
}

.momentum-cost-preview.tutorial-preview.active-preview {
    opacity: 1;
}

/* Area for Attack Cards below Momentum */
.tutorial-attack-preview-area {
    display: flex;
    justify-content: center;
    gap: 10px; /* Reduced gap slightly */
    margin-top: 15px;
    flex-wrap: nowrap; /* Prevent wrapping */
    width: 100%; /* Take full width */
    max-width: calc(150px * 2 + 10px); /* Approximate max width based on scaled cards + gap */
    margin-left: auto;
    margin-right: auto;
}
.tutorial-attack-card-wrapper {
    cursor: pointer;
    flex-shrink: 0; /* Prevent shrinking */
    /* Ensure wrappers don't cause overflow if flex-basis is needed */
}
.tutorial-attack-card.small {
    transform: scale(0.85);
    transform-origin: center center;
    min-width: 150px; /* Ensure minimum size */
    width: 150px; /* Set explicit base width before scaling */
    height: auto; /* Maintain aspect ratio */
}

/* Style for inline code snippets */
.inline-code {
  font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
  background-color: rgba(255, 255, 255, 0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.85em;
  color: var(--color-accent-secondary);
}

</style>
