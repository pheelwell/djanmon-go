<script setup>
import { ref, computed, onMounted } from 'vue';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth'; // To check if user is logged in
import { storeToRefs } from 'pinia';
// import AttackCard from '@/components/AttackCard.vue'; // Import the new component
// import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // <-- Import this instead
import UserStatsSummary from '@/components/UserStatsSummary.vue'; // <-- Import
import LeaderboardTable from '@/components/LeaderboardTable.vue'; // <-- Import

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
// const hoveredAttack = ref(null); // Will hold the attack object being hovered
// const hoverCardStyle = ref({}); // Holds position style for the card

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
// const nemesisDisplay = computed(() => {
//   if (!myStats.value || !myStats.value.nemesis) {
//     return 'None (yet!)';
//   }
//   return `${myStats.value.nemesis.username} (${myStats.value.nemesis.losses_against} losses)`;
// });

// REPLACED formatLoadout with individual span logic for hover
// function formatLoadout(attacks) {
//   if (!attacks || attacks.length === 0) {
//     return '-';
//   }
//   return attacks.map(attack => attack.emoji || attack.name).join(', ');
// }

// NEW: Hover handlers
// function handleMouseEnter(attack, event) {
//   console.log('Mouse Enter:', attack.name, event.target);
//   hoveredAttack.value = attack;
//   // Position card slightly below and to the right of the triggering element
//   const rect = event.target.getBoundingClientRect();
//   hoverCardStyle.value = {
//     left: `${rect.left + window.scrollX}px`,
//     top: `${rect.bottom + window.scrollY + 5}px`, // 5px offset below
//     opacity: 1,
//     transform: 'translateY(0)'
//   };
//   console.log('Hover Card Style:', hoverCardStyle.value);
// }

// function handleMouseLeave() {
//   console.log('Mouse Leave');
//   hoveredAttack.value = null;
//   // We don't strictly need to reset style here as v-if removes the element,
//   // but keeping opacity/transform helps if we change to v-show
//   hoverCardStyle.value = {
//       ...hoverCardStyle.value, // Keep position but fade out
//       opacity: 0,
//       transform: 'translateY(10px)'
//   };
// }

</script>

<template>
  <div class="leaderboard-view">
    <h1>Leaderboard</h1>

    <div v-if="leaderboardError" class="error-message">
      Error loading data: {{ leaderboardError }}
    </div>

    <!-- Current User Stats Section (UPDATED) -->
    <UserStatsSummary
        v-if="isAuthenticated && !leaderboardError"
        :stats="myStats"
        :isLoading="isLoadingMyStats"
    />

    <!-- Leaderboard Table Section (UPDATED) -->
    <LeaderboardTable
        :leaderboardData="leaderboardData"
        :isLoading="isLoadingLeaderboard"
    />

    <!-- REMOVED: Attack Card Popover (now inside LeaderboardTable) -->
    <!-- <div v-if="hoveredAttack" ... > ... </div> -->

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

/* REMOVED: .loading styles (handled by components) */
/* REMOVED: .my-stats styles (moved to UserStatsSummary) */
/* REMOVED: .my-stats h2 styles */
/* REMOVED: .my-stats-grid styles */
/* REMOVED: .my-stats p styles */
/* REMOVED: .my-stats strong styles */
/* REMOVED: .leaderboard-table-section styles (moved to LeaderboardTable) */
/* REMOVED: .leaderboard-table styles */
/* REMOVED: table th, td styles */
/* REMOVED: table head styles */
/* REMOVED: table body styles */
/* REMOVED: column width/alignment styles */
/* REMOVED: .loadout-cell styles */
/* REMOVED: .attack-item styles */
/* REMOVED: .attack-hover-popup styles */

</style> 