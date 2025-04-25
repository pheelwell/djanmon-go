<script setup>
import { computed } from 'vue';

const props = defineProps({
  player: {
    type: Object,
    required: true
  },
  currentHp: {
    type: Number,
    required: true
  },
  statStages: {
    type: Object,
    default: () => ({})
  },
  customStatuses: {
    type: Object,
    default: () => ({})
  },
  playerType: {
    type: String, // 'user' or 'opponent'
    default: 'user'
  },
  isCurrentUser: {
    type: Boolean,
    default: false
  }
});

// Calculate HP percentage
const hpPercentage = computed(() => {
  if (!props.player || !props.player.hp || props.player.hp === 0) return 0;
  return Math.max(0, (props.currentHp / props.player.hp) * 100);
});

// Determine HP bar class based on percentage
const hpBarClass = computed(() => {
  const percentage = hpPercentage.value;
  if (percentage > 60) return 'hp-bar-high';
  if (percentage > 30) return 'hp-bar-medium';
  return 'hp-bar-low';
});

// --- Formatting Helpers ---
function formatStage(stage) {
  return stage > 0 ? `+${stage}` : `${stage}`;
}
function getStatClass(stage) {
  if (stage > 0) return 'stat-up';
  if (stage < 0) return 'stat-down';
  return '';
}

// --- Hashing and Color Generation for Statuses ---
function stringToHashCode(str) {
  if (!str) return 0;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

function getStatusColorStyle(statusName) {
  const hash = stringToHashCode(statusName);
  const hue = hash % 360; // Hue based on hash
  const saturation = 60 + (hash % 21); // Saturation between 60-80%
  const lightness = 45 + (hash % 11); // Lightness between 45-55%

  const backgroundColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  // Simple contrast check: if lightness is high, use dark text, else light text
  const textColor = lightness > 50 ? '#111' : '#fff';

  return {
    backgroundColor: backgroundColor,
    color: textColor,
    borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 15}%)` // Slightly darker border
  };
}

// Helper function for HP bar class
function getHpBarClass(currentHp, maxHp, playerType) {
    if (maxHp <= 0 || currentHp <= 0) return playerType === 'user' ? 'hp-bar-user' : 'hp-bar-opponent'; // Default if no HP
    const percentage = (currentHp / maxHp) * 100;
    let colorClass = 'hp-high';
    if (percentage <= 50) colorClass = 'hp-medium';
    if (percentage <= 20) colorClass = 'hp-low';

    const baseClass = playerType === 'user' ? 'hp-bar-user' : 'hp-bar-opponent';
    return [baseClass, colorClass];
}

const cardClasses = computed(() => [
    'player-card',
    props.playerType,
    { 'current-user': props.isCurrentUser }
]);

</script>

<template>
  <div :class="cardClasses">
      <h3>{{ player?.username }} <span v-if="player.is_bot" class="bot-label">(BOT)</span></h3>
      <!-- Container for Badges -->
      <div class="badges-area">
          <!-- Stat Stages -->
          <div class="stat-badges-container">
             <template v-for="(stage, stat) in statStages" :key="stat">
                 <span v-if="stage !== 0" :class="['stat-badge', getStatClass(stage)]">
                     {{ stat.toUpperCase() }} {{ formatStage(stage) }}
                 </span>
             </template>
          </div>
          <!-- Custom Statuses -->
          <div class="custom-statuses-container">
             <template v-for="(value, name) in customStatuses" :key="name">
                 <span v-if="value" class="custom-status-badge" :style="getStatusColorStyle(name)">
                     {{ name.replace(/_/g, ' ').toUpperCase() }} {{ typeof value === 'number' ? '(' + value + ')' : '' }}
                 </span>
             </template>
          </div>
      </div>
      <!-- HP Display at the bottom -->
      <div class="hp-display">
         <span class="hp-label">HP:</span>
         <span class="hp-values">{{ currentHp }} / {{ player?.hp }}</span>
         <div class="hp-bar-container">
             <div :class="['hp-bar-fill', hpBarClass]" :style="{ width: hpPercentage + '%' }"></div>
         </div>
      </div>
  </div>
</template>

<style scoped>
.player-card {
    /* Uses .panel styles from BattleView by default */
    display: flex;
    flex-direction: column;
    gap: 8px; /* Adjust gap */
    padding: 10px; /* Match panel padding */
    min-width: 150px; /* Allow smaller cards */
    font-family: var(--font-primary);
    line-height: 1.3;
    background-color: var(--color-panel-bg); /* Ensure background is set */
    border: var(--border-width) solid var(--color-border);
    box-shadow: inset 0 0 0 2px var(--color-bg); /* Inner border */
    border-radius: 0;
}

.player-card.opponent {
    /* Optional: slightly different bg or border for opponent? */
    /* Example: border-color: var(--color-accent); */
}

.player-card h3 { /* Player Name */
    margin: 0;
    color: var(--color-accent-secondary);
    font-size: 1.1em;
    font-weight: normal;
    line-height: 1.2;
    text-align: center;
    border-bottom: 1px dashed var(--color-border);
    padding-bottom: 4px;
    margin-bottom: 4px;
    text-transform: uppercase;
}

.bot-label {
    font-size: 0.8em;
    color: var(--color-log-system);
    margin-left: 5px;
}

.badges-area {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-height: 30px; /* Ensure space even if empty */
    margin-bottom: auto; /* Push HP bar to bottom */
}

.stat-badges-container,
.custom-statuses-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    justify-content: center; /* Center badges */
}

.stat-badge, .custom-status-badge {
    display: inline-block;
    padding: 1px 5px;
    font-size: 0.8em;
    font-weight: normal;
    border-radius: 0;
    border: 1px solid;
    line-height: 1.1;
    text-transform: uppercase;
}

.stat-badge.stat-up {
    color: var(--color-stat-up);
    border-color: var(--color-stat-up);
    background-color: rgba(83, 189, 235, 0.1); /* Faint background */
}

.stat-badge.stat-down {
    color: var(--color-stat-down);
    border-color: var(--color-stat-down);
    background-color: rgba(233, 69, 96, 0.1);
}

.custom-status-badge {
    /* Style is dynamically generated via :style */
    /* Add base styling */
    font-weight: normal;
}

/* --- HP Bar --- */
.hp-display {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
}

.hp-label {
    font-size: 0.9em;
    color: var(--color-text);
    flex-shrink: 0;
}

.hp-values {
    font-size: 0.9em;
    color: var(--color-text);
    flex-shrink: 0;
    margin-left: auto; /* Push values to right */
    font-weight: bold;
}

.hp-bar-container {
    flex-grow: 1;
    height: 15px; /* Pixel-friendly height */
    background-color: #333; /* Dark background for bar */
    border: 1px solid var(--color-border);
    padding: 1px; /* Inner padding to contain fill */
    box-shadow: inset 1px 1px 0px rgba(0,0,0,0.5); /* Inner shadow */
    position: relative;
}

.hp-bar-fill {
    height: 100%;
    transition: width 0.5s ease-in-out;
    position: absolute;
    top: 0;
    left: 0;
    /* Base color if none match */
    background-color: var(--color-text); 
}

.hp-bar-high {
    background-color: var(--color-hp-high);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2); /* Optional highlight */
}
.hp-bar-medium {
    background-color: var(--color-hp-medium);
}
.hp-bar-low {
    background-color: var(--color-hp-low);
}

/* Remove old progress element styles */
/* progress { ... } */
/* progress::-webkit-progress-bar { ... } */
/* progress::-webkit-progress-value { ... } */
/* progress::-moz-progress-bar { ... } */
/* .hp-bar-user::-webkit-progress-value, ... etc */

</style> 