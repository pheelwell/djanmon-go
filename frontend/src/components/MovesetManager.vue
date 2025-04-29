<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
// Removed useGameStore as we assume attacks are on user object
// import { useGameStore } from '@/stores/game';
// Removed api import as we use store action
// import api from '@/services/api'; 
// Removed AttackCardDisplay import (now only used inside AttackGrid)
import AttackGrid from './AttackGrid.vue';
// Removed AttackListMobile import
import { debounce } from 'lodash-es'; // <-- Import debounce
import ConfirmDeleteModal from './ConfirmDeleteModal.vue'; // <-- Import modal

const authStore = useAuthStore();

const user = computed(() => authStore.currentUser);

// --- State for the Editor --- 
// Removed selectedInEditor ref
const allAvailableAttacks = ref([]); // Holds the full unfiltered list
// REMOVED: const currentAvailableAttacks = ref([]); 
const selectedIds = ref([]); // <-- Holds IDs of selected attacks (bound to AttackGrid)
const searchQuery = ref(''); 
const showOnlyFavorites = ref(false); // <-- ADDED

const isSaving = ref(false);
const error = ref(null);
const successMessage = ref(null);
const deletingAttackId = ref(null); // <-- Add state for delete loading
const isDeleteModalOpen = ref(false); // <-- State for modal visibility
const attackToDelete = ref(null);     // <-- State for attack being deleted

const MAX_SELECTED = 6; // Still relevant for limiting selection

// --- Computed property for Count ---
// Removed selectedCount computed property

// --- NEW: Computed property for ALL Attack IDs Set (including favorite status) ---
// Keep allAttackInfo if needed elsewhere, otherwise remove
// const allAttackInfo = computed(() => { ... }); 

const favoriteAttackIdsSet = computed(() => {
    const ids = new Set();
    if (user.value && user.value.attacks) {
        user.value.attacks.forEach(attack => {
            if (attack && attack.id !== undefined && attack.is_favorite) {
                ids.add(attack.id);
            }
        });
    }
    return ids;
});

// --- NEW: Computed property for Selected IDs Set ---
// Removed selectedAttackIdsSet, using selectedIds ref directly

// --- Methods ---
const initializeManager = () => { // Renamed from initializeEditorLists
    console.log("Initializing Moveset Manager...");
    selectedIds.value = []; // Initialize as empty array
    allAvailableAttacks.value = [];
    // REMOVED: currentAvailableAttacks.value = [];

    if (user.value && Array.isArray(user.value.attacks)) { 
         console.log(`User ${user.value.id} found with ${user.value.attacks.length} attacks.`);
         // Keep mapping and initial sort logic
         allAvailableAttacks.value = user.value.attacks.map(a => ({ 
            ...a, 
            is_favorite: !!a.is_favorite // Ensure is_favorite exists
         })).sort((a, b) => {
             const favA = a.is_favorite ? 0 : 1;
             const favB = b.is_favorite ? 0 : 1;
             if (favA !== favB) return favA - favB; // Favorites first
             return a.name.localeCompare(b.name);
         });

         // Initialize selectedIds based on store data, ensuring they exist in the available list
        selectedIds.value = (user.value.selected_attacks || [])
                               .map(attack => attack?.id)
                               .filter(id => id !== undefined && allAvailableAttacks.value.some(a => a.id === id));

         // REMOVED: filterAvailableAttacks(); 
         console.log(`Initialized with ${allAvailableAttacks.value.length} total attacks, ${selectedIds.value.length} selected.`);

    } else {
         if(user.value) {
              console.warn("User object missing or has invalid 'attacks' array during init.");
         } else {
             console.warn("No user data available during init.");
         }
    }
};

// --- Drag and Drop Logic --- REMOVED checkMove function

// --- UPDATED: Function to Apply Filter --- 
// REMOVED: const filterAvailableAttacks = () => { // Keep this logic, but target currentAvailableAttacks

// --- Save Logic (Modified for auto-save) --- 
// Debounced save function
const debouncedSaveSelection = debounce(async () => {
    if (isSaving.value) return; // Prevent concurrent saves
    isSaving.value = true;
    error.value = null;
    // successMessage.value = null; // Keep success message maybe?

    // const selectedIdsToSave = selectedIds.value; // Use the array directly
    console.log("Auto-saving selection:", selectedIds.value);

    try {
        await authStore.updateSelectedAttacks(selectedIds.value); // Pass the array
        // successMessage.value = 'Moveset auto-saved!'; // Optional: subtle feedback?
        // setTimeout(() => successMessage.value = null, 2000);
    } catch (err) {
        console.error("Failed to auto-save moveset:", err);
        error.value = err.response?.data?.detail || 'Failed to auto-save moveset.';
        // Attempt to revert on error
        initializeManager(); // Re-initialize from store
    } finally {
        isSaving.value = false;
    }
}, 1000); // Debounce for 1 second (adjust as needed)

// --- UPDATED: Handle Toggle Favorite --- 
async function handleToggleFavorite(attackId) { // Keep existing logic
    if (!attackId) return;
    const attackInAllIndex = allAvailableAttacks.value.findIndex(a => a.id === attackId);
    let originalFavoriteStatus = null;

    // Optimistic UI update
    if (attackInAllIndex !== -1) {
        originalFavoriteStatus = allAvailableAttacks.value[attackInAllIndex].is_favorite;
        allAvailableAttacks.value[attackInAllIndex].is_favorite = !originalFavoriteStatus;
        console.log(`Optimistically toggled favorite for ${attackId} to ${!originalFavoriteStatus}`);

        // Re-sort the main list after optimistic toggle
        allAvailableAttacks.value.sort((a, b) => {
            const favA = a.is_favorite ? 0 : 1;
            const favB = b.is_favorite ? 0 : 1;
            if (favA !== favB) return favA - favB;
            return a.name.localeCompare(b.name);
        });

        // Re-apply filters immediately to update the view
        // REMOVED: filterAvailableAttacks();
    } else {
        console.warn(`Attack ID ${attackId} not found in allAvailableAttacks for optimistic update.`);
    }
    
    try {
        await authStore.toggleAttackFavorite(attackId);
        // Success message handled by store, data updated reactively
    } catch (err) { // Revert optimistic update on error
        console.error("Failed to toggle favorite via store, reverting UI:", err);
        if (attackInAllIndex !== -1 && originalFavoriteStatus !== null) {
            allAvailableAttacks.value[attackInAllIndex].is_favorite = originalFavoriteStatus; // Revert
            
            // Re-sort again after reverting
            allAvailableAttacks.value.sort((a, b) => {
                 const favA = a.is_favorite ? 0 : 1;
                 const favB = b.is_favorite ? 0 : 1;
                 if (favA !== favB) return favA - favB;
                 return a.name.localeCompare(b.name);
            });
            // Re-apply filters again after reverting
            // REMOVED: filterAvailableAttacks();
        }
        // Error message handled by store
    }
}

// --- MODIFIED: Delete Handler (Opens Modal) ---
function handleDeleteAttack(attackToConfirm) { // Keep existing logic
   if (!attackToConfirm || !attackToConfirm.id || deletingAttackId.value) return;
   attackToDelete.value = attackToConfirm; // Set the attack for the modal
   isDeleteModalOpen.value = true;         // Open the modal
}

// --- NEW: Execute Actual Delete After Confirmation ---
async function executeDelete() { // Keep existing logic, but ensure it re-initializes
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
        // Explicitly re-initialize after successful deletion
        initializeManager(); // <-- ADD THIS LINE
    } catch (err) {
        console.error("Deletion failed:", err);
        // Error message should be set in authStore.actionError
    } finally {
        deletingAttackId.value = null;
        attackToDelete.value = null; // Clear the attack being deleted
    }
}

// --- NEW: Close Modal Handler ---
function closeDeleteModal() { // Keep existing logic
    isDeleteModalOpen.value = false;
    attackToDelete.value = null;
}

// --- Lifecycle --- 
onMounted(() => {
    initializeManager(); // Use new init function name
});

// --- Watchers --- 

// Watch for changes in the EDITOR's selected list and trigger auto-save
watch(selectedIds, (newValue, oldValue) => { // Watch selectedIds ref
    // Avoid saving on initial load or if lists are programmatically reset
    // Check specifically for changes initiated by user interaction (not store sync)
     if (oldValue && JSON.stringify(newValue) !== JSON.stringify(oldValue)) {
        // Check against max limit (AttackGrid should handle this, but double check)
        if (newValue.length > MAX_SELECTED) {
           console.warn(`Selection limit exceeded (${newValue.length}/${MAX_SELECTED}). This shouldn't happen if AttackGrid is working correctly.`);
           // Potentially force slice? For now, assume AttackGrid prevents this.
           // selectedIds.value = newValue.slice(0, MAX_SELECTED); // Force limit if needed
        }
        console.log("Selected IDs changed locally, triggering auto-save.", newValue);
        // The computed property will update automatically, no need to call filter func
        debouncedSaveSelection();
    }
}, { deep: true });

// Watch for EXTERNAL changes from the store (e.g., after a failed save revert)
watch(() => user.value?.selected_attacks, (newSelectionInStore, oldSelectionInStore) => {
    // Convert both to comparable format (e.g., sorted array of IDs)
    const storeIds = (newSelectionInStore || []).map(a => a?.id).filter(id => id !== undefined).sort();
    const editorIds = [...selectedIds.value].sort(); // Use local selectedIds ref

    if (JSON.stringify(storeIds) !== JSON.stringify(editorIds)) {
        console.log("Store selected_attacks changed externally or after error, re-initializing manager.");
        initializeManager(); // Re-sync local state
    }
}, { deep: true }); 

// The watcher for user.value.attacks should trigger re-initialization
watch(() => user.value?.attacks, (newAttacks, oldAttacks) => {
     // Keep existing comparison logic
     const newAttacksSimple = (newAttacks || []).map(a => ({id: a.id, name: a.name, is_favorite: a.is_favorite}));
     const oldAttacksSimple = (oldAttacks || []).map(a => ({id: a.id, name: a.name, is_favorite: a.is_favorite}));
     if (JSON.stringify(newAttacksSimple) !== JSON.stringify(oldAttacksSimple)) {
        console.log("User attacks changed in store, re-initializing manager lists..."); // Debug log
        initializeManager(); // Re-initialize fully
     }
}, { deep: true });

// REMOVED watchers for searchQuery and showOnlyFavorites (now dependencies of computed prop)

// --- NEW Computed property for the displayed grid data ---
const filteredAndSortedAttacks = computed(() => {
    console.log(`Recalculating filtered/sorted attacks. Selected: [${selectedIds.value.join(', ')}]`);
    let filtered = [...allAvailableAttacks.value]; 

    // --- 1. Apply Filters ---
    if (showOnlyFavorites.value) {
        filtered = filtered.filter(attack => attack.is_favorite);
    }
    if (searchQuery.value) {
        const lowerCaseQuery = searchQuery.value.toLowerCase();
        filtered = filtered.filter(attack => 
            (attack.name && attack.name.toLowerCase().includes(lowerCaseQuery)) || 
            (attack.description && attack.description.toLowerCase().includes(lowerCaseQuery))
        );
    }
    
    // --- 2. Sort the Filtered List ---
    filtered.sort((a, b) => {
        const isASelected = selectedIds.value.includes(a.id);
        const isBSelected = selectedIds.value.includes(b.id);

        // Prioritize selected items 
        if (isASelected !== isBSelected) {
            return isASelected ? -1 : 1;
        }

        // Maintain original sort (favorite > name)
        const favA = a.is_favorite ? 0 : 1;
        const favB = b.is_favorite ? 0 : 1;
        if (favA !== favB) return favA - favB; 
        return a.name.localeCompare(b.name); 
    });

    return filtered;
});

// --- Mobile Click Handlers --- REMOVED handleMobileSelect/handleMobileDeselect

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

    <!-- Single Column Layout -->
    <div class="manager-content"> 
        <h3>
            Attacks 
            <span v-if="selectedIds.length > 0">({{ selectedIds.length }}/{{ MAX_SELECTED }} Selected)</span>
        </h3>
        
        <!-- Search & Filter Controls -->
        <div class="controls-bar">
          <div class="search-bar-container">
            <input 
              type="search" 
              v-model="searchQuery" 
              placeholder="Search..." 
              class="search-input"
            />
          </div>
          <div class="filter-toggle-container">
            <label class="toggle-switch">
              <input type="checkbox" v-model="showOnlyFavorites">
              <span class="slider"></span>
            </label>
            <span class="toggle-label">Only Favorites</span>
          </div>
        </div>

        <!-- Unified Attack Grid -->
         <AttackGrid
             mode="select" 
             :attacks="filteredAndSortedAttacks" 
             v-model:selectedIds="selectedIds" 
             :maxSelectable="MAX_SELECTED" 
             :allowDeletion="true" 
             @deleteAttack="handleDeleteAttack" 
             :showFavoriteButton="true" 
             :favoriteAttackIds="favoriteAttackIdsSet"
             @toggleFavorite="handleToggleFavorite"
             class="unified-attack-grid" 
         >
             <template #empty>
                 <div class="empty-list-message">
                   {{ searchQuery ? 'No attacks match your search.' : (allAvailableAttacks.length === 0 ? 'No attacks created yet.' : 'No attacks match filters.') }}
                </div>
            </template>
         </AttackGrid>
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

.moveset-manager h2 { /* Remove if no longer needed */
    /* text-align: center; */
    /* margin-bottom: 1.5rem; */
    /* color: var(--color-heading); */
}

.manager-content { /* Replaces manager-layout */
    /* Single column, no grid needed here */
    width: 100%;
    margin: 0 auto; /* Center the content area */
}

.manager-content h3 {
    text-align: center;
    margin-bottom: 1rem;
    color: var(--color-text-muted);
    font-weight: 500;
}
.manager-content h3 span {
    font-size: 0.85em;
    color: var(--color-accent); /* Highlight selected count */
}

/* Keep Controls Bar Styles */
.controls-bar {
  display: flex;
  justify-content: space-between; 
  align-items: center;
  margin-bottom: 1.5rem; /* Increased space */
  padding: 0 5px; 
  gap: 15px;
}
.search-bar-container { flex-grow: 1; }
.filter-toggle-container { display: flex; align-items: center; gap: 8px; }
.toggle-label { font-size: 0.85em; color: var(--color-text-muted); cursor: pointer; }

/* --- UPDATED: Toggle Switch Styles (Match AttackCreatorView) --- */
.toggle-switch { position: relative; display: inline-block; width: 34px; height: 20px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.slider { 
    position: absolute; 
    cursor: pointer; 
    top: 0; 
    left: 0; 
    right: 0; 
    bottom: 0; 
    background-color: var(--color-border); /* Match background */
    transition: .4s; 
    /* border-radius: 20px; REMOVED */
    border: 1px solid var(--color-border-hover); 
    border-radius: 0; /* Make square */
}
.slider:before { 
    position: absolute; 
    content: ""; 
    height: 14px; 
    width: 14px; 
    left: 2px; 
    bottom: 2px; 
    background-color: var(--color-panel-bg); /* Match panel background */
    transition: .4s; 
    /* border-radius: 50%; REMOVED */
    border-radius: 0; /* Make square */
}
input:checked + .slider { 
    background-color: var(--color-accent-secondary); 
}
input:checked + .slider:before { 
    transform: translateX(14px); 
}
/* --- END UPDATED --- */

/* Keep Search Input Styles - Remove border-radius */
.search-input {
  width: 100%;
  padding: 0.6rem 1rem;
  /* border-radius: 6px; REMOVED */
  border-radius: 0; /* Make square */
  border: 1px solid var(--color-border-hover); /* Match border */
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.5rem;
  font-family: var(--font-primary); /* Ensure font consistency */
}
.search-input:focus {
  outline: none;
  border-color: var(--primary-color, var(--color-accent-secondary)); /* Use theme color or fallback */
  box-shadow: 0 0 0 2px var(--primary-color-translucent, var(--color-accent-secondary-transparent)); /* Use theme color or fallback */
}


/* Unified Attack Grid Styling - Remove border-radius */
.unified-attack-grid {
  /* Remove any specific styles like max-width from selected-attack-grid */
  /* Allow it to fill the container */
  min-height: 300px; 
  overflow-y: auto; /* Scroll if many attacks */
  padding: 1rem; /* Add padding around the grid */
  /* border-radius: 8px; REMOVED */
  border-radius: 0; /* Make square */
  border: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
}


/* Remove Grid Column definitions and related styles if they were specific to manager layout */
/* .attack-column { ... } */ 
/* .selected-column { ... } */
/* .available-column { ... } */
/* .selected-attack-grid { ... } */
/* .available-attack-grid { ... } */

/* Remove fixed 3 column styles */
/* .selected-attacks-fixed-3 .attack-grid-layout { ... } */

/* Keep empty message style */
.empty-list-message {
  grid-column: 1 / -1; /* Span all columns */
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-text-mute);
  font-style: italic;
}

/* Keep draggable styling if needed for future use, otherwise remove */
/* .ghost { ... } */
/* .sortable-chosen { ... } */
/* .sortable-drag { ... } */

/* Keep Saving Indicator Style */
.saving-indicator {
  text-align: right;
  font-style: italic;
  color: var(--color-text-mute);
  font-size: 0.9em;
  margin-bottom: 0.5rem; 
  height: 1.2em; 
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

/* Remove Responsive Display Toggle CSS */
/* .attack-display-mobile { ... } */
/* .attack-display-desktop { ... } */
/* @media (max-width: 768px) { ... } */

/* Keep Loading Placeholder */
.loading-placeholder { 
   padding: 10px;
   text-align: center;
   font-style: italic;
   color: var(--color-log-system);
   background-color: var(--color-bg);
   border: 1px dashed var(--color-border);
   margin-bottom: 1rem;
}

</style> 