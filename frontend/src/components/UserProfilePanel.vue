<script setup>
import { computed, ref } from 'vue';
import UserProfileStatsEditor from '@/components/UserProfileStatsEditor.vue';
import { useAuthStore } from '@/stores/auth';

// --- NEW: API Service Import ---
// Import the specific function and potentially the client if needed elsewhere
import { generateProfilePicture as apiGenerateProfilePicture } from '@/services/api'; // Correct path and import specific function

const props = defineProps({
  user: {
    type: Object,
    required: true
  }
});

const authStore = useAuthStore();
const isUpdatingBotOptIn = ref(false);
// --- NEW: State for Image Generation ---
const isGeneratingImage = ref(false);
const generationError = ref(null);
// --- END NEW ---

const allowBotChallengesModel = computed({
  get: () => props.user?.allow_bot_challenges ?? false,
  async set(newValue) {
    if (!props.user) return;
    isUpdatingBotOptIn.value = true;
    const success = await authStore.updateUserProfile({ allow_bot_challenges: newValue });
    if (!success) {
      console.error('Failed to update bot challenge preference');
    } else {
       // Optionally show success feedback
    }
    isUpdatingBotOptIn.value = false;
  }
});

const profilePicBase64 = computed(() => props.user?.profile_picture_base64);
// --- END NEW ---

async function generateProfilePic() {
    if (!props.user || isGeneratingImage.value) return;

    isGeneratingImage.value = true;
    generationError.value = null;

    try {
        console.log("Requesting profile picture generation...");
        // Call the imported function directly
        const updatedUser = await apiGenerateProfilePicture(); // Use the imported function

        if (updatedUser) {
            // Update the local user state via the store
            authStore.fetchUserProfile(); // Re-fetch user data to get the new URL
            console.log("Profile picture generated successfully!");
        } else {
             // The API function might throw an error, or return null/undefined
             // if it handles errors internally. Adjust based on api.js implementation.
             generationError.value = "Failed to generate profile picture. Response was empty or invalid.";
        }

    } catch (error) {
        console.error("Error generating profile picture:", error);
        generationError.value = error.response?.data?.detail || error.message || "An unknown error occurred.";
        // Handle specific errors like insufficient credits
        if (error.response?.status === 400) {
             generationError.value = error.response.data.detail; // Show backend message
        }
    } finally {
        isGeneratingImage.value = false;
    }
}
// --- END NEW ---

</script>

<template>
  <div class="user-panel panel">
      <div v-if="user">
        <!-- Header: Title and Level -->
        <div class="panel-header">
            <h2>{{ user.username }}'s Quarters</h2>
            <div class="stat-level">
                <span class="label">LVL</span>
                <span class="value">{{ user.level || '1' }}</span>
            </div>
        </div>

        <!-- Main Content Area (Flex Row) -->
        <div class="panel-content">
            <!-- Left Column: Picture & Credits -->
            <div class="content-left">
                <div class="profile-picture-area">
                     <div class="profile-picture-container">
                         <!-- Use data URI for base64 -->
                         <img 
                            v-if="profilePicBase64" 
                            :src="'data:image/png;base64,' + profilePicBase64" 
                            alt="User Profile Picture" 
                            class="profile-picture"
                         />
                         <div v-else class="profile-picture-placeholder">
                             <span>?</span> 
                         </div>
                     </div>
                     <button 
                         @click="generateProfilePic" 
                         :disabled="isGeneratingImage || !user"
                         class="button generate-button"
                         title="Costs 1 Credit"
                     >
                         <span v-if="!isGeneratingImage">Generate Picture</span>
                         <span v-else>Generating...</span>
                         <span v-if="isGeneratingImage" class="loading-spinner"></span>
                     </button>
                     <p v-if="generationError" class="error-message">{{ generationError }}</p>
                </div>
                 <!-- Display Booster Credits -->
                <div class="user-currency">
                  <span class="label">💰 Credits:</span>
                  <span class="value">{{ user.booster_credits ?? 0 }}</span>
                </div>
            </div>

            <!-- Right Column: Stats Editor -->
            <div class="content-right">
                <UserProfileStatsEditor />
            </div>
        </div>

        <!-- Footer: Bot Toggle -->
        <div class="panel-footer">
            <div class="bot-challenge-toggle">
              <label for="allow-bot-challenge-checkbox">
                <input 
                  type="checkbox" 
                  id="allow-bot-challenge-checkbox" 
                  v-model="allowBotChallengesModel" 
                  :disabled="isUpdatingBotOptIn"
                />
                Allow others to fight me as an AI
              </label>
              <span v-if="isUpdatingBotOptIn" class="loading-indicator">⚙️</span>
            </div>
        </div>

      </div>
      <div v-else>
        <p>Loading user profile...</p>
      </div>
  </div>
</template>

<style scoped>
/* General Panel Style (Keep as is) */
.panel {
    background-color: var(--color-background-soft);
    padding: 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column; /* Ensure panel itself stacks content vertically */
}

.user-panel {
   /* position: relative; */ /* Only if needed for absolute children */
}

/* --- Header Section --- */
.panel-header {
    display: flex;
    justify-content: space-between; /* Pushes title and level apart */
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--color-border-hover);
}

.panel-header h2 {
    margin: 0; /* Remove default margins */
    color: var(--color-heading);
    /* Removed text-align, border, padding from h2 */
}

.stat-level {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: var(--color-background-mute);
    padding: 0.5rem 1rem;
    border-radius: 50%;
    width: 55px; /* Slightly smaller */
    height: 55px;
    justify-content: center;
    border: 2px solid var(--color-border-hover);
    flex-shrink: 0; /* Prevent shrinking */
}
.stat-level .label {
    font-size: 0.7em; /* Smaller label */
    color: var(--color-text-muted);
    font-weight: bold;
    line-height: 1;
}
.stat-level .value {
    font-size: 1.2em; /* Smaller value */
    font-weight: bold;
    color: var(--color-heading);
    line-height: 1.1;
}

/* --- Main Content Section --- */
.panel-content {
    display: flex;
    gap: 2rem; /* Space between left and right columns */
    flex-grow: 1; /* Allow content to take available space */
    margin-bottom: 1.5rem; /* Space before footer */
    /* Default: Row layout */
    flex-direction: row;
}

/* --- Left Column (Picture & Credits) --- */
.content-left {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem; /* Space between picture area and credits */
    flex-basis: 150px; /* Give it a base width, adjust as needed */
    flex-shrink: 0; /* Prevent shrinking too much */
}

.profile-picture-area {
    display: flex;
    flex-direction: column;
    gap: 1rem; 
}

.profile-picture-container {
    background-color: var(--color-background-mute);
    border: 2px solid var(--color-border);
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden; 
    box-shadow: 2px 2px 0px var(--color-border);
}

.profile-picture {
    width: 100%;
    height: 100%;
    object-fit: contain; 
    image-rendering: pixelated; 
    background-color: #555; 
}

.profile-picture-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 3em; /* Larger placeholder icon/text */
    color: var(--color-text-muted);
    font-family: var(--font-primary);
}

.generate-button {
    /* Styles unchanged, assuming base button styles exist */
    padding: 6px 12px;
    font-size: 0.9em;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-primary);
    border: var(--border-width) solid var(--color-border);
    background-color: var(--color-accent-secondary);
    color: var(--color-panel-bg);
    cursor: pointer;
    text-align: center;
    transition: background-color 0.2s ease, transform 0.1s ease, opacity 0.2s ease;
    box-shadow: 2px 2px 0px var(--color-border);
    text-transform: uppercase;
    border-radius: 0;
}
/* ... (rest of generate-button styles: hover, active, disabled, spinner) ... */
.generate-button:hover:not(:disabled) {
    background-color: var(--color-text); /* Example hover */
    color: var(--color-bg);
}
.generate-button:active:not(:disabled) {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px var(--color-border);
}
.generate-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    box-shadow: 1px 1px 0px var(--color-border);
}
.loading-spinner {
    display: inline-block;
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-bottom-color: transparent;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
}
.error-message { 
    color: var(--color-accent);
    font-size: 0.85em;
    margin-top: 0.25rem;
    text-align: center;
    width: 100%; 
}

.user-currency {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    font-size: 1em; /* Slightly smaller */
    background-color: var(--color-background-mute);
    padding: 0.5rem 0.8rem;
    border-radius: 6px;
    border: 1px solid var(--color-border);
    width: fit-content;
}
.user-currency .label {
    font-weight: bold;
    color: var(--color-text-muted);
}
.user-currency .value {
    font-weight: bold;
    color: var(--vt-c-yellow);
}

/* --- Right Column (Stats Editor) --- */
.content-right {
    flex-grow: 1; /* Takes remaining space */
    display: flex; /* Allow stats editor to fill height if needed */
    flex-direction: column;
}

/* --- Footer Section --- */
.panel-footer {
    margin-top: auto; /* Pushes footer to the bottom if panel has extra height */
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
}

.bot-challenge-toggle {
  text-align: center;
}

.bot-challenge-toggle label {
  cursor: pointer;
  display: inline-flex; 
  align-items: center;
  gap: 0.5rem;
}

.bot-challenge-toggle input[type="checkbox"] {
  cursor: pointer;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  width: 14px; 
  height: 14px;
  background-color: var(--color-bg); 
  border: 1px solid var(--color-border);
  position: relative;
  display: inline-block;
  vertical-align: middle; 
  border-radius: 0; 
  box-shadow: 1px 1px 0px var(--color-border); 
}

.bot-challenge-toggle input[type="checkbox"]:checked {
  background-color: var(--color-accent-secondary); 
  border-color: var(--color-border);
}

.bot-challenge-toggle input[type="checkbox"]:checked::after {
  content: '';
  display: block;
  position: absolute;
  left: 4px;
  top: 1px;
  width: 3px;
  height: 7px;
  border: solid var(--color-bg); 
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.bot-challenge-toggle input[type="checkbox"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    box-shadow: none;
}

.loading-indicator {
    display: inline-block;
    margin-left: 0.5rem;
    animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Remove redundant/unused styles */
.user-basic-info { display: none; } /* Hide the old basic info container */

/* --- Responsive: Mobile Layout --- */
@media (max-width: 768px) { 
    .panel-header {
        flex-direction: column;
        align-items: center; /* Center header items */
        gap: 0.5rem;
    }
    .stat-level {
        /* Adjust level display if needed for stacked header */
    }

    .panel-content {
        flex-direction: column; /* Stack columns vertically */
        align-items: center; /* Center columns */
        gap: 1.5rem; /* Adjust gap for vertical layout */
    }

    .content-left {
        flex-basis: auto; /* Remove fixed basis */
        width: 100%; /* Allow left content to take full width */
        max-width: 250px; /* Limit max width */
        /* Items inside are already centered by flexbox */
    }

    .content-right {
        width: 100%; /* Allow stats editor to take full width */
        max-width: 400px; /* Optional: Limit width */
    }
}

</style> 