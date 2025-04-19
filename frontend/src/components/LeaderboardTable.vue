<script setup>
import { ref, computed } from 'vue';
// Use AttackCardDisplay for the popup content
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';

const props = defineProps({
  leaderboardData: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

// State for hover card
const hoveredAttack = ref(null); // Will hold the attack object being hovered
const hoverCardStyle = ref({}); // Holds position style for the card
const hoverTimeoutId = ref(null); // Timeout for delayed hide

// Hover handlers
function handleMouseEnter(attack, event) {
  if (hoverTimeoutId.value) {
    clearTimeout(hoverTimeoutId.value);
    hoverTimeoutId.value = null;
  }
  hoveredAttack.value = attack;
  // Calculate position based on the triggering element (e.g., the emoji span)
  const rect = event.target.getBoundingClientRect();
  hoverCardStyle.value = {
    // Position below and slightly offset from the element
    left: `${rect.left + window.scrollX}px`, 
    top: `${rect.bottom + window.scrollY + 8}px`, // 8px offset below
    opacity: 1,
    transform: 'translateY(0)',
    visibility: 'visible' // Ensure it's visible
  };
}

function handleMouseLeave() {
  // Delay hiding the card slightly to allow moving mouse onto it
  hoverTimeoutId.value = setTimeout(() => {
    hoveredAttack.value = null;
    hoverCardStyle.value = {
        ...hoverCardStyle.value,
        opacity: 0,
        transform: 'translateY(10px)',
        visibility: 'hidden' // Hide it
    };
  }, 150); // 150ms delay
}

// Keep hover card visible if mouse enters it
function handleCardMouseEnter() {
  if (hoverTimeoutId.value) {
    clearTimeout(hoverTimeoutId.value);
    hoverTimeoutId.value = null;
  }
}

// Hide card when mouse leaves the card itself
function handleCardMouseLeave() {
    handleMouseLeave(); // Use the same delayed hide logic
}

</script>

<template>
  <section class="leaderboard-table-section">
    <h2>Top Players</h2>
    <div v-if="isLoading" class="loading">Loading leaderboard...</div>
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
          <td>
            {{ user.username }}
            <span v-if="user.is_bot" class="bot-label">(BOT)</span>
          </td>
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
    <div v-else class="no-data-message">
      No player data available yet.
    </div>

    <!-- Attack Card Popover - Use AttackCardDisplay now -->
    <div
      v-if="hoveredAttack"
      class="attack-hover-popup"
      :style="hoverCardStyle"
      @mouseenter="handleCardMouseEnter"
      @mouseleave="handleCardMouseLeave"
    >
      <AttackCardDisplay :attack="hoveredAttack" />
    </div>

  </section>
</template>

<style scoped>
/* Styles adapted from LeaderboardView.vue */
.leaderboard-table-section {
    margin-top: 2rem;
    position: relative; /* Needed for popup positioning context */
}

h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}

.loading,
.no-data-message {
  text-align: center;
  padding: 1rem;
  color: var(--color-text-muted);
  font-style: italic;
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

/* Styles for the hover popup wrapper */
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
  /* Set a fixed height to match other cards */
  height: 180px; /* Match AttackCreatorView, adjust if needed */
  display: flex; /* Ensure content inside centers if needed */
  justify-content: center;
  align-items: center;
}

.bot-label {
  font-weight: normal;
  font-size: 0.9em;
  color: var(--color-text-mute);
  margin-left: 0.3em;
}

</style> 