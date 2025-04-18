<template>
  <div class="attack-creator-view panel">
    <div class="booster-header">
      <h2>Open New Booster</h2>
    </div>

    <div v-if="isLoading" class="loading-placeholder">Generating your attacks... please wait.</div>
    <div v-if="error && !isLoading" class="error-message">⚠️ {{ error }}</div>
    <div v-if="successMessage && !isLoading" class="success-message">✅ {{ successMessage }}</div>

    <form @submit.prevent="handleSubmit" class="attack-generation-form">
      <div class="form-group">
        <label for="attack-concept">Booster Theme/Concept:</label>
        <input 
          id="attack-concept" 
          v-model="concept" 
          type="text" 
          placeholder="e.g., 'Shadow magic', 'Clockwork devices', 'Oceanic power'"
          :maxlength="MAX_CONCEPT_LENGTH"
          required 
        />
        <small class="char-counter" :class="{ 'limit-reached': remainingChars < 0 }">
          {{ remainingChars >= 0 ? `${remainingChars} characters remaining` : 'Character limit exceeded' }}
        </small>
      </div>

      <!-- Favorite Attacks Selection -->
      <div v-if="userAttacks.length > 0" class="form-group favorite-attacks-section full-width">
        <label>Select Favorite Attacks (Optional, Max {{ MAX_FAVORITES }} for Inspiration):</label>

        <!-- Add Search Input -->
        <div class="search-bar-container">
          <input 
            type="search" 
            v-model="favoriteSearchQuery" 
            placeholder="Search your attacks..." 
            class="search-input"
          />
        </div>

        <!-- Use AttackGrid for selection - Pass filtered attacks -->
        <AttackGrid 
            :attacks="filteredUserAttacks"
            mode="select"
            v-model:selectedIds="selectedFavoriteAttackIds"
            :maxSelectable="MAX_FAVORITES"
            class="favorite-attack-selector"
        />
         <small class="selection-counter">{{ selectedFavoriteAttackIds.length }} / {{ MAX_FAVORITES }} selected</small>
      </div>
      <!-- End Favorite Attacks Selection -->

      <button 
        type="submit" 
        :disabled="isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0" 
        class="button button-primary open-booster-button"
        :class="{ 'disabled-look': isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0 }"
      >
        <span class="button-icon">🎁</span>
        {{ isLoading ? 'Opening...' : `Open Booster for ${BOOSTER_COST} 💰` }}
      </button>
    </form>

    <!-- Generated Attacks Preview -->
    <div v-if="generatedAttacks.length > 0 && !isLoading" class="generated-attacks-preview">
        <h3>Generated Attacks Preview:</h3>
        <!-- Use AttackGrid for reveal -->
        <AttackGrid
            :attacks="generatedAttacks"
            mode="reveal"
            :revealedIds="revealedAttackIds"
            @reveal="revealedAttackIds.add($event)"
            class="generated-attack-display"
        />
        <!-- Removed old grid and transition -->
        <p class="preview-footer">These attacks have been added to your collection.</p>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import AttackGrid from '@/components/AttackGrid.vue';

const gameStore = useGameStore();
const authStore = useAuthStore();

const concept = ref('');
const isLoading = ref(false);
const error = ref(null);
const successMessage = ref(null);
const generatedAttacks = ref([]);
const revealedAttackIds = ref(new Set());
const selectedFavoriteAttackIds = ref([]);
const favoriteSearchQuery = ref('');

const MAX_CONCEPT_LENGTH = 50;
const BOOSTER_COST = 6;
const MAX_FAVORITES = 6;

// Computed property for character count
const conceptCharCount = computed(() => concept.value.length);
const remainingChars = computed(() => MAX_CONCEPT_LENGTH - conceptCharCount.value);

// Get current user credits
const userCredits = computed(() => authStore.currentUser?.booster_credits ?? 0);
const hasEnoughCredits = computed(() => userCredits.value >= BOOSTER_COST);

// Get user's attacks from the AUTH store
const userAttacks = computed(() => authStore.currentUser?.attacks || []);

// Filter user attacks based on search query
const filteredUserAttacks = computed(() => {
  if (!favoriteSearchQuery.value) return userAttacks.value;
  const lowerQuery = favoriteSearchQuery.value.toLowerCase();
  return userAttacks.value.filter(attack => 
    (attack.name && attack.name.toLowerCase().includes(lowerQuery)) ||
    (attack.description && attack.description.toLowerCase().includes(lowerQuery)) // Optional: search description too
  );
});

async function handleSubmit() {
  error.value = null;
  successMessage.value = null;
  generatedAttacks.value = [];
  revealedAttackIds.value.clear();
  selectedFavoriteAttackIds.value = [];
  favoriteSearchQuery.value = '';
  isLoading.value = true;

  try {
    // Check credits again just before submitting (belt and suspenders)
    if (!hasEnoughCredits.value) {
      throw new Error("Not enough credits.");
    }
    // Use concept for name generation in backend, or generate unique name here
    // For now, just pass concept as both name and concept to backend
    const generatedName = concept.value.trim().substring(0, 50); // Use trimmed concept as name (up to 50 chars)
    const result = await gameStore.generateAttacks(
        concept.value, // Pass the concept text
        selectedFavoriteAttackIds.value // Pass the array of selected favorite IDs
    );
    successMessage.value = result.message || 'Attacks generated successfully!'; // Use message from backend
    generatedAttacks.value = result.attacks || []; // Store attacks for preview
    // Refresh user profile to get updated credits
    await authStore.fetchUserProfile(); 
    // Optionally clear form on success
    // concept.value = '';
  } catch (err) {
    // Error is already set in the store action, but we can capture it here too if needed
    error.value = err.message || err.response?.data?.error || 'Failed to open booster.';
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
    // Clear any previous messages when component mounts
    error.value = null;
    successMessage.value = null;
    generatedAttacks.value = [];
    revealedAttackIds.value.clear();
    selectedFavoriteAttackIds.value = [];
    favoriteSearchQuery.value = '';

    // REMOVED: Fetch user attacks (now assumed to be in authStore.currentUser)
    // if (gameStore.userAttacks === null || gameStore.userAttacks.length === 0) {
    //     try {
    //         await gameStore.fetchUserAttacks(); 
    //     } catch (fetchError) {
    //         console.error("Failed to fetch user attacks:", fetchError);
    //     }
    // }
});

</script>

<style scoped>
.attack-creator-view {
  max-width: 700px; /* Adjust width */
  margin: 2rem auto;
  padding: 2rem;
  text-align: center; /* Center align content */
}

.booster-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #444; /* Separator */
}

.booster-header h2 {
  margin-bottom: 0.5rem;
  font-size: 1.8em;
}

.attack-generation-form {
  display: flex;
  flex-direction: column;
  align-items: center; /* Center form elements */
  gap: 1.5rem;
}

.form-group {
  width: 100%;
  max-width: 500px; /* Limit input width */
  text-align: left; /* Align label/input left */
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 0.8rem 1rem;
}

.char-counter {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.85em;
  color: #aaa;
  text-align: right;
}

.char-counter.limit-reached {
  color: var(--danger-color);
  font-weight: bold;
}

.open-booster-button {
  padding: 1rem 2rem; /* Larger padding */
  font-size: 1.2em; /* Larger font */
  font-weight: bold;
  background: linear-gradient(145deg, var(--primary-color-light), var(--primary-color-dark)); /* Gradient */
  border: none;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: inline-flex; /* Align icon and text */
  align-items: center;
  gap: 0.5rem;
  min-width: 200px; /* Ensure decent width */
  justify-content: center;
}

.open-booster-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 255, 157, 0.3);
}

.open-booster-button:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 5px rgba(0, 255, 157, 0.2);
}

.open-booster-button.disabled-look {
  background: #555; /* Darker grey when disabled */
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
  transform: none;
}

.button-icon {
  font-size: 1.3em;
}

.small-text {
    font-size: 0.9em;
}

/* Styles for the preview grid (similar to MovesetManager) */
.preview-grid {
  display: grid;
  gap: 1rem;
  padding: 1rem 0; /* Adjust padding */
  /* Let auto-fit handle columns */
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
}

.attack-card-wrapper {
  background-color: var(--color-background);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  padding: 0.8rem; /* Keep padding */
  height: 200px; /* Adjusted fixed height */
  width: 100%; /* Ensure it fills grid cell width */
  display: flex; 
  flex-direction: column; 
  justify-content: center; 
  align-items: center; 
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  overflow: hidden; /* Prevent content from spilling out */
  perspective: 1000px; /* Add perspective for 3D flip */
}

/* RE-ADD: Styles for face-down card */
.attack-card-face-down {
  width: 100%;
  height: 100%;
  background-color: var(--color-background-mute);
  border: 2px dashed var(--color-border-hover);
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 0.9em;
  font-style: italic;
  cursor: pointer;
  transition: background-color 0.2s;
  border-radius: 6px; /* Keep radius */
  box-sizing: border-box; 
}

.attack-card-face-down:hover {
  background-color: var(--color-background-soft);
}

.reveal-prompt {
  /* Optional: specific styling */
}

/* RE-ADD: Flip Transition Styles */
.flip-enter-active,
.flip-leave-active {
  transition: transform 0.6s ease;
  backface-visibility: hidden; /* Hide back during flip */
}

.flip-enter-from,
.flip-leave-to {
  transform: rotateY(90deg);
}

.flip-enter-to,
.flip-leave-from {
  transform: rotateY(0deg);
}

/* Keep Generated Attacks Preview styles */
.generated-attacks-preview {
    margin-top: 3rem;
    text-align: left;
}

.preview-footer {
    margin-top: 1.5rem;
    text-align: center;
    font-style: italic;
    color: #aaa;
}

/* Styles for Favorite Attack Selection */
.favorite-attacks-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #444;
  width: 100%;
  /* max-width: 600px; */ /* REMOVED max-width */
}

/* Ensure full-width section is centered like the form */
.favorite-attacks-section.full-width {
  /* max-width: 700px; */ /* <-- Ensure this line is removed or commented out */
  margin: 1.5rem auto 0 auto; /* Keep centering and margin top */
}

/* Styles for Search Bar (similar to MovesetManager) */
.search-bar-container {
  margin-bottom: 0.5rem; /* Space below search bar */
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
  box-shadow: 0 0 0 2px var(--primary-color-translucent); 
}

/* Style the AttackGrid component specifically for favorites if needed */
.favorite-attack-selector {
  /* Add specific styles for the favorites grid container if necessary */
  max-height: 250px; /* Limit height and make scrollable */
  overflow-y: auto; /* Add scrollbar if needed */
  padding: 0.5rem;
  border: 1px solid #555;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.1); /* Slight background */
  margin-top: 0.5rem;
}

/* Remove old grid item styles */
/* .attack-selection-grid { ... } */
/* .attack-checkbox-item { ... } */
/* .attack-checkbox-label { ... } */
/* .selection-indicator { ... } */

/* Keep counter style */
.selection-counter {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.9em;
  color: #aaa;
  text-align: right;
}
/* End Styles for Favorite Attack Selection */

</style> 