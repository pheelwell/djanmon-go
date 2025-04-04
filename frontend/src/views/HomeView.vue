<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router'; // Import useRouter
import { useAuthStore } from '@/stores/auth';
import { useGameStore } from '@/stores/game'; // Import the game store
import MovesetManager from '@/components/MovesetManager.vue'; // Import the new component
import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // Import the new component

const authStore = useAuthStore();
const gameStore = useGameStore(); // Initialize the game store
const router = useRouter(); // Initialize router

// Get user data reactively from the auth store
const user = computed(() => authStore.currentUser);

// Get game data reactively from the game store
const availableUsers = computed(() => gameStore.users);
const pendingBattles = computed(() => gameStore.pendingBattles);
const activeBattle = computed(() => gameStore.activeBattle); // For later use
const isLoadingUsers = computed(() => gameStore.isLoadingUsers);
const isLoadingPendingBattles = computed(() => gameStore.isLoadingPendingBattles);
const isLoadingActiveBattle = computed(() => gameStore.isLoadingActiveBattle); // Get loading state
const actionError = computed(() => gameStore.actionError);
const actionSuccessMessage = computed(() => gameStore.actionSuccessMessage);

// State for managing button loading states
const challengingUserId = ref(null);
const respondingBattleId = ref(null);
let pollingIntervalId = null; // Variable to store the interval ID
const POLLING_INTERVAL_MS = 1000; // Poll every 1 second now

const showMovesetManager = ref(false); // State to toggle manager visibility

// Computed property to find opponent
const opponent = computed(() => {
    if (!activeBattle.value || !user.value) return null;
    return activeBattle.value.player1.id === user.value.id 
        ? activeBattle.value.player2 
        : activeBattle.value.player1;
});

// Fetch initial data when the component mounts
onMounted(() => {
  gameStore.fetchUsers(); // Initial fetch (will show loading)
  gameStore.fetchPendingBattles(); // Initial fetch (will show loading)
  gameStore.fetchActiveBattle(); // Initial fetch (will show loading)
  gameStore.clearMessages(); 

  // Start polling
  pollingIntervalId = setInterval(() => {
      console.log('Polling for updates...'); 
      // Pass true to indicate polling, preventing loading state flicker and unnecessary updates
      gameStore.fetchUsers(true); 
      gameStore.fetchPendingBattles(true);
      gameStore.fetchActiveBattle(true); 
  }, POLLING_INTERVAL_MS);
});

onUnmounted(() => {
  // Clear the interval when the component is unmounted
  if (pollingIntervalId) {
    clearInterval(pollingIntervalId);
    console.log('Polling stopped.'); // Optional: for debugging
  }
});

// --- Action Handlers ---

async function handleChallenge(opponentId) {
    challengingUserId.value = opponentId; // Set loading state for this button
    await gameStore.challengeUser(opponentId);
    // Optionally trigger an immediate fetch after challenging to update lists faster
    // await gameStore.fetchUsers(); 
    challengingUserId.value = null; // Clear loading state
    // Success/error messages are handled via computed properties
}

async function handleResponse(battleId, responseAction) {
    respondingBattleId.value = battleId; // Set loading state
    const result = await gameStore.respondToBattle(battleId, responseAction);
    respondingBattleId.value = null; // Clear loading state
     // Success/error messages are handled via computed properties
    // If accepted, navigate to the battle view
    if (result.accepted && result.battle) {
        goToBattle(result.battle.id);
    }
}

function goToBattle(battleId) {
    router.push({ name: 'battle', params: { id: battleId } });
}

function handleLogout() {
    authStore.logout();
    router.push({ name: 'login' }); // Redirect to login page
}

</script>

<template>
  <main class="home-view">
    <div v-if="user" class="user-panel panel">
      <h2>{{ user.username }}'s Quarters</h2>

      <!-- Updated Stats Section -->
      <div class="stats-container-reimagined">
          <div class="stat-level">
              <span class="label">LVL</span>
              <span class="value">{{ user.level }}</span>
          </div>
          <div class="stats-right-column">
              <div class="stat-hp">
                  <span class="value">{{ user.hp }} HP</span>
                  <!-- Optional: Max HP display: {{ user.currentHp || user.hp }} / {{ user.hp }} HP -->
              </div>
              <div class="stat-bars-container">
                  <div class="stat-bar stat-bar-atk" :style="{ '--stat-value-percent': (user.attack / 50) * 100 + '%' }" title="Attack">
                      <span class="label">ATK</span>
                      <div class="bar"><div class="fill"></div></div>
                  </div>
                   <div class="stat-bar stat-bar-def" :style="{ '--stat-value-percent': (user.defense / 50) * 100 + '%' }" title="Defense">
                      <span class="label">DEF</span>
                      <div class="bar"><div class="fill"></div></div>
                  </div>
                   <div class="stat-bar stat-bar-spd" :style="{ '--stat-value-percent': (user.speed / 50) * 100 + '%' }" title="Speed">
                      <span class="label">SPD</span>
                       <div class="bar"><div class="fill"></div></div>
                  </div>
              </div>
          </div>
      </div>

      <!-- Updated Known Moves Section -->
      <div class="attacks-container">
        <h3>Selected Moveset (Max 6)</h3>
        <ul v-if="user.selected_attacks && user.selected_attacks.length" class="attacks-grid">
          <li v-for="attack in user.selected_attacks" :key="attack.id" class="attack-card">
            <AttackCardDisplay :attack="attack" />
          </li>
          <li v-for="n in (6 - user.selected_attacks.length)" :key="'empty-'+n" class="attack-card empty-slot">
            <span>Empty Slot</span>
          </li>
        </ul>
        <p v-else class="no-items-message">No moves selected yet.</p>
      </div>
      
      <!-- Button Controls -->
      <div class="user-controls">
          <button @click="showMovesetManager = true" class="button button-secondary">
              Manage Moveset
          </button>
          <button @click="handleLogout" class="button button-danger">
              Logout
          </button>
      </div>
    </div>
    <div v-else class="panel">
      <p>Loading user profile...</p>
    </div>

    <!-- Actions Panel -->
    <div class="actions-panel panel">
        <h2>Command Center</h2>

        <!-- Action Feedback -->
        <div class="action-feedback">
            <p v-if="actionError" class="error-message">⚠️ {{ actionError }}</p>
            <p v-if="actionSuccessMessage" class="success-message">✅ {{ actionSuccessMessage }}</p>
        </div>

        <!-- Active Battle Display (No container, No Title) -->
        <div class="active-battle-section">
            <p v-if="isLoadingActiveBattle">Checking battle status...</p>
            <div v-else-if="activeBattle && opponent" class="active-battle-resume">
                 <button 
                    @click="goToBattle(activeBattle.id)" 
                    class="button button-primary"
                 >
                   Resume Battle against {{ opponent.username }}
                 </button>
            </div>
        </div>

        <!-- User List (No container, No Title) -->
        <div class="user-list-section">
             <p v-if="isLoadingUsers && !(activeBattle && opponent)">Loading players...</p>
            <p v-else-if="!availableUsers.length && !(activeBattle && opponent)">No other players available.</p>
            <ul v-if="availableUsers.length > 0" class="simple-list">
                <li v-for="player in availableUsers" :key="player.id" class="list-item-simple">
                    <span>{{ player.username }} (Lvl {{ player.level }})</span>
                    <button
                        @click="handleChallenge(player.id)"
                        :disabled="challengingUserId === player.id"
                        class="button button-secondary button-small"
                     >
                        {{ challengingUserId === player.id ? 'Sending...' : 'Challenge' }}
                    </button>
                </li>
            </ul>
        </div>

        <!-- Pending Battles (Conditional Section, No 'From:') -->
         <div v-if="pendingBattles.length > 0" class="pending-battles-section section-simple">
            <h3>Incoming Challenges</h3>
            <p v-if="isLoadingPendingBattles">Loading challenges...</p>
            <ul v-else class="simple-list"> 
                 <li v-for="battle in pendingBattles" :key="battle.id" class="list-item-simple">
                    <span><strong>{{ battle.player1.username }}</strong> (Lvl {{ battle.player1.level }})</span>
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
    </div>
    
    <!-- Moveset Manager (Modal Placeholder) -->
    <div v-if="showMovesetManager" class="modal-overlay">
        <div class="modal-content">
            <MovesetManager />
            <button @click="showMovesetManager = false" class="close-button">Close</button>
        </div>
    </div>
  </main>
</template>

<style scoped>
/* --- Overall Layout & Theme (Keep Panel Style) --- */
.home-view {
  display: grid;
  grid-template-columns: 1fr; /* Single column by default */
  gap: 2rem;
  padding: 2rem;
  max-width: 1200px; /* Limit max width */
  margin: 1rem auto;
  background-color: var(--color-background); /* Use main background */
}

@media (min-width: 992px) { /* Adjust breakpoint for two columns */
  .home-view {
    /* Adjusted width for potentially wider stats/moves */
    grid-template-columns: minmax(400px, 450px) 1fr;
  }
}

.panel {
  background-color: var(--color-background-soft);
  padding: 1.5rem 2rem;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 2rem; /* Increased gap */
}

.panel h2 {
  margin: 0 0 0.5rem 0;
  color: var(--color-heading);
  font-size: 1.8em;
  border-bottom: 2px solid var(--vt-c-indigo);
  padding-bottom: 0.6rem;
  text-align: center;
  font-weight: 600;
}

.panel h3 {
  margin: 0 0 1rem 0;
  color: var(--color-heading);
  font-size: 1.3em;
  font-weight: 500;
  border-bottom: 1px solid var(--color-border-hover);
  padding-bottom: 0.4rem;
}

/* --- User Panel Specifics --- */
.user-panel h2 {
   border-bottom-color: var(--vt-c-blue);
}

/* --- NEW Stats Section Styles --- */
.stats-container-reimagined {
    display: flex;
    align-items: flex-start; /* Align items to the top */
    gap: 1.5rem;
    background-color: var(--color-background-mute);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
}

.stat-level {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: var(--color-background);
    border: 1px solid var(--color-border-hover);
    border-radius: 50%; /* Make it circular */
    width: 70px;
    height: 70px;
    padding: 0.5rem;
}

.stat-level .label {
    font-size: 0.8em;
    color: var(--color-text-mute);
    line-height: 1;
}

.stat-level .value {
    font-size: 1.6em;
    font-weight: bold;
    color: var(--vt-c-indigo);
    line-height: 1.2;
}

.stats-right-column {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.stat-hp {
    font-size: 1.2em;
    font-weight: bold;
    color: var(--vt-c-green-dark);
    text-align: right;
    padding-right: 0.5rem;
}

.stat-bars-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem; /* Space between bars */
}

.stat-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.stat-bar .label {
    font-size: 0.8em;
    font-weight: 600;
    width: 30px; /* Fixed width for labels */
    text-align: right;
}

.stat-bar .bar {
    flex-grow: 1;
    height: 10px;
    background-color: var(--color-background);
    border-radius: 5px;
    overflow: hidden;
    border: 1px solid var(--color-border-hover);
}

.stat-bar .fill {
    height: 100%;
    width: var(--stat-value-percent, 0%); /* Use CSS variable for width */
    border-radius: 5px;
    transition: width 0.5s ease-out;
}

.stat-bar-atk .label { color: var(--vt-c-red); }
.stat-bar-atk .fill { background-color: var(--vt-c-red); }

.stat-bar-def .label { color: var(--vt-c-blue); }
.stat-bar-def .fill { background-color: var(--vt-c-blue); }

.stat-bar-spd .label { color: var(--vt-c-yellow); }
.stat-bar-spd .fill { background-color: var(--vt-c-yellow); }


/* --- NEW Known Moves Section Styles --- */
.attacks-container {
    background-color: var(--color-background-mute);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
}

.attacks-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); 
    gap: 0.8rem;
    list-style: none;
    padding: 0;
    margin: 0 0 1rem 0; 
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
    align-items: center; /* Align content */
    transition: none; /* No transitions needed here */
    cursor: default; 
}

/* Style for empty slots in HomeView */
.attack-card.empty-slot {
    background-color: var(--color-background-mute);
    border-style: dashed;
    color: var(--color-text-mute);
    opacity: 0.7;
    justify-content: center;
    align-items: center;
    font-size: 0.9em;
    font-style: italic;
}

/* Remove specific content styles again, as they are in AttackCardDisplay */
/* .attack-card .emoji { ... } */
/* .attack-card h4 { ... } */
/* .attack-card .power { ... } */
/* .attack-card .desc { ... } */

/* --- Actions Panel Specifics (Reverted Style) --- */
.actions-panel h2 {
   border-bottom-color: var(--vt-c-red);
}

/* Container for each subsection in actions panel */
.section-simple {
    background-color: var(--color-background-mute);
    padding: 1.2rem 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    /* Removed margin-bottom, gap in panel handles spacing */
}

.action-feedback {
    margin-bottom: 1rem; /* Keep feedback visible */
    text-align: center;
    order: -1; /* Display feedback at the top */
}
/* Feedback message styles remain the same */
.error-message, .success-message { /* ... styles from previous version ... */ }
.error-message { background-color: var(--vt-c-red-soft); color: var(--vt-c-red-dark); border: 1px solid var(--vt-c-red); padding: 0.8rem 1rem; border-radius: 6px; font-weight: 500;}
.success-message { background-color: var(--vt-c-green-soft); color: var(--vt-c-green-dark); border: 1px solid var(--vt-c-green); padding: 0.8rem 1rem; border-radius: 6px; font-weight: 500;}

.no-items-message {
    color: var(--color-text-mute);
    font-style: italic;
    text-align: center;
    padding: 1rem 0;
}

/* --- Simple Lists (Users, Pending Battles) --- */
.simple-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 250px; /* Adjust height */
  overflow-y: auto;
  padding-right: 5px;
}

.list-item-simple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0.5rem; /* Slightly less padding */
  margin-bottom: 0.5rem;
  border-radius: 4px;
  background-color: var(--color-background);
  border-bottom: 1px solid var(--color-border-hover); /* Use bottom border */
  transition: background-color 0.2s ease;
}
.list-item-simple:last-child {
    margin-bottom: 0;
    border-bottom: none;
}

.list-item-simple:hover {
    background-color: var(--color-background-soft);
}

.list-item-simple span {
  font-weight: 500;
}
.list-item-simple span strong {
    color: var(--color-heading);
}

.list-item-simple .button-group {
    display: flex;
    gap: 0.5rem;
}

/* Active Battle Specific (Simplified) */
.active-battle-resume {
    text-align: center;
    padding: 0.5rem 0; 
    margin-bottom: 1rem; /* Add space below resume button */
}

/* Remove old list-item styles for active battle */
/* .list-item-simple.active { ... } */

/* --- Buttons (Keep general styles, add small variant) --- */
.button { /* ... base styles ... */
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.button:disabled { opacity: 0.6; cursor: not-allowed; }

.button-primary { background-color: var(--vt-c-indigo); color: white; }
.button-primary:hover:not(:disabled) { background-color: var(--vt-c-indigo-dark); box-shadow: 0 2px 4px rgba(0,0,0,0.2); }

.button-secondary { background-color: var(--color-border-hover); color: var(--color-text); border: 1px solid var(--color-border); }
.button-secondary:hover:not(:disabled) { background-color: var(--color-border); border-color: var(--color-text-mute); }

.button-accept { background-color: var(--vt-c-green-soft); color: var(--vt-c-green-dark); border: 1px solid var(--vt-c-green); }
.button-accept:hover:not(:disabled) { background-color: var(--vt-c-green); color: white; }

.button-decline { background-color: var(--vt-c-red-soft); color: var(--vt-c-red-dark); border: 1px solid var(--vt-c-red); }
.button-decline:hover:not(:disabled) { background-color: var(--vt-c-red); color: white; }

/* Smaller buttons for lists */
.button-small {
    padding: 0.35rem 0.8rem;
    font-size: 0.8em;
}

/* Pulse animation (Keep) */
@keyframes pulse-animation { /* ... */ }
.button.pulse { /* ... */ }
:root { --vt-c-indigo-rgb: 47, 58, 178; }

/* Fix pulse animation definition */
@keyframes pulse-animation {
  0% { box-shadow: 0 0 0 0 rgba(var(--vt-c-indigo-rgb), 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(var(--vt-c-indigo-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--vt-c-indigo-rgb), 0); }
}
.button.pulse {
  box-shadow: 0 0 0 0 rgba(var(--vt-c-indigo-rgb), 0.7);
  animation: pulse-animation 2s infinite;
}

/* Remove background/border from the sections inside Command Center */
.active-battle-section,
.user-list-section {
    background-color: transparent;
    padding: 0;
    border: none;
}

/* Keep styling for pending battles section */
.pending-battles-section {
    background-color: var(--color-background-mute);
    padding: 1.2rem 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
}

/* Adjust resume button margin if needed */
.active-battle-resume {
    text-align: center;
    padding: 0.5rem 0; 
    margin-bottom: 1rem; /* Add space below resume button */
}

/* Simplified display grid for selected moves */
.attacks-grid-display {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem; /* Smaller gap */
  list-style: none;
  padding: 0;
  margin: 0;
}
.attack-card-small.display-only {
  cursor: default;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
}
.attack-card-small.empty-slot.display-only {
    background-color: var(--color-background);
}

/* Modal Styling (Basic) */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.6);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 100;
}

.modal-content {
    background-color: var(--color-background);
    padding: 2rem;
    border-radius: 8px;
    max-width: 90vw;
    max-height: 85vh;
    overflow-y: auto; /* Scroll if content exceeds height */
    position: relative;
}

.close-button {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--color-text-mute);
}
.close-button:hover {
    color: var(--color-text);
}

.user-controls {
    margin-top: 1.5rem;
    display: flex;
    gap: 1rem;
    justify-content: center; /* Center buttons */
}

/* Add styles for danger button */
.button.button-danger {
    background-color: var(--vt-c-red-soft);
    color: var(--vt-c-red-dark);
    border-color: var(--vt-c-red);
}

.button.button-danger:hover {
    background-color: var(--vt-c-red);
    color: var(--color-text-inverse);
    border-color: var(--vt-c-red-dark);
}

</style>
