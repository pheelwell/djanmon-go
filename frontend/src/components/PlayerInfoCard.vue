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
      <div class="stat-badges-container">
          <!-- Stat Stages -->
          <span class="stat-badges">
             <template v-for="(stage, stat) in statStages" :key="stat">
                 <span v-if="stage !== 0" :class="[
                     'stat-badge',
                     getStatClass(stage)
                 ]">
                     {{ stat.toUpperCase() }} {{ formatStage(stage) }}
                 </span>
             </template>
          </span>
          <!-- Custom Statuses -->
          <span class="custom-statuses">
             <template v-for="(value, name) in customStatuses" :key="name">
                 <span v-if="value"
                       class="custom-status-badge"
                       :style="getStatusColorStyle(name)">
                     {{ name.replace(/_/g, ' ').toUpperCase() }} {{ typeof value === 'number' ? '(' + value + ')' : '' }}
                 </span>
             </template>
          </span>
      </div>
      <div class="hp-display">
         <p>HP: {{ currentHp }} / {{ player?.hp }}</p>
         <progress
            :value="currentHp"
            :max="player?.hp"
            :class="hpBarClass"
        ></progress>
      </div>
  </div>
</template>

<style scoped>
/* Styles copied and adapted from BattleView.vue */
.player-card {
    min-width: 280px;
    flex: 1;
    padding: 1rem 1.5rem;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background-color: var(--color-background-mute);
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}

.player-card.user { border-left: 4px solid var(--vt-c-blue); }
.player-card.opponent { border-left: 4px solid var(--vt-c-red); }

.player-card h3 {
    margin: 0;
    color: var(--color-heading);
    font-size: 1.3em;
    font-weight: 600;
    line-height: 1.2;
}
.player-card h3 span {
    font-weight: normal;
    font-size: 0.9em;
    color: var(--color-text-muted);
}

.player-card p { /* HP Text */
    margin: 0;
    text-align: right;
    font-size: 0.9em;
    color: var(--color-text);
    font-weight: 500;
    white-space: nowrap;
    flex-shrink: 0;
    max-width: 80px;
}

.player-card progress {
    width: auto;
    height: 12px;
    flex-grow: 1;
    -webkit-appearance: none;
    appearance: none;
    background-color: var(--color-background-soft);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}

progress::-webkit-progress-bar {
    background-color: var(--color-background-soft);
    border-radius: 6px;
}

progress::-webkit-progress-value {
    border-radius: 6px;
    transition: width 0.5s ease-in-out;
}

progress::-moz-progress-bar {
    border-radius: 6px;
    transition: width 0.5s ease-in-out;
}

.hp-bar-user::-webkit-progress-value,
.hp-bar-user::-moz-progress-bar {
    background-color: var(--vt-c-blue);
}
.hp-bar-opponent::-webkit-progress-value,
.hp-bar-opponent::-moz-progress-bar {
    background-color: var(--vt-c-red);
}

progress.hp-medium::-webkit-progress-value,
progress.hp-medium::-moz-progress-bar {
    background-color: var(--vt-c-yellow-darker);
}

progress.hp-low::-webkit-progress-value,
progress.hp-low::-moz-progress-bar {
    background-color: var(--vt-c-red-dark);
}

.hp-bar-opponent.hp-low::-webkit-progress-value,
.hp-bar-opponent.hp-low::-moz-progress-bar {
     background-color: var(--vt-c-red-dark);
}

.stat-badges-container {
    min-height: 20px; /* Prevents layout shifts */
    display: flex;
    flex-direction: column;
    gap: 0.4rem; /* Space between stat badges and custom statuses */
}

.stat-badges, .custom-statuses {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}

.stat-badge {
    display: inline-block;
    padding: 0.2em 0.5em;
    font-size: 0.8em;
    font-weight: 600;
    border-radius: 4px;
    color: var(--vt-c-white-soft);
    text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
    border: 1px solid transparent; /* Add for consistency */
}

.stat-badge.stat-up {
    background-color: var(--vt-c-green);
    border-color: var(--vt-c-green-dark);
}

.stat-badge.stat-down {
    background-color: var(--vt-c-red);
    border-color: var(--vt-c-red-dark);
}

.custom-status-badge {
    display: inline-block;
    padding: 0.2em 0.5em;
    font-size: 0.8em;
    font-weight: 500;
    border-radius: 4px;
    text-transform: capitalize;
    border: 1px solid transparent;
}

.hp-display {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: auto; /* Pushes HP to bottom */
}

.bot-label {
    font-weight: normal;
    font-size: 0.8em;
    color: var(--color-text-muted);
    margin-left: 0.3em;
}
</style> 