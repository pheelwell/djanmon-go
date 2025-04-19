<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  logEntries: {
    type: Array,
    default: () => []
  },
  userPlayerRole: {
    type: String, // 'player1' or 'player2' or null
    required: true
  },
  battleId: {
    type: [String, Number],
    required: true
  }
});

const battleLogContainer = ref(null);
const userScrolledUp = ref(false); // Track if user manually scrolled up

// Function to handle user scroll
function handleScroll() {
    const container = battleLogContainer.value;
    if (!container) return;
    // Check if user is scrolled near the bottom
    const threshold = 20; // Pixels from bottom to consider "at bottom"
    const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
    userScrolledUp.value = !atBottom;
}

// Function to scroll log to bottom if needed
function scrollToBottomIfNeeded(force = false) {
  nextTick(() => {
    const container = battleLogContainer.value;
    if (container) {
        // Only scroll down if user hasn't manually scrolled up, or if forced (initial load)
        if (!userScrolledUp.value || force) {
            container.scrollTop = container.scrollHeight;
        }
    }
  });
}

// Watch for new log entries
watch(() => props.logEntries, (newLog, oldLog) => {
    // Determine if the scroll should happen *before* nextTick captures the current state
    const container = battleLogContainer.value;
    let shouldScroll = false;
    if (container) {
        const threshold = 20;
        const atBottomBeforeUpdate = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
        shouldScroll = atBottomBeforeUpdate;
    }

    // Wait for DOM update, then scroll if user was at bottom
    nextTick(() => {
        const updatedContainer = battleLogContainer.value;
        if (updatedContainer && shouldScroll) {
            updatedContainer.scrollTop = updatedContainer.scrollHeight;
            userScrolledUp.value = false; // Reset flag after auto-scroll
        }
    });
}, { deep: true }); // Don't use immediate: true, handle initial scroll in onMounted

// Add scroll listener on mount
onMounted(() => {
    const container = battleLogContainer.value;
    if (container) {
        container.addEventListener('scroll', handleScroll, { passive: true });
    }
    // Scroll to bottom on initial load
    scrollToBottomIfNeeded(true); // Force scroll on mount
});

// Remove listener on unmount
onBeforeUnmount(() => {
    const container = battleLogContainer.value;
    if (container) {
        container.removeEventListener('scroll', handleScroll);
    }
});

</script>

<template>
  <div class="battle-log-container" ref="battleLogContainer">
      <ul v-if="logEntries && logEntries.length" class="turn-summary-list">
          <template v-for="(entry, index) in logEntries" :key="`${battleId}-entry-${index}`">
              <!-- ADDED: Turn Separator Line -->
              <li v-if="entry.effect_type === 'turnchange'" class="log-turn-separator" aria-hidden="true"></li>

              <!-- Existing Log Entry List Item -->
              <li
                  :class="{
                      'log-entry-container': true,
                      [`source-${entry.source || 'unknown'}`]: true,
                      'log-user': entry.source === userPlayerRole,
                      'log-opponent': entry.source !== userPlayerRole && entry.source !== 'system' && entry.source !== 'script' && entry.source !== 'debug',
                      'log-system': entry.source === 'system' || entry.source === 'script' || entry.source === 'debug'
                  }"
              >
                  <span
                     :class="[
                         'log-bubble',
                         `effect-${entry.effect_type || 'info'}`,
                         entry.effect_details?.stat ? `bubble-stat-${entry.effect_details.stat}` : '',
                         entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0 ? 'stat-arrow-up' : '',
                         entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0 ? 'stat-arrow-down' : ''
                     ]"
                  >
                      <span v-if="entry.effect_type === 'action' && entry.effect_details?.emoji" class="log-emoji">{{ entry.effect_details.emoji }}</span>
                      <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0" class="stat-arrow up">▲</span>
                      <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0" class="stat-arrow down">▼</span>
                      {{ entry.text }}
                  </span>
              </li>
          </template>
      </ul>
      <div v-else class="empty-log-message">Battle log is empty.</div>
      <!-- Empty div to ensure scroll height is calculated correctly -->
      <div style="height: 1px; flex-shrink: 0;"></div>
  </div>
</template>

<style scoped>
/* Styles adapted from BattleView.vue messages section */
.battle-log-container {
    padding: 0.5rem;
    min-height: 200px;
    max-height: 400px;
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden; /* Prevent horizontal scroll */
}

.turn-summary-list {
    flex-grow: 1;
    list-style: none;
    padding: 0 0.5rem;
    margin: 0;
}

.empty-log-message {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--color-text-mute);
    font-style: italic;
}

/* Container for each log line - uses Flex */
.log-entry-container {
    margin-bottom: 0.5rem;
    display: flex;
}

/* --- Alignment by Source --- */
.log-entry-container.log-user {
   justify-content: flex-start;
}
.log-entry-container.log-opponent {
    justify-content: flex-end;
}
.log-entry-container.log-system {
   justify-content: center;
}

/* The bubble itself */
.log-bubble {
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    max-width: 70%;
    word-wrap: break-word;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    line-height: 1.3;
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    border: 1px solid transparent;
    transition: background-color 0.2s ease, color 0.2s ease;
}

/* --- Log Bubble Styling by Source --- */
.log-entry-container.source-player1 .log-bubble,
.log-entry-container.source-player2 .log-bubble {
    background-color: var(--vt-c-indigo); /* Default player bubble */
    color: white;
}
/* Adjust rounding based on side */
.log-entry-container.log-user .log-bubble {
    border-bottom-left-radius: 3px;
}
.log-entry-container.log-opponent .log-bubble {
     border-bottom-right-radius: 3px;
     border-bottom-left-radius: 15px; /* Keep other corners rounded */
}

.log-entry-container.source-script .log-bubble {
    background-color: #5a5f89; /* Distinct color for script/system actions */
    color: white;
}

.log-entry-container.source-system .log-bubble {
    color: var(--color-text-mute);
    background-color: transparent;
    box-shadow: none;
    font-style: italic;
    border: none;
    padding: 0.1rem 0.5rem;
}

.log-entry-container.source-debug .log-bubble {
    color: #666;
    background-color: transparent;
    box-shadow: none;
    font-style: italic;
    opacity: 0.6;
    font-size: 0.85em;
    padding: 0.1rem 0.5rem;
    border: none;
}

/* --- Log Bubble Styling by Effect Type --- */
/* Actions usually keep their source styling */

.log-bubble.effect-damage {
    background-color: var(--vt-c-red-soft);
    color: var(--vt-c-red-dark);
    border-color: var(--vt-c-red);
}

.log-bubble.effect-heal {
    background-color: var(--vt-c-green-soft);
    color: var(--vt-c-green-dark);
    border-color: var(--vt-c-green);
}

/* Stat change bubble itself can be neutral, arrows provide visual */
.log-bubble.effect-stat_change {
    background-color: var(--color-background-soft); /* Subtle background */
    color: var(--color-text);
    border-color: var(--color-border-hover);
}

.log-bubble.effect-status_apply,
.log-bubble.effect-status_remove,
.log-bubble.effect-status_effect {
     background-color: var(--color-background-mute);
     color: var(--color-text);
     border-style: dashed;
     border-color: var(--color-border-hover);
}

.log-bubble.effect-info {
    /* Keep neutral, source styles will apply */
    color: var(--color-text);
}
/* Override for system/script info */
.log-entry-container.source-system .log-bubble.effect-info,
.log-entry-container.source-script .log-bubble.effect-info {
     color: var(--color-text-mute);
     background-color: transparent;
     box-shadow: none;
     font-style: italic;
}

.log-bubble.effect-error {
    background-color: var(--vt-c-red-dark);
    color: white;
    font-weight: bold;
    border: none;
}

/* --- Icon/Arrow Styles --- */
.stat-arrow { display: inline-block; margin-right: 0.2em; font-weight: bold; }
.stat-arrow.up { color: var(--vt-c-green); }
.stat-arrow.down { color: var(--vt-c-red); }
.log-emoji { margin-right: 0.3em; font-size: 1.1em; line-height: 1; }

/* --- Turn Separator --- */
.log-turn-separator {
    list-style: none;
    height: 1px;
    background-color: var(--color-border-hover);
    margin: 1rem 0.5rem;
    flex-basis: 100%;
}

</style> 