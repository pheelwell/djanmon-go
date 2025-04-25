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

    <!-- Controls -->
    <div class="controls">
        <div class="status">
            <span v-if="saveError" class="error">Error: {{ saveError }}</span>
             <span v-else-if="isValid" class="valid">Total: {{ currentSum }}/{{ TARGET_SUM }}</span>
             <span v-else class="invalid">Total: {{ currentSum }}/{{ TARGET_SUM }}</span>
        </div>
        <div class="buttons">
            <button @click="handleReset" :disabled="!statsChanged || isSaving" class="btn btn-secondary">Reset</button>
            <button @click="handleSave" :disabled="!isValid || !statsChanged || isSaving" class="btn btn-primary">{{ saveButtonText }}</button>
        </div>
    </div>
  </div>
</template>

<style scoped>
.stats-editor {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: var(--border-width) dashed var(--color-border);
  font-family: var(--font-primary);
}

.stat-bars-editable {
    display: flex;
    flex-direction: column;
    gap: 12px; /* Adjust gap */
    margin-bottom: 20px;
}

.stat-bar-group {
    display: flex;
    align-items: center;
    gap: 10px;
}

.stat-bar-group label {
    flex-basis: 100px; /* Fixed width for labels */
    flex-shrink: 0;
    text-align: right;
    font-size: 0.9em;
    color: var(--color-text);
    text-transform: uppercase;
}

.bar-track {
    flex-grow: 1;
    height: 20px; /* Bar height */
    background-color: var(--color-bg); /* Dark track */
    border: 1px solid var(--color-border);
    border-radius: 0; /* No rounded corners */
    position: relative;
    cursor: grab; /* Indicate draggable */
    overflow: hidden; /* Hide overflow for fill */
    box-shadow: inset 1px 1px 0px rgba(0,0,0,0.5); /* Inner shadow */
}

.bar-fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background-color: var(--color-text); /* Default fill color */
    border-radius: 0;
    pointer-events: none; /* Prevent fill from stealing clicks */
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.1); /* Inner highlight */
}

/* --- Stat Specific Colors --- */
.bar-fill.hp { background-color: var(--color-hp-high); }
.bar-fill.attack { background-color: var(--color-accent); } /* Red */
.bar-fill.defense { background-color: var(--color-momentum-user); } /* Blue */
.bar-fill.speed { background-color: var(--color-hp-medium); } /* Yellow */

.handle {
    position: absolute;
    right: -6px; /* Position handle slightly outside */
    top: 50%;
    transform: translateY(-50%);
    width: 10px; /* Handle width */
    height: 24px; /* Handle height */
    background-color: var(--color-text); /* Handle color */
    border: 1px solid var(--color-border);
    border-radius: 0; /* No rounded corners */
    cursor: grab;
    z-index: 2;
    box-shadow: 1px 1px 0px var(--color-border); /* Pixel shadow */
    pointer-events: auto; /* Allow handle to be grabbed */
}

.handle:active {
    cursor: grabbing;
    background-color: var(--color-accent-secondary);
}

.controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 15px;
    padding-top: 15px;
    border-top: var(--border-width) dashed var(--color-border);
}

.status span {
    font-size: 0.9em;
    font-weight: normal;
}

.status .valid {
    color: var(--color-hp-high);
}
.status .invalid {
    color: var(--color-accent);
}
.status .error {
    color: var(--color-accent);
    font-weight: bold;
}

.buttons {
    display: flex;
    gap: 10px;
}

/* Apply base btn styles, assume they exist globally */
.btn {
    /* Assuming base styles are in main.css or similar */
}

.btn-secondary {
     background-color: var(--color-log-system);
     color: var(--color-bg);
     border-color: var(--color-border);
}
.btn-secondary:hover:not(:disabled) {
    background-color: var(--color-text);
    color: var(--color-bg);
}

.btn-primary {
    /* Base theme button uses accent-secondary, which is fine */
}

</style> 