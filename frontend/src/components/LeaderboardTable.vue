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
  <div class="leaderboard-table-component-root">
    <section class="leaderboard-table-section">
      <h2>Top Players</h2>
      <div v-if="isLoading && leaderboardData.length === 0" class="loading">Loading leaderboard...</div>
      <table v-else-if="leaderboardData && leaderboardData.length > 0" class="leaderboard-table user-leaderboard">
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th title="Wins/Losses vs Humans">Human (W/L)</th>
            <th title="Wins/Losses vs Bots">BOT (W/L)</th>
            <th title="Total Damage Dealt">Dmg Done</th>
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
            <td class="center">{{ user.wins_vs_human ?? 0 }}/{{ user.losses_vs_human ?? 0 }}</td>
            <td class="center">{{ user.wins_vs_bot ?? 0 }}/{{ user.losses_vs_bot ?? 0 }}</td>
            <td class="center">{{ user.total_damage_dealt ?? 0 }}</td>
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

    <!-- UPDATED: Attack Leaderboard Section -->
    <section class="leaderboard-table-section attack-leaderboard-section">
      <h2>Top Attacks</h2>
      <div v-if="isLoading && attackLeaderboardData.length === 0" class="loading">Loading attack stats...</div>
      <table v-else-if="attackLeaderboardData && attackLeaderboardData.length > 0" class="leaderboard-table attack-leaderboard">
        <thead>
          <tr>
            <th title="Attack">Atk</th>
            <th title="Creator">Owner</th>
            <th title="Times Used Globally">Used</th>
            <th title="Overall Win Rate %">Win%</th>
            <th title="Damage Per Use (Avg)">DPU</th>
            <th title="Wins/Losses vs Humans">Human (W/L)</th>
            <th title="Wins/Losses vs Bots">BOT (W/L)</th>
            <th title="Total Damage Dealt">Dmg Done</th>
            <th title="Most Used With">Synergy</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(attackStat, index) in attackLeaderboardData" :key="attackStat.attack_details?.id || index">
            <td class="center">
              <span class="attack-item emoji-only"
                    :title="attackStat.attack_details?.name || 'Unknown Attack'"
                    @mouseenter="handleMouseEnter(attackStat.attack_details, $event)"
                    @mouseleave="handleMouseLeave">
                {{ attackStat.attack_details?.emoji || '?' }} 
              </span>
            </td>
            <td>{{ attackStat.owner_username || '-' }}</td>
            <td class="center">{{ attackStat.times_used ?? '-' }}</td>
            <td class="center">{{ attackStat.win_rate ?? '-' }}%</td>
            <td class="center">{{ attackStat.damage_per_use ?? '-' }}</td>
            <td class="center">{{ attackStat.wins_vs_human ?? 0 }}/{{ attackStat.losses_vs_human ?? 0 }}</td>
            <td class="center">{{ attackStat.wins_vs_bot ?? 0 }}/{{ attackStat.losses_vs_bot ?? 0 }}</td>
            <td class="center">{{ attackStat.total_damage_dealt ?? '-' }}</td>
            <td class="synergy-cell">
                <span v-if="!attackStat.top_co_used_attacks || attackStat.top_co_used_attacks.length === 0">-</span>
                 <template v-else>
                   <span v-for="(co_attack, idx) in attackStat.top_co_used_attacks" :key="co_attack.id"
                         class="attack-item synergy-item emoji-only"
                         :title="co_attack.name"
                         @mouseenter="handleMouseEnter(co_attack, $event)" 
                         @mouseleave="handleMouseLeave">
                      {{ co_attack.emoji || '?' }}
                   </span>
                 </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!isLoading" class="no-data-message">
        No attack data available yet.
      </div>
    </section>
  </div>
</template>

<style scoped>
.leaderboard-table-component-root {
  /* Add any necessary styles for the root wrapper if needed,
     or leave it empty if it only serves structure. */
}

.leaderboard-table-section {
    margin-top: 20px;
    position: relative; /* Keep for popup */
    font-family: var(--font-primary);
    color: var(--color-text);
}

h2 {
  text-align: center;
  margin-bottom: 15px;
  color: var(--color-accent-secondary);
  font-size: 1.2em;
  text-transform: uppercase;
  font-weight: normal;
  border-bottom: 1px dashed var(--color-border);
  padding-bottom: 8px;
}

.loading,
.no-data-message {
  text-align: center;
  padding: 15px;
  color: var(--color-log-system);
  font-style: italic;
  font-size: 0.9em;
  border: 1px dashed var(--color-border);
  background-color: var(--color-bg);
  text-transform: uppercase;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  box-shadow: none; /* Remove shadow */
  border: 1px solid var(--color-border);
}

.leaderboard-table th,
.leaderboard-table td {
  padding: 6px 8px; /* Slightly reduce padding */
  text-align: left;
  border: 1px solid var(--color-border); /* Border for all cells */
  font-size: 0.9em;
  vertical-align: middle;
}

.leaderboard-table thead {
   background-color: var(--color-bg); /* Darker header */
}

.leaderboard-table th {
  font-weight: normal; /* Pixel font often not bold */
  color: var(--color-accent-secondary);
  text-transform: uppercase;
}

.leaderboard-table tbody tr {
    background-color: var(--color-panel-bg); /* Use panel background */
}

.leaderboard-table tbody tr:nth-child(even) {
  background-color: var(--color-bg); /* Slightly darker for even rows */
}

.leaderboard-table tbody tr:hover {
  background-color: var(--color-border); /* Darken on hover */
  color: var(--color-accent-secondary);
}

/* Specific Column Alignments/Widths */
.leaderboard-table th:first-child,
.leaderboard-table td:first-child { /* Rank */
  text-align: center;
  width: 40px;
}

.user-leaderboard th:nth-child(3),
.user-leaderboard td:nth-child(3),
.attack-leaderboard th:nth-child(3),
.attack-leaderboard td:nth-child(3),
.attack-leaderboard th:nth-child(4),
.attack-leaderboard td:nth-child(4) { /* Used, Wins */
  text-align: center;
  /* width: 60px; */ /* Let content decide more */
}

/* Adjust widths for new User Leaderboard columns */
.user-leaderboard th:nth-child(3), /* Human W/L */
.user-leaderboard td:nth-child(3),
.user-leaderboard th:nth-child(4), /* BOT W/L */
.user-leaderboard td:nth-child(4) {
  width: 85px;
}
.user-leaderboard th:nth-child(5), /* Dmg Done */
.user-leaderboard td:nth-child(5) {
  width: 75px;
}

.loadout-cell {
    position: relative; 
    vertical-align: middle; 
    text-align: left; /* Override center, keep for loadout */
}

.user-leaderboard td:last-child, 
.user-leaderboard th:last-child {
    font-size: 1em; /* Normal emoji size */
    text-align: left; 
    width: auto; /* Let content decide width */
    min-width: 100px;
}

.bot-label {
    font-size: 0.8em;
    color: var(--color-log-system);
    margin-left: 5px;
    font-style: italic;
}

.attack-item {
    cursor: default;
    display: inline-block; 
    margin-right: 5px; 
    padding: 0 3px; 
    border-radius: 0;
    transition: background-color 0.2s;
    line-height: 1; 
    background-color: transparent; /* Remove background */
    border: none; /* Remove border */
}

.attack-item:hover {
    background-color: var(--color-border); /* Simple highlight */
}

/* Attack Card Popover */
.attack-hover-popup {
  position: fixed; 
  /* Position calculation removed - place it top right for now */
  top: 20px; 
  right: 20px; 
  width: 180px; /* Fixed width for consistency */
  height: auto; /* Adjust height automatically */
  z-index: 100;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0s linear 0.2s;
  pointer-events: none; /* Allow interaction only when visible */
}

.attack-hover-popup :deep(.attack-card-content) {
    /* Ensure popup style matches */
    font-size: 0.8em; /* Smaller font for popup */
}

/* Keep hover effect to show popup */
.attack-item:hover + .attack-hover-popup,
.attack-hover-popup:hover {
    opacity: 1;
    visibility: visible;
    transition: opacity 0.2s ease;
    pointer-events: auto;
}

/* Attack Leaderboard Specifics */
.attack-leaderboard-section {
    margin-top: 30px; /* More space before attack leaderboard */
}

/* Adjust column widths/alignment */
.attack-leaderboard th:first-child, 
.attack-leaderboard td:first-child { 
    width: 45px; 
    text-align: center;
    padding-left: 3px;
    padding-right: 3px;
} /* Attack Emoji */
.attack-leaderboard td:nth-child(2) { width: 80px; } /* Owner */
.attack-leaderboard td:nth-child(3) { width: 50px; } /* Used */
.attack-leaderboard td:nth-child(4) { width: 55px; } /* Win% */
.attack-leaderboard td:nth-child(5) { width: 50px; } /* DPU */
.attack-leaderboard td:nth-child(6) { width: 85px; } /* Human W/L */
.attack-leaderboard td:nth-child(7) { width: 75px; } /* BOT W/L */
.attack-leaderboard td:nth-child(8) { width: 70px; } /* Dmg Done */
.attack-leaderboard td:last-child { width: auto; min-width: 70px; } /* Synergy */

.center {
    text-align: center;
}

.synergy-cell {
    text-align: center;
}
.synergy-item {
    margin-right: 3px;
    padding: 1px 2px;
    font-size: 0.9em;
    border: 1px solid var(--color-border);
}
.synergy-item:last-child {
    margin-right: 0;
}

.attack-item.emoji-only {
    font-size: 1.2em; /* Make emoji slightly larger */
    padding: 1px; /* Minimal padding */
    display: inline-flex; /* Center vertically if needed */
    justify-content: center;
    align-items: center;
    min-width: 20px; /* Ensure minimum width for hover */
}

</style> 