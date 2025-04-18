<script setup>
import { ref, computed, onMounted } from 'vue';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth'; // To check if user is logged in
import { storeToRefs } from 'pinia';
// import AttackCard from '@/components/AttackCard.vue'; // Import the new component
import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // <-- Import this instead

const gameStore = useGameStore();
const authStore = useAuthStore();

// Destructure state and getters from the store, making them reactive refs
const {
  myStats,
  leaderboardData,
  isLoadingMyStats,
  isLoadingLeaderboard,
  leaderboardError
} = storeToRefs(gameStore);

// Destructure actions
const { fetchMyStats, fetchLeaderboard } = gameStore;

// NEW: State for hover card
const hoveredAttack = ref(null); // Will hold the attack object being hovered
const hoverCardStyle = ref({}); // Holds position style for the card

const isLoading = computed(() => isLoadingMyStats.value || isLoadingLeaderboard.value);
const isAuthenticated = computed(() => authStore.isAuthenticated);

// Fetch data when the component is mounted
onMounted(() => {
  // Only fetch personal stats if the user is logged in
  if (isAuthenticated.value) {
    fetchMyStats();
  }
  fetchLeaderboard();
});

// Helper to format nemesis display
const nemesisDisplay = computed(() => {
  if (!myStats.value || !myStats.value.nemesis) {
    return 'None (yet!)';
  }
  return `${myStats.value.nemesis.username} (${myStats.value.nemesis.losses_against} losses)`;
});

// REPLACED formatLoadout with individual span logic for hover
// function formatLoadout(attacks) {
//   if (!attacks || attacks.length === 0) {
//     return '-';
//   }
//   return attacks.map(attack => attack.emoji || attack.name).join(', ');
// }

// NEW: Hover handlers
function handleMouseEnter(attack, event) {
  console.log('Mouse Enter:', attack.name, event.target);
  hoveredAttack.value = attack;
  // Position card slightly below and to the right of the triggering element
  const rect = event.target.getBoundingClientRect();
  hoverCardStyle.value = {
    left: `${rect.left + window.scrollX}px`,
    top: `${rect.bottom + window.scrollY + 5}px`, // 5px offset below
    opacity: 1,
    transform: 'translateY(0)'
  };
  console.log('Hover Card Style:', hoverCardStyle.value);
}

function handleMouseLeave() {
  console.log('Mouse Leave');
  hoveredAttack.value = null;
  // We don't strictly need to reset style here as v-if removes the element,
  // but keeping opacity/transform helps if we change to v-show
  hoverCardStyle.value = {
      ...hoverCardStyle.value, // Keep position but fade out
      opacity: 0,
      transform: 'translateY(10px)'
  };
}

</script>

<template>
  <div class="leaderboard-view">
    <h1>Leaderboard</h1>

    <div v-if="leaderboardError" class="error-message">
      Error loading data: {{ leaderboardError }}
    </div>

    <!-- Current User Stats Section -->
    <section v-if="isAuthenticated && !leaderboardError" class="my-stats">
      <h2>My Stats</h2>
      <div v-if="isLoadingMyStats" class="loading">Loading your stats...</div>
      <div v-else-if="myStats">
        <div class="my-stats-grid">
          <p><strong>Wins:</strong> {{ myStats.total_wins ?? 'N/A' }}</p>
          <p><strong>Losses:</strong> {{ myStats.total_losses ?? 'N/A' }}</p>
          <p><strong>Rounds Played:</strong> {{ myStats.total_rounds_played ?? 'N/A' }}</p>
          <p><strong>Nemesis:</strong> {{ nemesisDisplay }}</p>
        </div>
      </div>
       <div v-else>Could not load your stats.</div>
    </section>

    <!-- Leaderboard Table Section -->
    <section class="leaderboard-table-section">
      <h2>Top Players</h2>
      <div v-if="isLoadingLeaderboard" class="loading">Loading leaderboard...</div>
      <table v-else-if="leaderboardData && leaderboardData.length > 0" class="leaderboard-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Username</th>
            <th>Level</th>
            <th>Wins</th>
            <th>Current Loadout</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(user, index) in leaderboardData" :key="user.id">
            <td>{{ index + 1 }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.level }}</td>
            <td>{{ user.total_wins }}</td>
            <td class="loadout-cell">
              <span v-if="!user.selected_attacks || user.selected_attacks.length === 0">-</span>
              <span 
                v-for="attack in user.selected_attacks" 
                :key="attack.id" 
                class="attack-item"
                @mouseenter="handleMouseEnter(attack, $event)"
                @mouseleave="handleMouseLeave"
              >
                {{ attack.emoji || attack.name }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!leaderboardError">
        No player data available yet.
      </div>
    </section>

    <!-- Attack Card Popover - Use AttackCardDisplay now -->
    <div 
      v-if="hoveredAttack" 
      class="attack-hover-popup" 
      :style="hoverCardStyle"
    >
      <AttackCardDisplay :attack="hoveredAttack" />
    </div>

  </div>
</template>

<style scoped>
.leaderboard-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
}

h1, h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}

.error-message {
  color: var(--vt-c-red);
  background-color: var(--vt-c-red-soft);
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}

.loading {
  text-align: center;
  padding: 1rem;
  color: var(--color-text-muted);
}

.my-stats {
  background-color: var(--color-background-soft);
  padding: 1.5rem 2rem;
  border-radius: 8px;
  margin-bottom: 2.5rem;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  border-left: 5px solid var(--color-border-hover);
}

.my-stats h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.8rem;
}

.my-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
}

.my-stats p {
  margin: 0;
  line-height: 1.6;
  background-color: var(--color-background-mute);
  padding: 0.8rem 1rem;
  border-radius: 4px;
}

.my-stats strong {
    color: var(--color-text);
    display: block;
    margin-bottom: 0.25rem;
    font-size: 0.9em;
    color: var(--color-text-muted);
}

.leaderboard-table-section {
    margin-top: 2rem;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.leaderboard-table th,
.leaderboard-table td {
  padding: 0.8rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.leaderboard-table th {
  background-color: var(--color-background-mute);
  font-weight: bold;
  color: var(--color-heading);
}

.leaderboard-table tbody tr:nth-child(even) {
  background-color: var(--color-background-soft);
}

.leaderboard-table tbody tr:hover {
  background-color: var(--color-background-mute);
}

.leaderboard-table td:first-child, /* Rank */
.leaderboard-table th:first-child {
  text-align: center;
  width: 50px;
}
.leaderboard-table td:nth-child(3), /* Level */
.leaderboard-table th:nth-child(3),
.leaderboard-table td:nth-child(4), /* Wins */
.leaderboard-table th:nth-child(4) {
  text-align: center;
  width: 80px;
}

.leaderboard-table td:last-child { /* Loadout */
    font-size: 0.9em;
    color: var(--color-text-muted);
    /* Ensure cell can contain multiple items */
    /* line-height: 1.8;  Adjust if needed */
}

.loadout-cell {
    position: relative; /* Needed for absolute positioning of children/card */
}

.attack-item {
    cursor: default; /* Indicate interactivity */
    display: inline-block; /* Allow spacing */
    margin-right: 0.5em; /* Space between attack items */
    padding: 0.1em 0.3em;
    border-radius: 3px;
    transition: background-color 0.2s;
}

.attack-item:hover {
    background-color: var(--color-background-mute); /* Highlight on hover */
}

/* NEW: Styles for the hover popup wrapper */
.attack-hover-popup {
  position: absolute;
  background-color: var(--color-background);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  padding: 0.8rem; /* Match wrapper padding */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 10; /* Ensure it's on top */
  pointer-events: none; /* Prevent interaction with the popup */
  opacity: 0; /* Hidden by default, controlled by style binding */
  transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
  transform: translateY(10px);
  /* Set a min/max width if needed, or let content decide */
  min-width: 140px; 
  max-width: 200px; /* Example max width */
  /* Set a fixed height to match other cards? */
  height: 180px; /* Match AttackCreatorView */
  display: flex; /* Ensure content inside centers if needed */
  justify-content: center;
  align-items: center;
}

/* REMOVED .attack-card styles from here */

</style> 