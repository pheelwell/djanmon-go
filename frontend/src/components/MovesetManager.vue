<script setup>
import { ref, computed, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import draggable from 'vuedraggable';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue'; // Import the new component

const authStore = useAuthStore();

// --- State ---
const user = computed(() => authStore.currentUser);

// Local copies of attack lists to manage within the component
// Initialize from store, but allow local modification before saving
const learnedAttacks = ref([]);
const selectedAttacks = ref([]);

// --- Computed ---
const isLoading = computed(() => authStore.isUpdatingMoveset);
const error = computed(() => authStore.movesetUpdateError);

// Filtered list of learned attacks NOT currently selected (available to drag)
// *Important*: vuedraggable needs a writable ref for v-model.
// We'll manage the 'available' list locally based on the selected ones.
const availableAttacksInternal = ref([]); 

// Validation: Can the user save? (e.g., not more than 6 selected)
const canSave = computed(() => {
    return selectedAttacks.value.length <= 6 && !isLoading.value; // Add more checks later if needed
});
const saveError = computed(() => {
    if (selectedAttacks.value.length > 6) {
        return "You can only select up to 6 attacks.";
    }
    return null; // No validation error
});

// --- Watchers ---
// Update local state if the user data in the store changes (e.g., after login/fetch)
watch(user, (newUser) => {
    if (newUser) {
        // Initialize selected attacks
        selectedAttacks.value = newUser.selected_attacks ? [...newUser.selected_attacks] : [];
        // Initialize available attacks (all learned minus selected)
        const allLearned = newUser.attacks ? [...newUser.attacks] : [];
        const selectedIds = new Set(selectedAttacks.value.map(a => a.id));
        availableAttacksInternal.value = allLearned.filter(attack => !selectedIds.has(attack.id));

    } else {
        availableAttacksInternal.value = [];
        selectedAttacks.value = [];
    }
}, { immediate: true }); // Run immediately on component mount

// Watch for changes in selectedAttacks to update availableAttacksInternal
watch(selectedAttacks, (newSelected, oldSelected) => {
    if (!user.value || !user.value.attacks) return; // Guard against initial null state

    const allLearned = [...user.value.attacks];
    const selectedIds = new Set(newSelected.map(a => a.id));
    availableAttacksInternal.value = allLearned.filter(attack => !selectedIds.has(attack.id));

}, { deep: true }); // deep watch might be needed if item properties change

// --- Methods ---

// Save the currently selected moveset
async function saveMoveset() {
    if (!canSave.value || saveError.value) {
        console.error("Cannot save:", saveError.value || "Unknown reason");
        return; 
    }

    const selectedIds = selectedAttacks.value.map(attack => attack.id);
    await authStore.updateSelectedAttacks(selectedIds);
    // Optionally: close modal on success? show success message?
    // Error handling is shown via computed `error` property
}

</script>

<template>
  <div class="moveset-manager">
    <h2>Manage Moveset</h2>

    <div v-if="error" class="error-message">
        Error saving moveset: {{ error.detail || 'Please try again.' }}
    </div>
     <div v-if="saveError" class="error-message validation-error">
        {{ saveError }}
    </div>

    <div class="lists-container">
      <!-- Available Attacks -->
      <div class="list-section">
        <h3>Available Attacks</h3>
        <draggable
            v-model="availableAttacksInternal"
            group="attacks"
            item-key="id"
            class="attack-list available-list"
            ghost-class="ghost-card"
            drag-class="dragging-card"
            tag="ul" >
            <template #item="{element}">
                <li class="attack-card">
                   <AttackCardDisplay :attack="element" />
                </li>
            </template>
            <template #header>
                 <div v-if="availableAttacksInternal.length === 0" class="empty-list-message">No more attacks to select.</div>
            </template>
        </draggable>
      </div>

      <!-- Selected Attacks -->
      <div class="list-section">
        <h3>Selected Attacks ({{ selectedAttacks.length }}/6)</h3>
         <draggable
            v-model="selectedAttacks"
            group="attacks"
            item-key="id"
            class="attack-list selected-list"
            ghost-class="ghost-card"
            drag-class="dragging-card"
            tag="ul" >
            <template #item="{element}">
                <li class="attack-card">
                   <AttackCardDisplay :attack="element" />
                </li>
            </template>
            <template #header>
                 <div v-if="selectedAttacks.length === 0" class="empty-list-message">Drag attacks here!</div>
            </template>
        </draggable>
      </div>
    </div>

    <button @click="saveMoveset" :disabled="!canSave || isLoading" class="button button-primary save-button">
      {{ isLoading ? 'Saving...' : 'Save Moveset' }}
    </button>

  </div>
</template>

<style scoped>
.moveset-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 600px; /* Ensure minimum width */
}

.lists-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.list-section {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  background-color: var(--color-background-soft);
}

.list-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  text-align: center;
   border-bottom: 1px solid var(--color-border-hover);
   padding-bottom: 0.5rem;
}

.attack-list {
  min-height: 250px;
  max-height: 45vh;
  overflow-y: auto;
  background-color: var(--color-background-mute);
  border-radius: 6px;
  padding: 0.8rem;
}

.attack-list ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.8rem;
    min-height: 50px;
}

.attack-card {
    background-color: var(--color-background);
    border: 1px solid var(--color-border-hover);
    border-radius: 8px;
    padding: 0.8rem;
    text-align: center;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: grab;
}
.attack-card:active {
    cursor: grabbing;
}

.empty-list-message {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--color-text-mute);
  padding: 2rem 1rem;
  font-style: italic;
}

.save-button {
  align-self: center;
  padding: 0.8rem 2rem;
}

.error-message {
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
  border: 1px solid var(--vt-c-red);
  padding: 0.8rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  text-align: center;
}
.validation-error {
     background-color: var(--vt-c-yellow-soft);
     color: var(--vt-c-yellow-darker);
     border-color: var(--vt-c-yellow);
}

.ghost-card {
  opacity: 0.5;
  background: #c8ebfb;
  border: 1px dashed var(--vt-c-indigo);
  border-radius: 8px;
  min-height: 110px;
}

.dragging-card {
    background-color: var(--color-background);
    border: 1px solid var(--vt-c-indigo);
    border-radius: 8px;
    padding: 0.8rem;
    text-align: center;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    transform: rotate(2deg);
    animation: wiggle 0.3s infinite ease-in-out;
    cursor: grabbing;
}

@keyframes wiggle {
  0% { transform: rotate(-2deg); }
  50% { transform: rotate(2deg); }
  100% { transform: rotate(-2deg); }
}

.attack-list.sortable-chosen {
    /* You might not need this if ghost-class is sufficient */
}
.attack-list.sortable-drag {
     /* You might not need this if drag-class is sufficient */
}

</style> 