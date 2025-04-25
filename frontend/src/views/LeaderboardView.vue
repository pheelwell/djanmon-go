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


</script>

<template>
  <div class="leaderboard-view panel">
    <h1>Leaderboard</h1>

    <div v-if="leaderboardError" class="error-message">
      ⚠️ Error loading data: {{ leaderboardError }}
    </div>

    <!-- Current User Stats Section (Needs styling in its component) -->
    <UserStatsSummary
        v-if="isAuthenticated && !leaderboardError"
        :stats="myStats"
        :isLoading="isLoadingMyStats"
        class="user-summary-section" 
    />

    <!-- Leaderboard Table Section (Needs styling in its component) -->
    <LeaderboardTable
        :leaderboardData="leaderboardData"
        :isLoading="isLoadingLeaderboard"
        class="leaderboard-table-section"
    />

  </div>
</template>

<style scoped>
.leaderboard-view {
  /* Uses .panel style from HomeView */
  max-width: 900px;
  margin: 1rem auto;
  padding: var(--panel-padding);
  font-family: var(--font-primary);
}

h1 {
  /* Use panel-title styling */
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

.error-message {
  /* Style adapted from AttackCreator */
  padding: 8px 10px;
  border-radius: 0;
  font-weight: normal;
  text-align: center;
  margin-bottom: 10px; 
  border: 1px solid var(--color-accent);
  font-size: 0.9em;
  background-color: rgba(233, 69, 96, 0.1);
  color: var(--color-accent);
}

.user-summary-section,
.leaderboard-table-section {
    margin-top: 15px; /* Add space between sections */
}

</style> 