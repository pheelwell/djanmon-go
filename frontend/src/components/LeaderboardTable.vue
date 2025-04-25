<script setup>
import { ref, computed } from 'vue';
// Use AttackCardDisplay for the popup content
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';

const props = defineProps({
  leaderboardData: {
    type: Array,
    default: () => []
  },
  attackLeaderboardData: {
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
  // No longer need position calculation based on event

  hoverCardStyle.value = {
    // Only control visibility/opacity now
    opacity: 1,
    visibility: 'visible' // Ensure it's visible
  };
}

function handleMouseLeave() {
  // Delay hiding the card slightly to allow moving mouse onto it
  hoverTimeoutId.value = setTimeout(() => {
    hoveredAttack.value = null;
    hoverCardStyle.value = {
        // Only control visibility/opacity now
        opacity: 0,
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
    <div v-if="isLoading && leaderboardData.length === 0" class="loading">Loading leaderboard...</div>
    <table v-else-if="leaderboardData && leaderboardData.length > 0" class="leaderboard-table user-leaderboard">
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Wins</th>
          <th>Atks</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(user, index) in leaderboardData" :key="user.id">
          <td>{{ index + 1 }}</td>
          <td>
            {{ user.username }}
            <span v-if="user.is_bot" class="bot-label">(BOT)</span>
          </td>
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
    <div v-else-if="!isLoading" class="no-data-message">
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

  <!-- NEW: Attack Leaderboard Section -->
  <section class="leaderboard-table-section attack-leaderboard-section">
    <h2>Top Attacks</h2>
    <div v-if="isLoading && attackLeaderboardData.length === 0" class="loading">Loading attack stats...</div>
    <table v-else-if="attackLeaderboardData && attackLeaderboardData.length > 0" class="leaderboard-table attack-leaderboard">
      <thead>
        <tr>
          <th>Attack</th>
          <th>Owner</th>
          <th>Used</th>
          <th>Wins</th>
        </tr>
      </thead>
      <tbody>
        <!-- Example structure, replace with actual data fields -->
        <tr v-for="(attackStat, index) in attackLeaderboardData" :key="attackStat.attack_id || index">
          <td>
            <span class="attack-item" 
                  @mouseenter="handleMouseEnter(attackStat.attack_details, $event)" 
                  @mouseleave="handleMouseLeave">
              {{ attackStat.attack_details?.emoji || '' }} {{ attackStat.attack_details?.name || 'Unknown' }}
            </span>
          </td>
          <td>{{ attackStat.owner_username || '-' }}</td>
          <td>{{ attackStat.times_used ?? '-' }}</td>
          <td>{{ attackStat.total_wins ?? '-' }}</td> 
        </tr>
      </tbody>
    </table>
    <div v-else-if="!isLoading" class="no-data-message">
      No attack data available yet.
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

.loadout-cell {
    position: relative; /* Needed for absolute positioning of children/card */
    vertical-align: middle; /* Vertically center content */
}

.user-leaderboard td:last-child, /* Loadout Specifics */
.user-leaderboard th:last-child {
    font-size: 1.1em; /* Increase emoji size slightly */
    color: var(--color-text); /* Make emojis normal text color */
    text-align: left; /* Align emojis left */
    width: 150px; 
}

.attack-item {
    cursor: default; /* Indicate interactivity */
    display: inline-block; /* Allow spacing */
    margin-right: 0.5em; /* Space between attack items */
    padding: 0 0.3em; 
    border-radius: 3px;
    transition: background-color 0.2s;
    line-height: 1; /* Prevent extra line height */
}

.attack-item:hover {
    background-color: var(--color-background-mute); /* Highlight on hover */
}

/* Styles for the hover popup wrapper */
.attack-hover-popup {
  position: fixed; 
  top: 50%;      /* Keep vertically centered */
  left: 20px;     /* Position from left edge */
  transform: translateY(-50%); /* Only vertical centering needed */
  background-color: var(--color-background);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  padding: 0.8rem; 
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 1000; 
  pointer-events: auto; 
  opacity: 0; 
  transition: opacity 0.2s ease-in-out, visibility 0.2s ease-in-out;
  visibility: hidden; 
  min-width: 140px;
  max-width: 200px; 
  height: 180px; 
  display: flex; 
  justify-content: center;
  align-items: center;
}

.bot-label {
  font-weight: normal;
  font-size: 0.9em;
  color: var(--color-text-mute);
  margin-left: 0.3em;
}

.leaderboard-table-section {
    margin-bottom: 2.5rem; /* Add space between sections */
}

.leaderboard-table-section:last-child {
    margin-bottom: 0; /* Remove bottom margin from the last section */
}

/* Optional: Add specific styles if needed */
.user-leaderboard {
  /* styles specific to user table */
}

.attack-leaderboard {
  /* styles specific to attack table */
}

/* Adjust column widths for the new attack table */
.attack-leaderboard th:nth-child(1), /* Attack Name */
.attack-leaderboard td:nth-child(1) {
  width: auto; /* Let it take available space */
  text-align: left;
}

.attack-leaderboard th:nth-child(2), /* Owner */
.attack-leaderboard td:nth-child(2) {
  width: 120px; 
  text-align: left;
}

.attack-leaderboard th:nth-child(3), /* Used */
.attack-leaderboard td:nth-child(3),
.attack-leaderboard th:nth-child(4), /* Wins */
.attack-leaderboard td:nth-child(4) {
  width: 80px;
  text-align: center;
}

</style> 