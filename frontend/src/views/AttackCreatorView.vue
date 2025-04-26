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


      <!-- Generated Attacks Preview -->
      <div v-if="generatedAttacks.length > 0 && !isLoading" class="generated-attacks-preview">
          <h3>Generated Attacks Preview:</h3>
          <!-- Desktop Grid -->
          <div class="attack-display-desktop">
            <AttackGrid
                :attacks="generatedAttacks"
                mode="reveal"
                :revealedIds="revealedAttackIds"
                @reveal="revealedAttackIds.add($event)"
                class="generated-attack-display"
            />
          </div>
           <!-- Mobile List -->
          <div class="attack-display-mobile">
              <AttackListMobile 
                  :attacks="generatedAttacks" 
                  mode="display"
              />
          </div>
          <!-- Removed old grid and transition -->
          <p class="preview-footer">These attacks have been added to your collection.</p>
      </div>

      <button 
        type="submit" 
        :disabled="isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0" 
        class="button button-primary open-booster-button"
        :class="{ 'disabled-look': isLoading || !concept.trim() || !hasEnoughCredits || remainingChars < 0 }"
      >
        <span class="button-icon">🎁</span>
        {{ isLoading ? 'Opening...' : `Open Booster for ${BOOSTER_COST} 💰` }}
      </button>

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

        <!-- Desktop Grid -->
        <div class="attack-display-desktop">
            <AttackGrid 
                :attacks="filteredUserAttacks"
                mode="select"
                v-model:selectedIds="selectedFavoriteAttackIds"
                :maxSelectable="MAX_FAVORITES"
                class="favorite-attack-selector"
            />
        </div>
        <!-- Mobile List -->
        <div class="attack-display-mobile">
            <AttackListMobile
                :attacks="filteredUserAttacks"
                mode="action"
                @attackClick="toggleFavoriteSelection($event)"
                :disabledIds="new Set()"
                :selectedIdsSet="selectedFavoriteAttackIdsSet"
                class="favorite-attack-selector-mobile"
            />
        </div>
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
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import AttackGrid from '@/components/AttackGrid.vue';
import AttackListMobile from '@/components/AttackListMobile.vue';

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

// --- NEW: Computed property for Selected IDs Set ---
const selectedFavoriteAttackIdsSet = computed(() => {
    return new Set(selectedFavoriteAttackIds.value);
});

// --- NEW: Mobile Favorite Selection Handler ---
function toggleFavoriteSelection(attack) {
  const index = selectedFavoriteAttackIds.value.indexOf(attack.id);
  if (index > -1) {
    // Deselect
    selectedFavoriteAttackIds.value.splice(index, 1);
  } else {
    // Select if not full
    if (selectedFavoriteAttackIds.value.length < MAX_FAVORITES) {
      selectedFavoriteAttackIds.value.push(attack.id);
    }
  }
}

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
    error.value = null;
    successMessage.value = null;
    generatedAttacks.value = [];
    revealedAttackIds.value.clear();
    selectedFavoriteAttackIds.value = [];
    favoriteSearchQuery.value = '';
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
  max-width: 500px; 
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

.search-bar-container {
  margin-bottom: 8px; 
}

.favorite-attack-selector {
  /* Remove border/padding, let AttackGrid handle internal padding */
  border: none;
  border-radius: 0;
  padding: 0;
  margin-top: 5px;
}

.selection-counter {
  display: block;
  margin-top: 5px;
  font-size: 0.85em;
  color: var(--color-log-system);
  text-align: right;
}

/* Responsive Toggle */
.attack-display-mobile { display: none; }
@media (max-width: 768px) { 
    .attack-display-desktop { display: none; }
    .attack-display-mobile { display: block; }
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

</style> 