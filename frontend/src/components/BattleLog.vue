<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue';

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

// --- NEW: State for expandable debug messages ---
const expandedDebugIndices = ref(new Set()); // Stores indices of *non-debug* items whose debug logs are shown

// Toggle visibility of debug messages associated with a non-debug entry
function toggleDebugMessages(index) {
    if (expandedDebugIndices.value.has(index)) {
        expandedDebugIndices.value.delete(index);
    } else {
        expandedDebugIndices.value.add(index);
    }
    // No need to force scroll here, expansion happens in place
}

// Determine if a debug entry should be shown
function shouldShowDebug(debugEntryIndex) {
    let precedingNonDebugIndex = -1;
    // Find the index of the closest *preceding* non-debug, non-separator entry
    for (let i = debugEntryIndex - 1; i >= 0; i--) {
        const entry = props.logEntries[i];
        if (entry && entry.source !== 'debug' && entry.effect_type !== 'turnchange') {
            precedingNonDebugIndex = i;
            break;
        }
    }
    return expandedDebugIndices.value.has(precedingNonDebugIndex);
}

// Check if a non-debug entry has *any* immediately following debug entries
function hasAssociatedDebug(index) {
    // Look ahead until the next non-debug entry or end of log
    for (let i = index + 1; i < props.logEntries.length; i++) {
        const nextEntry = props.logEntries[i];
        if (!nextEntry) continue; // Should not happen
        if (nextEntry.source === 'debug') {
            return true; // Found a debug entry before any other type
        }
        if (nextEntry.effect_type !== 'turnchange') {
             return false; // Found a different non-debug/non-separator entry first
        }
        // If it's a turnchange, continue looking
    }
    return false; // Reached end of log without finding debug
}

// Check if a specific non-debug entry is currently expanded
function isExpanded(index) {
    return expandedDebugIndices.value.has(index);
}
// --- END: Expandable debug messages ---

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
      <TransitionGroup 
          tag="ul" 
          name="log-item" 
          class="turn-summary-list"
      >
          <!-- Iterate directly within TransitionGroup -->
          <template v-for="(entry, index) in logEntries" :key="`${battleId}-item-${index}`">
              
              <!-- 1. Turn Separator -->
              <li v-if="entry.effect_type === 'turnchange'" 
                  class="log-turn-separator" 
                  aria-hidden="true" 
                  :key="`${battleId}-separator-${index}`" 
              >
                <hr /> <!-- Use an actual hr for semantics -->
              </li>

              <!-- 2. Debug Entry (Conditionally Rendered) -->
              <template v-else-if="entry.source === 'debug'">
                  <li v-if="shouldShowDebug(index)" 
                      :class="{
                          'log-entry-container': true,
                          'source-debug': true,
                          'log-system': true, /* Align center */
                          'log-debug-entry': true 
                      }"
                      :key="`${battleId}-debug-${index}`" 
                  >
                      <span :class="['log-bubble', 'effect-info', 'log-debug-bubble']">
                          {{ entry.text }}
                      </span>
                  </li>
              </template>

              <!-- 3. Regular Non-Debug Entry -->
              <li v-else 
                  @click="hasAssociatedDebug(index) ? toggleDebugMessages(index) : null" 
                  :class="{
                      'log-entry-container': true,
                      [`source-${entry.source || 'unknown'}`]: true,
                      'log-user': entry.source === userPlayerRole,
                      'log-opponent': entry.source !== userPlayerRole && entry.source !== 'system' && entry.source !== 'script',
                      'log-system': entry.source === 'system' || entry.source === 'script',
                      'can-expand': hasAssociatedDebug(index), 
                      'expanded': isExpanded(index) 
                  }"
                  :key="`${battleId}-entry-${index}`" 
                  :style="hasAssociatedDebug(index) ? { cursor: 'pointer' } : {}"
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
                      <!-- Icons instead of arrows for stat changes -->
                      <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod > 0" class="stat-icon up">⬆️</span>
                      <span v-if="entry.effect_type === 'stat_change' && entry.effect_details?.mod < 0" class="stat-icon down">⬇️</span>
                      <span v-if="entry.effect_type === 'action' && entry.effect_details?.emoji" class="log-emoji">{{ entry.effect_details.emoji }}</span>
                      {{ entry.text }}
                  </span>
              </li>
          </template>
      </TransitionGroup>
      <div v-if="!logEntries || logEntries.length === 0" class="empty-log-message">Battle Log Is Empty...</div>
      <div style="height: 1px; flex-shrink: 0;"></div> <!-- Ensures scroll height calculation -->
  </div>
</template>

<style scoped>
.battle-log-container {
    padding: 5px; /* Reduced padding */
    min-height: 150px; /* Adjusted min height */
    max-height: 400px;
    background-color: var(--color-bg); /* Darker background inside */
    border: 1px solid var(--color-border);
    border-radius: 0; /* No border radius */
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden; 
    font-family: var(--font-primary);
    line-height: 1.3;
}

.turn-summary-list {
    flex-grow: 1;
    list-style: none;
    padding: 0 5px; /* Inner padding */
    margin: 0;
}

.empty-log-message {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--color-log-system); /* Use system log color */
    font-style: italic;
    font-size: 1em;
    padding: 20px;
    text-transform: uppercase;
}

.log-entry-container {
    margin-bottom: 6px;
    display: flex;
}

/* Alignment by Source */
.log-entry-container.log-user { justify-content: flex-start; }
.log-entry-container.log-opponent { justify-content: flex-end; }
.log-entry-container.log-system { justify-content: center; }

.log-bubble {
    padding: 4px 8px;
    border-radius: 0; /* No rounded corners */
    max-width: 75%;
    word-wrap: break-word;
    box-shadow: none; /* Remove shadow */
    line-height: 1.3;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: 1px solid var(--color-border); /* Default border */
    transition: background-color 0.2s ease, color 0.2s ease;
    font-size: 0.9em;
}

/* Bubble Styling by Source */
.log-entry-container.source-player1 .log-bubble,
.log-entry-container.source-player2 .log-bubble {
    background-color: var(--color-panel-bg); /* Player bubbles match panel */
    color: var(--color-text); /* Player text */
    /* Distinguish user/opponent slightly? */
    /* border-color: var(--color-border-hover); */ 
}
.log-entry-container.log-user .log-bubble {
    border-left-color: var(--color-log-user); /* Accent border */
    border-left-width: 3px;
}
.log-entry-container.log-opponent .log-bubble {
    border-right-color: var(--color-log-opponent);
    border-right-width: 3px;
}

.log-entry-container.source-script .log-bubble {
    background-color: var(--color-bg); /* Darker */
    color: var(--color-log-system);
    border-color: var(--color-border);
}

.log-entry-container.source-system .log-bubble {
    color: var(--color-log-system);
    background-color: transparent;
    border: none;
    font-style: italic;
    font-size: 0.9em;
    padding: 2px 5px;
}

.log-debug-bubble {
    color: #666;
    background-color: transparent;
    border: 1px dashed #444;
    font-style: italic;
    opacity: 0.8;
    font-size: 0.8em;
    padding: 1px 4px;
}

/* Bubble Styling by Effect Type */
.log-bubble.effect-damage {
    background-color: rgba(233, 69, 96, 0.1); /* Faint red */
    color: var(--color-accent); /* Red text */
    border-color: var(--color-accent);
}

.log-bubble.effect-heal {
    background-color: rgba(53, 208, 104, 0.1); /* Faint green */
    color: var(--color-hp-high); /* Green text */
    border-color: var(--color-hp-high);
}

.log-bubble.effect-stat_change {
    background-color: var(--color-panel-bg);
    color: var(--color-text);
    border-color: var(--color-border);
}

.log-bubble.effect-status_apply,
.log-bubble.effect-status_remove,
.log-bubble.effect-status_effect {
     background-color: var(--color-panel-bg);
     color: var(--color-text);
     border-style: dashed;
     border-color: var(--color-border-hover);
}

.log-bubble.effect-info {
    /* Keep base styles */
}

.log-bubble.effect-error {
    background-color: var(--color-accent);
    color: var(--color-bg);
    font-weight: bold;
    border: none;
}

/* Icon/Arrow Styles */
.stat-icon { display: inline-block; margin-right: 3px; font-size: 1em; line-height: 1; }
.stat-icon.up { color: var(--color-stat-up); } /* Use theme colors */
.stat-icon.down { color: var(--color-stat-down); }
.log-emoji { margin-right: 4px; font-size: 1.1em; line-height: 1; }

/* Turn Separator */
.log-turn-separator {
    list-style: none;
    height: auto; /* Remove fixed height */
    margin: 10px 5px;
    padding: 0;
}
.log-turn-separator hr {
    border: none;
    border-top: 1px dashed var(--color-border);
}

/* Debug Toggle Styles */
.log-entry-container.can-expand .log-bubble {
   cursor: pointer;
}
.log-entry-container.can-expand:hover .log-bubble {
  filter: brightness(1.2);
  border-color: var(--color-accent-secondary);
}

/* Animations (Keep as is) */
.log-item-enter-active,
.log-item-leave-active {
  transition: all 0.4s ease;
}
.log-item-enter-from,
.log-item-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
.log-item-move {
  transition: transform 0.4s ease;
}

</style> 