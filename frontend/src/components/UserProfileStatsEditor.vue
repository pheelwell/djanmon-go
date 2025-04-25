<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia'; // <-- Import storeToRefs
// import api from '@/services/api'; // <-- Remove direct API import

const authStore = useAuthStore();
const user = computed(() => authStore.currentUser);

// Get reactive state and actions from the store
const { isUpdatingStats, statsUpdateError } = storeToRefs(authStore);
const { updateUserStats, fetchUserProfile } = authStore;

// --- Component State ---
const hp = ref(100);
const attack = ref(100);
const defense = ref(100);
const speed = ref(100);

const isSaving = isUpdatingStats; // <-- Use store's loading state
const saveError = statsUpdateError; // <-- Use store's error state
const statsChanged = ref(false);

const TARGET_SUM = 400;
const STAT_INCREMENT = 10;
const MIN_STAT_VALUE = 10; // Match backend validation

const startValue = ref(0);
const barWidth = ref(0); // To calculate delta based on bar width
const statRefs = { hp, attack, defense, speed }; // Map names to refs

// --- Template Refs for Bar Elements ---
const hpBarRef = ref(null);
const attackBarRef = ref(null);
const defenseBarRef = ref(null);
const speedBarRef = ref(null);

// --- Computed Properties ---
const currentSum = computed(() => {
    // Ensure values are numbers before summing
    return (Number(hp.value) || 0) +
           (Number(attack.value) || 0) +
           (Number(defense.value) || 0) +
           (Number(speed.value) || 0);
});

const isValid = computed(() => {
    const numHp = Number(hp.value);
    const numAttack = Number(attack.value);
    const numDefense = Number(defense.value);
    const numSpeed = Number(speed.value);

    return currentSum.value === TARGET_SUM &&
           numHp >= MIN_STAT_VALUE && numAttack >= MIN_STAT_VALUE &&
           numDefense >= MIN_STAT_VALUE && numSpeed >= MIN_STAT_VALUE &&
           numHp % STAT_INCREMENT === 0 && numAttack % STAT_INCREMENT === 0 &&
           numDefense % STAT_INCREMENT === 0 && numSpeed % STAT_INCREMENT === 0;
});

// --- Methods ---
const initializeStats = () => {
    if (user.value) {
        hp.value = user.value.hp || 100;
        attack.value = user.value.attack || 100;
        defense.value = user.value.defense || 100;
        speed.value = user.value.speed || 100;
    }
    statsChanged.value = false;
    saveError.value = null;
};

const calculateBarWidth = (barElement) => {
    if (barElement) {
        barWidth.value = barElement.offsetWidth;
    }
};

const startDrag = (statName, event, barElement) => {
    draggingStat.value = statName;
    calculateBarWidth(barElement); // Ensure we have the width

    startX.value = event.clientX || event.touches[0].clientX;
    startValue.value = Number(statRefs[statName].value);

    // Add listeners to the window
    window.addEventListener('mousemove', handleDrag);
    window.addEventListener('mouseup', stopDrag);
    window.addEventListener('touchmove', handleDrag, { passive: false }); // Prevent scroll on touch
    window.addEventListener('touchend', stopDrag);
};

const handleDrag = (event) => {
    if (!draggingStat.value || !barWidth.value) return;
    event.preventDefault(); // Prevent text selection/scrolling

    const currentX = event.clientX || event.touches[0].clientX;
    const deltaX = currentX - startX.value;

    // --- Calculate Stat Change --- 
    // Determine max possible value for a single stat (TARGET_SUM - 3 * MIN_STAT_VALUE)
    const maxSingleStatValue = TARGET_SUM - (MIN_STAT_VALUE * 3);
    // Map bar width to the range of possible stat points (MIN_STAT_VALUE to maxSingleStatValue)
    const pointsPerPixel = (maxSingleStatValue - MIN_STAT_VALUE) / barWidth.value;
    let deltaValue = Math.round(deltaX * pointsPerPixel); // Raw change in points

    // Snap to increment
    deltaValue = Math.round(deltaValue / STAT_INCREMENT) * STAT_INCREMENT;

    let proposedValue = startValue.value + deltaValue;

    // --- Clamp proposedValue based on overall constraints ---
    const otherStatsMinSum = MIN_STAT_VALUE * 3;
    proposedValue = Math.max(MIN_STAT_VALUE, proposedValue); // Ensure min for dragged stat
    proposedValue = Math.min(TARGET_SUM - otherStatsMinSum, proposedValue); // Ensure others can meet min
    proposedValue = Math.round(proposedValue / STAT_INCREMENT) * STAT_INCREMENT;

    // Only update the dragged stat directly
    if (statRefs[draggingStat.value].value !== proposedValue) {
        statRefs[draggingStat.value].value = proposedValue;
        statsChanged.value = true;
    }
};

const stopDrag = () => {
    draggingStat.value = null;
    // Remove listeners from the window
    window.removeEventListener('mousemove', handleDrag);
    window.removeEventListener('mouseup', stopDrag);
    window.removeEventListener('touchmove', handleDrag);
    window.removeEventListener('touchend', stopDrag);
};

const handleSave = async () => {
    if (!isValid.value) return;

    // isSaving.value = true; // Handled by store
    // saveError.value = null; // Handled by store

    const statsData = {
        hp: hp.value,
        attack: attack.value,
        defense: defense.value,
        speed: speed.value
    };

    try {
        // Call the store action
        await updateUserStats(statsData); 
        // fetchUserProfile is now handled implicitly by updateUserStats on success
        // await authStore.fetchUserProfile(); 
        statsChanged.value = false; 
    } catch (err) {
        // Error is now handled and stored in statsUpdateError by the store action
        console.error("Error saving stats (caught in component, should be handled by store):", err); 
        // saveError.value = ...; // No need to set here
    } finally {
        // isSaving.value = false; // Handled by store
    }
};

const handleReset = () => {
    initializeStats();
};

// --- Lifecycle Hooks / Watchers ---
onMounted(() => {
    initializeStats();
});

// Re-initialize if the user data changes in the store (e.g., after login)
watch(user, () => {
    initializeStats();
}, { immediate: true }); // immediate might be redundant with onMounted

// Define emits
const emit = defineEmits(['close']);

// --- NEW: Drag State ---
const draggingStat = ref(null); // 'hp', 'attack', 'defense', 'speed'
const startX = ref(0);

// --- Computed property for Save Button Text (Uses store's isSaving) ---
const saveButtonText = computed(() => {
    if (isSaving.value) { // Check store's loading state first
        return 'Saving...';
    }
    if (isValid.value) {
        return 'Save';
    }
    const diff = TARGET_SUM - currentSum.value;
    const sign = diff > 0 ? '+' : '';
    return `Save (${sign}${diff} points)`; 
});

</script>

<template>
  <div class="stats-editor">
    <!-- Removed Title and Instructions -->
    <!-- Draggable Bars -->
    <div class="stat-bars-editable">
        <!-- HP Bar -->
        <div class="stat-bar-group">
            <label>HP: {{ hp }}</label>
            <div class="bar-track" ref="hpBarRef">
                 <div class="bar-fill hp" :style="{ width: (hp / (TARGET_SUM - MIN_STAT_VALUE * 3)) * 100 + '%' }">
                     <div 
                        class="handle"
                        @mousedown.prevent="startDrag('hp', $event, hpBarRef)"
                        @touchstart.prevent="startDrag('hp', $event, hpBarRef)"
                     ></div>
                </div>
            </div>
        </div>
        <!-- Attack Bar -->
        <div class="stat-bar-group">
            <label>Attack: {{ attack }}</label>
             <div class="bar-track" ref="attackBarRef">
                 <div class="bar-fill attack" :style="{ width: (attack / (TARGET_SUM - MIN_STAT_VALUE * 3)) * 100 + '%' }">
                     <div 
                        class="handle" 
                        @mousedown.prevent="startDrag('attack', $event, attackBarRef)"
                        @touchstart.prevent="startDrag('attack', $event, attackBarRef)"
                    ></div>
                </div>
            </div>
        </div>
        <!-- Defense Bar -->
        <div class="stat-bar-group">
            <label>Defense: {{ defense }}</label>
            <div class="bar-track" ref="defenseBarRef">
                 <div class="bar-fill defense" :style="{ width: (defense / (TARGET_SUM - MIN_STAT_VALUE * 3)) * 100 + '%' }">
                    <div 
                        class="handle" 
                        @mousedown.prevent="startDrag('defense', $event, defenseBarRef)"
                        @touchstart.prevent="startDrag('defense', $event, defenseBarRef)"
                    ></div>
                </div>
            </div>
        </div>
        <!-- Speed Bar -->
        <div class="stat-bar-group">
            <label>Speed: {{ speed }}</label>
             <div class="bar-track" ref="speedBarRef">
                 <div class="bar-fill speed" :style="{ width: (speed / (TARGET_SUM - MIN_STAT_VALUE * 3)) * 100 + '%' }">
                    <div 
                        class="handle" 
                        @mousedown.prevent="startDrag('speed', $event, speedBarRef)"
                        @touchstart.prevent="startDrag('speed', $event, speedBarRef)"
                    ></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Removed Summary Text -->
    <!-- <div class="summary"> ... </div> -->

    <div class="actions">
        <!-- Button is only visible if statsChanged is true -->
        <button 
            v-if="statsChanged"
            @click="handleSave"
            :disabled="!isValid || isSaving" 
            class="button button-primary save-button"
            :class="{ 'is-invalid': !isValid, 'is-valid': isValid }" 
        >
            <!-- Use store's isSaving -->
            <span v-if="isSaving">Saving...</span>
            <span v-else-if="isValid">Save Stats</span>
            <span v-else>{{ TARGET_SUM - currentSum }} points</span>
        </button>
        
        <!-- Show reset only if changes were made -->
        <button v-if="statsChanged" @click="handleReset" :disabled="isSaving" class="button button-secondary icon-button" title="Reset Stats">
            🔄 
        </button>
    </div>

    <!-- Use store's saveError -->
    <div v-if="saveError" class="error-message">Error: {{ saveError.detail || saveError }}</div>
    <!-- Removed saveSuccess message display -->

  </div>
</template>

<style scoped>
.stats-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.instructions {
  font-size: 0.9em;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.stat-bars-editable {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 1rem;
    user-select: none; /* Prevent text selection during drag */
}

.stat-bar-group {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.stat-bar-group label {
    font-weight: bold;
    width: 80px; /* Fixed width */
    text-align: right;
    flex-shrink: 0;
    white-space: nowrap; /* ADDED: Prevent line break */
}

.bar-track {
    flex-grow: 1;
    height: 20px; /* Make bars taller */
    background-color: var(--color-background-mute);
    border-radius: 10px;
    border: 1px solid var(--color-border);
    position: relative;
    cursor: grab;
}

.bar-track:active {
    cursor: grabbing;
}

.bar-fill {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    border-radius: 10px;
    background-color: var(--color-primary); /* Default fill */
    display: flex; /* To position handle */
    align-items: center; /* Center handle vertically */
    justify-content: flex-end; /* Position handle at the end */
}

.bar-fill.hp { background-color: var(--vt-c-green); }
.bar-fill.attack { background-color: var(--vt-c-red); }
.bar-fill.defense { background-color: var(--vt-c-blue); }
.bar-fill.speed { background-color: var(--vt-c-yellow); }

.handle {
    width: 10px; /* Width of the handle */
    height: 120%; /* Make handle slightly taller than bar */
    background-color: rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(0, 0, 0, 0.3);
    border-radius: 3px;
    cursor: ew-resize; /* East-west resize cursor */
    position: relative; /* Allows fine-tuning if needed */
    right: -5px; /* Center the handle visually over the end */
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.summary {
  margin-top: 0.5rem;
  font-weight: bold;
}

.summary .valid {
    color: var(--color-success);
}
.summary .invalid {
    color: var(--color-danger);
}
.validation-error {
    font-size: 0.85em;
    font-weight: normal;
    color: var(--color-danger);
    margin-left: 10px;
}

.actions {
    margin-top: 1rem;
    display: flex;
    gap: 1rem;
    justify-content: flex-end; /* Align buttons to the right */
}

.error-message {
    color: var(--color-danger);
    margin-top: 0.5rem;
}

/* Import button styles if not global */
.button {
  /* Basic button styles */
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s ease, opacity 0.2s ease;
}

.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-primary {
  background-color: var(--color-primary);
  color: white;
}
.button-primary:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
}

/* ADDED: Explicit gray background for disabled primary button */
.button-primary:disabled {
    background-color: #555; /* Example gray color */
    opacity: 0.7; /* Adjust opacity if needed */
}

.button-secondary {
  background-color: var(--color-secondary);
  color: var(--color-text);
  border: 1px solid var(--color-border-hover);
}
.button-secondary:hover:not(:disabled) {
  background-color: var(--color-background-mute);
}

/* Style for icon button */
.icon-button {
    padding: 0.5rem; /* Adjust padding for icon */
    line-height: 1; /* Ensure icon is centered vertically */
    min-width: auto;
    font-size: 1.2em; /* Make icon slightly larger */
}

/* Make save button potentially wider to accommodate text */
.save-button {
    min-width: 120px; 
    text-align: center;
    /* Add transition for border color/shadow */
    transition: background-color 0.2s ease, opacity 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

/* Styles for validation state */
.save-button.is-valid {
    background-color: var(--color-success); /* Green background */
    border: 1px solid var(--color-success-dark);
    box-shadow: 0 0 5px rgba(var(--vt-c-green-rgb), 0.4); 
}
.save-button.is-valid:hover:not(:disabled) {
    background-color: var(--color-success-dark);
}

.save-button.is-invalid {
    border: 2px solid var(--color-danger) !important; /* Ensure red outline appears */
    background-color: var(--color-background-soft); /* Keep background subtle */
    color: var(--color-text-muted); 
    box-shadow: 0 0 5px rgba(var(--vt-c-red-rgb), 0.4); 
    opacity: 0.7; /* Make it look more disabled */
    cursor: not-allowed;
}

/* Ensure disabled overrides invalid hover state if needed */
.save-button.is-invalid:hover {
     /* Keep the invalid appearance on hover */
     background-color: var(--color-background-soft);
     color: var(--color-text-muted);
}
</style> 