<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
// Removed useGameStore as we assume attacks are on user object
// import { useGameStore } from '@/stores/game';
// Removed api import as we use store action
// import api from '@/services/api'; 
import AttackCardDisplay from './AttackCardDisplay.vue';
import AttackGrid from './AttackGrid.vue';
import AttackListMobile from './AttackListMobile.vue'; // <-- Import Mobile List
import { debounce } from 'lodash-es'; // <-- Import debounce
import ConfirmDeleteModal from './ConfirmDeleteModal.vue'; // <-- Import modal

const authStore = useAuthStore();

const user = computed(() => authStore.currentUser);

// --- State for the Editor --- 
const selectedInEditor = ref([]); // Local state for selected list
const allAvailableAttacks = ref([]); // Holds the full unfiltered list
const currentAvailableDraggable = ref([]); // Holds the list bound to draggable (filtered or full)
const searchQuery = ref(''); 

const isSaving = ref(false);
const error = ref(null);
const successMessage = ref(null);
const deletingAttackId = ref(null); // <-- Add state for delete loading
const isDeleteModalOpen = ref(false); // <-- State for modal visibility
const attackToDelete = ref(null);     // <-- State for attack being deleted

const MAX_SELECTED = 6;

// --- Computed property for Count ---
const selectedCount = computed(() => selectedInEditor.value.length);

// --- NEW: Computed property for Selected IDs Set ---
const selectedAttackIdsSet = computed(() => {
    return new Set(selectedInEditor.value.map(attack => attack.id));
});

// --- Methods ---
const initializeEditorLists = () => {
    console.log("Attempting to initialize editor lists...");
    selectedInEditor.value = [];
    allAvailableAttacks.value = [];
    currentAvailableDraggable.value = [];

    if (user.value && Array.isArray(user.value.attacks)) { 
         console.log(`User ${user.value.id} found with ${user.value.attacks.length} attacks.`);
         const allUserAttacks = [...user.value.attacks];
         const selectedIds = new Set((user.value.selected_attacks || []).map(attack => attack?.id).filter(id => id !== undefined));
         console.log("Selected IDs from store:", Array.from(selectedIds));
         const currentSelected = [];
         const currentAvailable = [];
         // Reset main lists
         allAvailableAttacks.value = [];
         currentAvailableDraggable.value = [];

         allUserAttacks.forEach(attack => {
             if (attack && typeof attack === 'object' && attack.id !== undefined) { // Basic check for valid attack object
                if (selectedIds.has(attack.id)) {
                    currentSelected.push(attack);
                } else {
                    currentAvailable.push(attack);
                }
             } else {
                console.warn("Invalid item found in user.attacks:", attack);
             }
         });
         
         // Preserve order for selected based on user.selected_attacks
         selectedInEditor.value = currentSelected.sort((a, b) => {
             const idxA = (user.value.selected_attacks || []).indexOf(a.id);
             const idxB = (user.value.selected_attacks || []).indexOf(b.id);
             const effectiveIdxA = idxA === -1 ? Infinity : idxA;
             const effectiveIdxB = idxB === -1 ? Infinity : idxB;
             return effectiveIdxA - effectiveIdxB;
         });
         
         // ***MODIFIED SORTING FOR AVAILABLE ATTACKS***
         // Sort available by acquired_at date (descending - newest first)
         // Assumes an 'acquired_at' field exists, adjust if needed.
         allAvailableAttacks.value = currentAvailable.sort((a, b) => {
            const dateA = a.acquired_at ? new Date(a.acquired_at) : 0; // Handle missing date
            const dateB = b.acquired_at ? new Date(b.acquired_at) : 0; // Handle missing date
            return dateB - dateA; // Descending order
         });
         // Initialize the draggable list (apply filter if needed)
         filterAvailableAttacks(); 
         console.log(`Initialized selectedInEditor with ${selectedInEditor.value.length} items.`);
         console.log(`Initialized availableInEditor with ${currentAvailableDraggable.value.length} items.`);

    } else {
         if(user.value) {
              console.warn("User object missing or has invalid 'attacks' array during init.");
         } else {
             console.warn("No user data available during init.");
         }
    }
};

// --- Drag and Drop Logic ---
const checkMove = (evt) => {
    // Check if the target list is the 'selectedInEditor' list
    // evt.relatedContext gives info about the list the item is being dragged into
    if (evt.relatedContext?.list === selectedInEditor.value) {
        // Allow dragging into selected only if not full
        return selectedInEditor.value.length < MAX_SELECTED;
    }
    // Allow dragging out of selected, or within/into available always
    return true; 
};

// --- NEW: Function to Apply Filter --- 
const filterAvailableAttacks = () => {
    if (!searchQuery.value) {
        currentAvailableDraggable.value = [...allAvailableAttacks.value];
    } else {
        const lowerCaseQuery = searchQuery.value.toLowerCase();
        currentAvailableDraggable.value = allAvailableAttacks.value.filter(attack => 
            attack.name.toLowerCase().includes(lowerCaseQuery) || 
            (attack.description && attack.description.toLowerCase().includes(lowerCaseQuery))
        );
    }
};

// --- Save Logic (Modified for auto-save) --- 
// Debounced save function
const debouncedSaveSelection = debounce(async () => {
    if (isSaving.value) return; // Prevent concurrent saves
    isSaving.value = true;
    error.value = null;
    successMessage.value = null;

    const selectedIds = selectedInEditor.value.map(attack => attack.id);
    // console.log("Auto-saving selection:", selectedIds);

    try {
        await authStore.updateSelectedAttacks(selectedIds);
        // successMessage.value = 'Moveset auto-saved!'; // Optional: subtle feedback?
        // setTimeout(() => successMessage.value = null, 2000);
    } catch (err) {
        console.error("Failed to auto-save moveset:", err);
        error.value = err.response?.data?.detail || 'Failed to auto-save moveset.';
        // Attempt to revert on error
        initializeEditorLists(); 
    } finally {
        isSaving.value = false;
    }
}, 1000); // Debounce for 1 second (adjust as needed)

// --- MODIFIED: Delete Handler (Opens Modal) ---
function handleDeleteAttack(attackToConfirm) {
   if (!attackToConfirm || !attackToConfirm.id || deletingAttackId.value) return;
   attackToDelete.value = attackToConfirm; // Set the attack for the modal
   isDeleteModalOpen.value = true;         // Open the modal
}

// --- NEW: Execute Actual Delete After Confirmation ---
async function executeDelete() {
    if (!attackToDelete.value || !attackToDelete.value.id) return;
    if (deletingAttackId.value) return; // Prevent double clicks

    deletingAttackId.value = attackToDelete.value.id;
    error.value = null; 
    authStore.actionError = null; 
    authStore.actionSuccessMessage = null;
    isDeleteModalOpen.value = false; // Close modal immediately

    try {
        await authStore.deleteAttack(attackToDelete.value.id);
        successMessage.value = `Attack "${attackToDelete.value.name}" deleted.`;
        setTimeout(() => successMessage.value = null, 3000);
        initializeEditorLists(); // Refresh lists
    } catch (err) {
        console.error("Deletion failed:", err);
        // Error message should be set in authStore.actionError
    } finally {
        deletingAttackId.value = null;
        attackToDelete.value = null; // Clear the attack being deleted
    }
}

// --- NEW: Close Modal Handler ---
function closeDeleteModal() {
    isDeleteModalOpen.value = false;
    attackToDelete.value = null;
}

// --- Lifecycle --- 
onMounted(() => {
    initializeEditorLists();
});

// --- Watchers --- 

// Watch for changes in the EDITOR's selected list and trigger auto-save
watch(selectedInEditor, (newValue, oldValue) => {
    // Avoid saving on initial load or if lists are programmatically reset
    if (oldValue && oldValue.length > 0 && JSON.stringify(newValue) !== JSON.stringify(oldValue)) {
        debouncedSaveSelection();
    }
}, { deep: true });

// Watch for EXTERNAL changes from the store (e.g., after a failed save revert)
watch(() => user.value?.selected_attacks, (newSelection, oldSelection) => {
    // Convert both to comparable format (e.g., sorted array of IDs)
    const storeIds = (newSelection || []).map(a => a?.id).filter(id => id !== undefined).sort();
    const editorIds = selectedInEditor.value.map(a => a?.id).filter(id => id !== undefined).sort();

    if (JSON.stringify(storeIds) !== JSON.stringify(editorIds)) {
        // console.log("Store selected_attacks changed externally or after error, re-initializing editor lists.");
        initializeEditorLists();
    }
}, { deep: true }); 

// Watch for changes in all known attacks (unchanged)
watch(() => user.value?.attacks, (newAttacks, oldAttacks) => {
     if (JSON.stringify(newAttacks || []) !== JSON.stringify(oldAttacks || [])) {
        initializeEditorLists();
     }
}, { deep: true });

// Watch Search Query (unchanged)
watch(searchQuery, () => {
    filterAvailableAttacks();
});

// --- Mobile Click Handlers ---

function handleMobileSelect(attack) {
  // Check if we can add more
  if (selectedInEditor.value.length >= MAX_SELECTED) {
    error.value = `You can only select up to ${MAX_SELECTED} attacks.`;
    setTimeout(() => error.value = null, 3000); // Clear error after 3s
    return;
  }

  // Find and remove from available (both all and draggable)
  const indexInAll = allAvailableAttacks.value.findIndex(a => a.id === attack.id);
  if (indexInAll > -1) {
    allAvailableAttacks.value.splice(indexInAll, 1);
  }
  const indexInDraggable = currentAvailableDraggable.value.findIndex(a => a.id === attack.id);
  if (indexInDraggable > -1) {
    currentAvailableDraggable.value.splice(indexInDraggable, 1);
  }

  // Add to selected
  selectedInEditor.value.push(attack);
  // Trigger debounced save (already watched, but call explicitly for immediate feedback if desired)
  // debouncedSaveSelection(); 
}

function handleMobileDeselect(attack) {
  // Find and remove from selected
  const indexInSelected = selectedInEditor.value.findIndex(a => a.id === attack.id);
  if (indexInSelected > -1) {
    selectedInEditor.value.splice(indexInSelected, 1);

    // Add back to the main available list (sorted? TBD - let's just add)
    // Consider sorting logic if needed later
    allAvailableAttacks.value.push(attack); 
    // Re-apply filter to potentially add it back to the visible draggable list
    filterAvailableAttacks(); 
    // Trigger debounced save (already watched)
    // debouncedSaveSelection(); 
  }
}

</script>

<template>
  <div class="moveset-manager">

    <!-- Error/Success Messages -->
    <div v-if="error || authStore.actionError" class="error-message">
        {{ error || authStore.actionError }}
    </div>
     <div v-if="successMessage || authStore.actionSuccessMessage" class="success-message">
        {{ successMessage || authStore.actionSuccessMessage }}
    </div>
     <div v-if="deletingAttackId" class="loading-placeholder">
          Deleting attack...
     </div>

    <div class="manager-layout">
        <!-- Selected Attacks Column -->
        <div class="attack-column selected-column">
             <!-- Desktop Grid -->
             <div class="attack-display-desktop">
            <AttackGrid
                mode="drag"
                :attacks="selectedInEditor"
                v-model:draggableModel="selectedInEditor"
                groupName="attacks"
                class="selected-attack-grid selected-attacks-fixed-3"
                :dragOptions="{ ghostClass: 'ghost' }" 
                :move="checkMove"
                :allowDeletion="false" 
            >
                <template #empty>
                    <div class="empty-list-message">Drag attacks here to select (Max {{ MAX_SELECTED }}).</div>
                </template>
            </AttackGrid>
             </div>
             <!-- Mobile List -->
             <div class="attack-display-mobile">
                 <AttackListMobile
                     :attacks="selectedInEditor"
                     mode="action" 
                     @attackClick="handleMobileDeselect"
                     :allowDeletion="false" 
                 >
                     <template #empty>
                        <div class="empty-list-message">No attacks selected.</div>
                    </template>
                 </AttackListMobile>
             </div>
        </div>
        
        <!-- Available Attacks Column -->
        <div class="attack-column available-column">
            <h3>Available Attacks</h3>
            
            <!-- ADD Search Input -->
            <div class="search-bar-container">
              <input 
                type="search" 
                v-model="searchQuery" 
                placeholder="Search available attacks..." 
                class="search-input"
              />
            </div>

            <!-- Desktop Grid -->
            <div class="attack-display-desktop">
             <AttackGrid
                 mode="drag"
                 :attacks="currentAvailableDraggable"
                 v-model:draggableModel="currentAvailableDraggable"
                 groupName="attacks"
                 class="available-attack-grid"
                 :dragOptions="{ ghostClass: 'ghost', filter: '.filtered-out' }"
                 :move="checkMove" 
                 :allowDeletion="true" 
                 @deleteAttack="handleDeleteAttack" 
             >
                 <template #empty>
                     <div class="empty-list-message">
                       {{ searchQuery ? 'No attacks match your search.' : 'No more attacks available.' }}
                    </div>
                </template>
             </AttackGrid>
            </div>
            <!-- Mobile List -->
            <div class="attack-display-mobile">
                 <AttackListMobile
                     :attacks="currentAvailableDraggable"
                     mode="action"
                     @attackClick="handleMobileSelect"
                     :disabledIds="selectedAttackIdsSet"
                     :allowDeletion="true" 
                     @deleteAttack="handleDeleteAttack" 
                 >
                     <template #empty>
                         <div class="empty-list-message">
                         {{ searchQuery ? 'No attacks match your search.' : 'No more attacks available.' }}
                        </div>
                    </template>
                 </AttackListMobile>
             </div>
        </div>

    </div>

    <!-- Confirmation Modal -->
    <ConfirmDeleteModal 
        :isOpen="isDeleteModalOpen" 
        :attack="attackToDelete" 
        @update:isOpen="isDeleteModalOpen = $event" 
        @confirm="executeDelete"
    />

  </div>
</template>

<style scoped>
.moveset-manager {
  padding: 1rem 0; /* Add some vertical padding */
}

.moveset-manager h2 {
    text-align: center;
    margin-bottom: 1.5rem;
    color: var(--color-heading);
}

.manager-layout {
    display: grid;
    /* grid-template-columns: 1fr 1fr; */ /* CHANGED: Remove horizontal columns */
    grid-template-columns: 1fr; /* Single column layout */
    gap: 2rem;
    margin-bottom: 1.5rem;
}

.attack-column h3 {
    text-align: center;
    margin-bottom: 1rem;
    color: var(--color-text-muted);
    font-weight: 500;
}

.attack-grid {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
  min-height: 300px; /* Ensure dropzone height */
  overflow-y: auto; /* Scroll if many attacks */
  max-height: 60vh; /* Limit height */

  /* Default to 3 columns */
  grid-template-columns: repeat(3, 1fr);
}

/* Responsive Grid Columns */
@media (max-width: 992px) {
  .attack-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .attack-grid {
    grid-template-columns: 1fr;
    /* Adjust height limits for smaller screens if needed */
     max-height: 50vh;
  }
  .manager-layout {
      grid-template-columns: 1fr; /* Stack columns on small screens */
  }
}
/* Larger screens can potentially go to 6, but let's stick to 3 max for now */
/* Or add a wider breakpoint if needed for 6 */

.attack-card-wrapper {
  /* === Styles copied from BattleView.vue .attack-card === */
  background-color: var(--color-background);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  padding: 0.8rem; /* Apply padding to the wrapper */
  text-align: center;
  min-height: 110px; 
  display: flex; 
  flex-direction: column; 
  justify-content: center; 
  align-items: center; 
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: grab;
  /* Ensure the content inside fits properly */
  overflow: hidden; 
}

.attack-card-wrapper:active {
    cursor: grabbing;
}

/* Apply hover effect to wrapper */
.attack-card-wrapper:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    border-color: var(--vt-c-indigo); 
}

.empty-list-message {
  grid-column: 1 / -1; /* Span all columns */
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-text-mute);
  font-style: italic;
}

/* Draggable Styling - Apply ghost styles to wrapper size */
.ghost {
  opacity: 0.4;
  background: var(--color-background-soft);
  border: 2px dashed var(--vt-c-indigo);
  border-radius: 8px;
  /* Ensure ghost takes up space */
  min-height: 110px; 
  box-sizing: border-box; 
  /* Hide card content inside ghost if needed */
  /* & > * { visibility: hidden; } */
}

/* Style the element being chosen/dragged */
.sortable-chosen {
    /* Example: slight scale or brighter border */
     box-shadow: 0 5px 15px rgba(0,0,0,0.15);
     border-color: var(--vt-c-green); 
     cursor: grabbing !important;
}

/* This class is often applied to the item AND the helper clone */
.sortable-drag {
    cursor: grabbing !important;
    opacity: 0.8; /* Make the original spot slightly transparent */
}

.search-bar-container {
  margin-bottom: 1rem; /* Space below search bar */
  padding: 0 1rem; /* Align with grid padding */
}

.search-input {
  width: 100%;
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: 1px solid var(--color-border-hover);
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.95rem;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-color-translucent); /* Optional focus ring */
}

/* Style the grid components if needed */
.selected-attack-grid,
.available-attack-grid {
  /* Add any specific container styles here */
  min-height: 300px; 
  max-height: 60vh; 
}

/* Apply max-width specifically to selected grid */
.selected-attack-grid {
    max-width: 580px; /* Approx 3 cards + gaps */
    margin-left: auto; /* Center the grid container if space allows */
    margin-right: auto;
}

/* REMOVED: Force 3 columns rule */
/* 
.selected-attacks-fixed-3 .attack-grid-layout {
    grid-template-columns: repeat(3, 1fr) !important; 
}
*/

.empty-list-message {
  grid-column: 1 / -1; /* Span all columns */
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-text-mute);
  font-style: italic;
}

/* Draggable Styling - Apply ghost styles to wrapper size */
.ghost {
  opacity: 0.4;
  background: var(--color-background-soft);
  border: 2px dashed var(--vt-c-indigo);
  border-radius: 8px;
  /* Ensure ghost takes up space */
  min-height: 110px; 
  box-sizing: border-box; 
  /* Hide card content inside ghost if needed */
  /* & > * { visibility: hidden; } */
}

/* Style the element being chosen/dragged */
.sortable-chosen {
    /* Example: slight scale or brighter border */
     box-shadow: 0 5px 15px rgba(0,0,0,0.15);
     border-color: var(--vt-c-green); 
     cursor: grabbing !important;
}

/* This class is often applied to the item AND the helper clone */
.sortable-drag {
    cursor: grabbing !important;
    opacity: 0.8; /* Make the original spot slightly transparent */
}

/* Add Saving Indicator Style */
.saving-indicator {
  text-align: right;
  font-style: italic;
  color: var(--color-text-mute);
  font-size: 0.9em;
  margin-bottom: 0.5rem; /* Adjust spacing */
  height: 1.2em; /* Reserve space to prevent layout shift */
}
.saving-indicator span {
    display: inline-block;
    animation: spin 1s linear infinite;
    margin-right: 0.3em;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* --- Responsive Display Toggle --- */
.attack-display-mobile {
    display: none; /* Hidden by default */
}

@media (max-width: 768px) { /* Or your preferred mobile breakpoint */
    .attack-display-desktop {
        display: none; /* Hide grid on mobile */
    }
    .attack-display-mobile {
        display: block; /* Show list on mobile */
    }
    /* Adjust layout if needed for mobile */
    .manager-layout {
        flex-direction: column;
    }
}

.loading-placeholder { /* Basic loading style */
   padding: 10px;
   text-align: center;
   font-style: italic;
   color: var(--color-log-system);
   background-color: var(--color-bg);
   border: 1px dashed var(--color-border);
   margin-bottom: 1rem;
}

</style> 