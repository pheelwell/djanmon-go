<template>
  <div class="onboarding-view">
    <div class="onboarding-container panel">
      <div class="step-indicator">Step {{ currentStep + 1 }} / {{ totalSteps + 1 }}</div>
      
      <!-- Step Content -->
      <div v-if="currentStep === 0" class="step-content welcome-step">
        <h2>Welcome to GENGO!</h2>
        <p>Let's get you set up for your first battle. It only takes a minute.</p>
        <button @click="nextStep" class="btn btn-primary">Start Setup</button>
        <button @click="skipTutorial" class="btn btn-secondary btn-skip">Skip Tutorial</button>
      </div>

      <div v-else-if="currentStep === 1" class="step-content create-attacks-step">
        <h2>Step 1: Create Attacks</h2>
        <p>Every great fighter needs moves! Use the Attack Creator below to generate your first set.</p>
        <p>Just type a theme (like "Fire", "Water", "Robots") and click "Open Booster".</p>
        <AttackCreatorView class="embedded-component attack-creator-embedded" />
        <p v-if="!hasGeneratedAttacks" class="waiting-message">Waiting for you to generate attacks...</p>
         <button @click="skipTutorial" class="btn btn-secondary btn-skip">Skip Tutorial</button>
      </div>

      <div v-else-if="currentStep === 2" class="step-content select-moveset-step">
        <h2>Step 2: Select Moveset</h2>
        <p>Great! Now, choose which attacks you want to bring into battle.</p>
        <p>Drag up to 6 attacks from your Collection (right) to your Selected Moveset (left).</p>
        <MovesetManager class="embedded-component moveset-manager-embedded" />
        <p v-if="!hasSelectedAttacks" class="waiting-message">Waiting for you to select at least one attack...</p>
        <button @click="nextStep" class="btn btn-primary" :disabled="!hasSelectedAttacks">Continue to Stats</button>
         <button @click="skipTutorial" class="btn btn-secondary btn-skip">Skip Tutorial</button>
      </div>
      
       <div v-else-if="currentStep === 3" class="step-content adjust-stats-step">
         <h2>Step 3: Adjust Stats</h2>
         <p>Here are your starting stats. You have points to allocate! Click the pencil icons to adjust HP, Attack, Defense, and Speed.</p>
         <UserProfilePanel class="embedded-component user-profile-embedded" :user="user" />
         <p>(You can always change these later from the Profile tab in the main game).</p>
         <button @click="finishOnboarding" class="btn btn-primary">Finish Setup</button> 
         <button @click="skipTutorial" class="btn btn-secondary btn-skip">Skip Tutorial</button>
      </div>
      
       <div v-else-if="currentStep === 4" class="step-content complete-step">
         <h2>Setup Complete!</h2>
         <p>You're all set and ready to battle!</p>
         <button @click="goToGame" class="btn btn-primary">Let's Go!</button>
       </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

// Import necessary components to embed
import AttackCreatorView from '@/views/AttackCreatorView.vue';
import UserProfilePanel from '@/components/UserProfilePanel.vue';
import MovesetManager from '@/components/MovesetManager.vue';

const router = useRouter();
const authStore = useAuthStore();

const currentStep = ref(0);
const totalSteps = 4; // Welcome, Create, Select Moveset, Adjust Stats (Completion is step index 4)
const user = computed(() => authStore.currentUser);

// Computed properties to track progress
const hasGeneratedAttacks = computed(() => {
    // Directly check the authStore's reactive state
    return authStore.currentUser?.attacks?.length > 0;
});

const hasSelectedAttacks = computed(() => {
    return authStore.currentUser?.selected_attacks?.length > 0;
});

// --- Step Logic ---
function nextStep() {
    // Check if we can advance to the next logical step (index < totalSteps)
    if (currentStep.value < totalSteps) { 
        currentStep.value++;
    }
}

// Called when clicking button on Step 3 (Adjust Stats)
function finishOnboarding() { 
     console.log("Finishing onboarding setup steps...");
     localStorage.setItem('gengoTutorialCompleted', 'true');
     currentStep.value = totalSteps; // Move to the final completion message step (index = totalSteps)
}

function skipTutorial() {
    console.log("Skipping tutorial...");
    localStorage.setItem('gengoTutorialCompleted', 'true');
    goToGame();
}

function goToGame() {
     console.log("Navigating to home...");
     router.push({ name: 'home' });
}

// Watcher to automatically advance from attack creation step (Step 1)
watch(hasGeneratedAttacks, (newValue) => {
    // Only advance if we are *on* the attack creation step
    if (currentStep.value === 1 && newValue) {
        console.log("Attacks generated, moving to Select Moveset step (Step 2).");
        nextStep();
    }
});

// Watcher for selected attacks (Step 2) - now just enables the button
// The actual advancement happens when the user clicks the "Continue to Stats" button
watch(hasSelectedAttacks, (newValue) => {
     if (currentStep.value === 2 && newValue) {
         console.log("Moveset selected, enabling Continue button for Step 2.");
         // Button's :disabled state handles enabling based on this computed property
     }
 });

// --- Lifecycle --- 
onMounted(() => {
    // Ensure user data is loaded, though the router guard should handle this
    if (!user.value) {
        console.warn("OnboardingView mounted without user data!");
        // Optionally try fetching or redirecting
        // authStore.fetchUserProfile(); 
    }
     console.log("OnboardingView mounted. Current step:", currentStep.value);
});

</script>

<style scoped>
.onboarding-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  background-color: var(--color-bg); 
  font-family: var(--font-primary);
}

.onboarding-container {
  max-width: 900px; /* Allow wider content */
  width: 100%;
  padding: 20px;
  padding-top: 40px; /* Space for step indicator */
  text-align: center;
  position: relative; /* For step indicator */
}

/* Reuse panel style */
.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding);
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
    border-radius: 0;
}

.step-indicator {
    position: absolute;
    top: 10px;
    right: 15px;
    font-size: 0.9em;
    color: var(--color-log-system);
}

.step-content {
    margin-bottom: 20px;
}

.step-content h2 {
  font-size: 1.6em;
  color: var(--color-accent-secondary);
  margin-bottom: 15px;
  text-transform: uppercase;
}

.step-content p {
  font-size: 1.1em;
  line-height: 1.6;
  margin-bottom: 20px;
  color: var(--color-text);
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
}

.btn {
    margin: 5px;
     padding: 10px 20px;
     font-size: 1.1em;
}

.btn-skip {
    /* position: absolute;
    bottom: 15px;
    left: 15px; */
    font-size: 0.9em;
    padding: 6px 12px;
    margin-top: 15px;
    opacity: 0.8;
}

.btn-secondary {
    background-color: var(--color-log-system);
    color: var(--color-bg);
}
.btn-secondary:hover {
    background-color: gray;
}


.embedded-component {
    border: 1px dashed var(--color-border);
    padding: 15px;
    margin-top: 20px;
    margin-bottom: 20px;
    background-color: rgba(0,0,0,0.05); /* Slight bg tint */
}

/* Layout for profile/moveset step - REMOVED, handled by individual steps now */
/* .profile-moveset-layout { ... } */

.user-profile-embedded,
.moveset-manager-embedded {
    width: 100%;
    max-width: 750px; /* Limit width of embedded components */
    margin-left: auto; /* Center the component */
    margin-right: auto;
}

/* Specific styling adjustments for embedded components if needed */
:deep(.attack-creator-embedded .booster-header) {
    /* Example: Adjust header margin/padding if it looks odd */
     margin-top: -15px; 
}

:deep(.moveset-manager-embedded .manager-layout) {
     /* Example: Adjust layout for onboarding context */
     /* Maybe force a single column layout? */
}

.waiting-message {
    font-style: italic;
    color: var(--color-log-system);
    margin-top: 15px;
}

.complete-step p {
    font-size: 1.3em;
    color: var(--color-hp-high);
}

</style> 