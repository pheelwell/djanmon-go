<template>
  <div class="attack-creator-view panel">
    <div class="booster-header">
      <h2>Open New Booster</h2>
    </div>

    <div v-if="isLoading" class="loading-placeholder">Generating your attacks... please wait.</div>
    <div v-if="error && !isLoading" class="error-message">⚠️ {{ error }}</div>
    <div v-if="successMessage && !isLoading" class="success-message">✅ {{ successMessage }}</div>

    <form @submit.prevent="handleSubmit" class="attack-generation-form">
      <div class="form-group concept-group">
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


      <!-- Generated Attacks Preview -->
      <div v-if="generatedAttacks.length > 0 && !isLoading" class="generated-attacks-preview">
          <h3>Generated Attacks Preview:</h3>
          <!-- Desktop Grid -->
          <div class="attack-display-desktop">
             <!-- Wrap grid in TransitionGroup -->
            <TransitionGroup name="card-reveal" tag="div" class="generated-attack-display">
                <AttackGrid
                    :attacks="generatedAttacks"
                    mode="reveal"
                    :revealedIds="revealedAttackIds"
                    @reveal="revealedAttackIds.add($event)"
                    :key="'generated-grid'" 
                    class="generated-attack-grid"
                    :showFavoriteButton="true" 
                    :favoriteAttackIds="favoriteAttackIdsSet"
                    @toggleFavorite="handleToggleFavoriteInSelector"
                />
                 <!-- Add individual card handling for spin? Need to adjust AttackGrid or handle click here -->
                 <!-- Let's try applying class based on revealedIds directly in AttackGrid if possible, -->
                 <!-- or add a wrapper here if AttackGrid doesn't support itemClass -->
                 <!-- Simpler for now: Trigger reveal logic, CSS targets revealed cards -->
             </TransitionGroup>
          </div>
           <!-- Mobile List -->
          <div class="attack-display-mobile">
              <!-- Add TransitionGroup here too if desired -->
              <AttackListMobile 
                  :attacks="generatedAttacks" 
                  mode="display"
              />
          </div>
          <p class="preview-footer">These attacks have been added to your collection.</p>
      </div>

      <button 
        type="submit" 
        :disabled="isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0 || isLoadingConfig"
        class="button button-primary open-booster-button"
        :class="{ 'disabled-look': isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0 || isLoadingConfig }"
      >
        <span class="button-icon">🎁</span>
        <span v-if="isLoading">Opening...</span>
        <span v-else-if="isLoadingConfig">Loading Cost...</span>
        <span v-else>{{ `Open Booster for ${boosterCost} 💰` }}</span>
      </button>

      <!-- Favorite Attacks Selection -->
      <div v-if="userAttacks.length > 0" class="form-group favorite-attacks-section full-width">
        <label>Attacks for inspiration (Max {{ MAX_FAVORITES }}):</label>

        <!-- UPDATED: Add Search & Filter Controls -->
        <div class="controls-bar">
          <div class="search-bar-container">
            <input 
              type="search" 
              v-model="favoriteSearchQuery" 
              placeholder="Search..." 
              class="search-input"
            />
          </div>
          <div class="filter-toggle-container">
            <label class="toggle-switch">
              <input type="checkbox" v-model="showOnlyFavoritesInSelector">
              <span class="slider"></span>
            </label>
            <span class="toggle-label">Only Favorites</span>
          </div>
        </div>
        <!-- END UPDATED -->

        <!-- Use single AttackGrid -->
         <AttackGrid 
            :attacks="filteredUserAttacks"
            mode="select" 
            v-model:selectedIds="selectedFavoriteAttackIds" 
            :maxSelectable="MAX_FAVORITES"
            class="favorite-attack-selector" 
            :showFavoriteButton="true" 
            :favoriteAttackIds="favoriteAttackIdsSet"
            @toggleFavorite="handleToggleFavoriteInSelector"
         />
         <small class="selection-counter">{{ selectedFavoriteAttackIds.length }} / {{ MAX_FAVORITES }} selected</small>
      </div>
      <!-- End Favorite Attacks Selection -->
    </form>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useGameStore } from '@/stores/game';
import { useAuthStore } from '@/stores/auth';
import AttackGrid from '@/components/AttackGrid.vue';
import { fetchGameConfig } from '@/services/api';

const gameStore = useGameStore();
const authStore = useAuthStore();

const concept = ref('');
const isLoading = ref(false);
const error = ref(null);
const successMessage = ref(null);
const revealedAttackIds = ref(new Set());
const selectedFavoriteAttackIds = ref([]);
const favoriteSearchQuery = ref('');
const showOnlyFavoritesInSelector = ref(false);

const boosterCost = ref(1);
const isLoadingConfig = ref(true);

const MAX_CONCEPT_LENGTH = 50;
const MAX_FAVORITES = 6;

// Computed property for character count
const conceptCharCount = computed(() => concept.value.length);
const remainingChars = computed(() => MAX_CONCEPT_LENGTH - conceptCharCount.value);

// Get current user credits
const userCredits = computed(() => authStore.currentUser?.booster_credits ?? 0);
const hasEnoughCredits = computed(() => userCredits.value >= boosterCost.value);

// Get user's attacks from the AUTH store
const userAttacks = computed(() => authStore.currentUser?.attacks || []);

// --- NEW: Get generated attacks from the game store --- 
const generatedAttacks = computed(() => gameStore.lastGeneratedAttacks);

// --- NEW: Favorite Attack IDs Set from Auth Store ---
const favoriteAttackIdsSet = computed(() => {
    const ids = new Set();
    if (authStore.currentUser && authStore.currentUser.attacks) {
        authStore.currentUser.attacks.forEach(attack => {
            if (attack && attack.id !== undefined && attack.is_favorite) {
                ids.add(attack.id);
            }
        });
    }
    return ids;
});

// Filter user attacks based on search query AND favorite toggle
const filteredUserAttacks = computed(() => {
  let attacks = userAttacks.value || [];

  // --- 1. Apply Filters ---
  // Filter by favorite toggle
  if (showOnlyFavoritesInSelector.value) {
    attacks = attacks.filter(attack => attack.is_favorite);
  }
  // Filter by search query
  if (favoriteSearchQuery.value) {
    const lowerQuery = favoriteSearchQuery.value.toLowerCase();
    attacks = attacks.filter(attack => 
      (attack.name && attack.name.toLowerCase().includes(lowerQuery)) ||
      (attack.description && attack.description.toLowerCase().includes(lowerQuery))
    );
  }

  // --- 2. Sort the Filtered List ---
  attacks.sort((a, b) => {
      const isASelected = selectedFavoriteAttackIds.value.includes(a.id);
      const isBSelected = selectedFavoriteAttackIds.value.includes(b.id);

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

  return attacks;
});

// --- NEW: Handle Toggle Favorite Event --- 
async function handleToggleFavoriteInSelector(attackId) {
    if (!attackId) return;
    // No optimistic update here to avoid complexity, just call store action
    try {
        await authStore.toggleAttackFavorite(attackId);
        // User data in store will update automatically, triggering computed properties
        await authStore.fetchUserProfile(); 
        // Optionally clear form on success
        // concept.value = '';
    } catch (err) {
        console.error("Failed to toggle favorite in creator view:", err);
        // Error message handled by store/displayed globally
        error.value = err.message || err.response?.data?.error || 'Failed to open booster.';
    } finally {
        isLoading.value = false;
    }
}

async function fetchConfig() {
    isLoadingConfig.value = true;
    try {
        const response = await fetchGameConfig();
        if (response.data && response.data.attack_generation_cost) {
            boosterCost.value = response.data.attack_generation_cost;
            console.log("Booster cost fetched:", boosterCost.value);
        } else {
             console.warn("Attack generation cost not found in config response, using default.");
             boosterCost.value = 1; // Fallback to default if not found
        }
    } catch (err) {
        console.error("Failed to fetch game config:", err);
        boosterCost.value = 1; // Use default on error
    } finally {
        isLoadingConfig.value = false;
    }
}

async function handleSubmit() {
  error.value = null;
  successMessage.value = null;
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
    const generatedName = concept.value.trim().substring(0, 50); // Use trimmed concept as name (up to 50 chars)
    const result = await gameStore.generateAttacks(
        concept.value, // Pass the concept text
        selectedFavoriteAttackIds.value // Pass the array of selected favorite IDs
    );
    successMessage.value = result.message || 'Attacks generated successfully!'; // Use message from backend
    // generatedAttacks.value = result.attacks || []; // REMOVED: Handled by store
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
    error.value = null;
    successMessage.value = null;
    revealedAttackIds.value.clear();
    selectedFavoriteAttackIds.value = [];
    favoriteSearchQuery.value = '';
    fetchConfig();
});

</script>

<style scoped>
.attack-creator-view {
  /* Use panel styles already applied in HomeView */
  max-width: 700px; 
  margin: 1rem auto; /* Adjust margin */
  padding: var(--panel-padding); /* Use theme padding */
  text-align: center; 
  font-family: var(--font-primary);
}

.booster-header {
  margin: -15px -15px 15px -15px; /* Adjust to match panel-title */
  padding: 8px 15px;
  border-bottom: var(--border-width) solid var(--color-border);
  background-color: var(--color-border); 
  color: var(--color-text);
  box-shadow: inset 0 0 0 1px var(--color-panel-bg);
}

.booster-header h2 {
  margin: 0;
  font-size: 1.3em;
  font-weight: normal;
  text-transform: uppercase;
}

.attack-generation-form {
  display: flex;
  flex-direction: column;
  align-items: center; 
  gap: 15px; /* Adjust gap */
}

.form-group {
  width: 100%;
  max-width: 550px; /* Reduced max-width */
  text-align: left; 
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: normal; /* Pixel font usually doesn't need bold */
  font-size: 0.9em;
  color: var(--color-text);
  text-transform: uppercase;
}


.char-counter {
  display: block;
  margin-top: 3px;
  font-size: 0.8em;
  color: var(--color-log-system);
  text-align: right;
}

.char-counter.limit-reached {
  color: var(--color-accent);
}

/* Button should use global .btn styles */
.open-booster-button {
  /* font-size: 1.2em; Maybe adjust base btn */
  /* padding: 1rem 2rem; */
  display: inline-flex; 
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.button-icon {
  font-size: 1.1em; /* Adjust relative to button font size */
}

/* Preview Section */
.generated-attacks-preview {
    margin-top: 20px;
    text-align: left;
    width: 100%;
    border-top: var(--border-width) dashed var(--color-border);
    padding-top: 15px;
    overflow: hidden; /* Prevent overflow during animations */
}

.generated-attacks-preview h3 {
    text-align: center;
    font-size: 1.1em;
    color: var(--color-accent-secondary);
    margin-bottom: 10px;
    text-transform: uppercase;
}

.preview-footer {
    margin-top: 10px;
    text-align: center;
    font-style: italic;
    color: var(--color-log-system);
    font-size: 0.9em;
}

/* Favorite Section */
.favorite-attacks-section {
  margin-top: 15px;
  padding-top: 15px;
  border-top: var(--border-width) dashed var(--color-border);
  width: 100%;
  text-align: left; /* Ensure label is left-aligned */
}

.controls-bar {
  display: flex;
  justify-content: space-between; /* Align items */
  align-items: center;
  margin-bottom: 8px; /* Adjust spacing if needed */
  gap: 15px;
}

.search-bar-container {
  flex-grow: 1; /* Allow search to take up space */
}

.filter-toggle-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  font-size: 0.85em;
  color: var(--color-text-muted);
  cursor: pointer;
}

/* Basic Toggle Switch Styles */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 20px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--color-border);
  transition: .4s;
  border-radius: 20px;
  border: 1px solid var(--color-border-hover);
}

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
.slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 2px;
  bottom: 2px;
  background-color: var(--color-panel-bg);
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: var(--color-accent-secondary); /* Color when on */
}

input:checked + .slider:before {
  transform: translateX(14px);
}

.favorite-attack-selector {
  /* Remove border/padding, let AttackGrid handle internal padding */
  border: none;
  border-radius: 0;
  padding: 0;
  margin-top: 5px;
  /* Apply grid column styles directly if needed, or rely on AttackGrid's internal styles */
}

.selection-counter {
  display: block;
  margin-top: 5px;
  font-size: 0.85em;
  color: var(--color-log-system);
  text-align: right;
}

/* Loading and Feedback Messages */
.loading-placeholder, .error-message, .success-message {
    /* Assume styles from HomeView apply or copy/adapt them */
    padding: 8px 10px;
    border-radius: 0;
    font-weight: normal;
    text-align: center;
    margin-bottom: 10px; 
    border: 1px solid;
    font-size: 0.9em;
}
.loading-placeholder {
    color: var(--color-log-system);
    font-style: italic;
    border-style: dashed;
    border-color: var(--color-border);
    background-color: var(--color-bg);
    text-transform: uppercase;
}
.error-message {
  background-color: rgba(233, 69, 96, 0.1);
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.success-message {
  background-color: rgba(53, 208, 104, 0.1);
  color: var(--color-hp-high);
  border-color: var(--color-hp-high);
}

/* Make concept input wider */
.concept-group {
  max-width: 500px; /* Reduced max-width */
}

#attack-concept {
    /* Ensure input uses available width if not default */
    width: 100%; 
}

/* Generated Attacks Preview and Animations */
.generated-attack-display {
    /* Ensure the container for TransitionGroup behaves as expected */
    position: relative; 
}

/* Card Reveal Transition (Fade-in + Slight Scale) */
.card-reveal-enter-active,
.card-reveal-leave-active {
  transition: all 0.5s ease;
}
.card-reveal-enter-from,
.card-reveal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
/* Stagger effect */
.card-reveal-enter-active {
    transition-delay: calc(0.08s * var(--stagger-index, 0)); /* Needs index passed */
    /* Note: Passing index might require modifying AttackGrid or how items are rendered */
}


/* Card Spin Animation on Reveal */
/* Apply this class conditionally inside AttackGrid or AttackCardDisplay when revealed */
/* We target based on the presence of the reveal overlay being hidden */
:deep(.attack-grid-item .attack-card-content) {
    transition: transform 0.6s;
    transform-style: preserve-3d;
}

/* This targets the card *after* the overlay is removed (isRevealed becomes true) */
:deep(.attack-grid-item .is-revealed .attack-card-content) {
  /* Animation applied when revealed */
  animation: spin 0.6s ease-out;
}

@keyframes spin {
  from {
    transform: rotateY(0deg);
  }
  to {
    transform: rotateY(360deg);
  }
}

</style> 