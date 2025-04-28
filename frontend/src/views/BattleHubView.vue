<template>
  <div class="actions-panel panel">
     <!-- Action Feedback -->
     <div class="action-feedback">
        <p v-if="actionError" class="error-message">⚠️ {{ actionError }}</p>
        <p v-if="actionSuccessMessage" class="success-message">✅ {{ actionSuccessMessage }}</p>
     </div>
     <!-- 1. Loading state -->
     <div v-if="isLoadingActiveBattle" class="loading-placeholder">
         Checking battle status...
     </div>
     <!-- 2. Active Battle Display -->
     <ActiveBattleDisplay
         v-else-if="activeBattle && opponent" 
         :activeBattle="activeBattle"
         :opponent="opponent"
         @goToBattle="goToBattle"
     />
     <!-- 3. If NO active battle -->
     <div v-else class="no-active-battle-layout"> 
         <IncomingChallengesList
             :isLoading="isLoadingPendingBattles"
             :battles="pendingBattles"
             :respondingBattleId="respondingBattleId"
             @respond="handleResponse"
         />
         <AvailablePlayersList
             :isLoading="isLoadingUsers"
             :players="availableUsers"
             :challengingUserId="challengingUserId"
             @challenge="handleChallenge"
             @respond="handleResponse"
         />
     </div>
     <!-- === END === -->
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'; // Assuming onMounted is needed if fetching starts here
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useGameStore } from '@/stores/game';
import ActiveBattleDisplay from '@/components/ActiveBattleDisplay.vue';
import IncomingChallengesList from '@/components/IncomingChallengesList.vue';
import AvailablePlayersList from '@/components/AvailablePlayersList.vue';

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();

// State and Computed Props from HomeView related to Battle Panel
const user = computed(() => authStore.currentUser);
const availableUsers = computed(() => gameStore.users);
const pendingBattles = computed(() => gameStore.pendingBattles);
const activeBattle = computed(() => gameStore.activeBattle);
const isLoadingUsers = computed(() => gameStore.isLoadingUsers);
const isLoadingPendingBattles = computed(() => gameStore.isLoadingPendingBattles);
const isLoadingActiveBattle = computed(() => gameStore.isLoadingActiveBattle);
const actionError = computed(() => gameStore.actionError);
const actionSuccessMessage = computed(() => gameStore.actionSuccessMessage);

const challengingUserId = ref(null);
const respondingBattleId = ref(null);

const opponent = computed(() => {
    if (!activeBattle.value || !user.value) return null;
    return activeBattle.value.player1.id === user.value.id 
        ? activeBattle.value.player2 
        : activeBattle.value.player1;
});

// Event Handlers from HomeView
function goToBattle(battleId) {
    router.push({ name: 'battle', params: { id: battleId } });
}

async function handleChallenge(challengeData) {
    const { opponentId, fightAsBot } = challengeData;
    challengingUserId.value = opponentId;
    const result = await gameStore.challengeUser(opponentId, fightAsBot);
    challengingUserId.value = null;

    if (result && result.battleStarted && result.battle) {
      goToBattle(result.battle.id);
    }
}

async function handleResponse(battleId, responseAction) {
    respondingBattleId.value = battleId;
    const result = await gameStore.respondToBattle(battleId, responseAction);
    respondingBattleId.value = null;
    if (result.accepted && result.battle) {
        goToBattle(result.battle.id);
    }
}

// Consider if initial fetching needs to be triggered here or if HomeView still manages it.
// HomeView likely polls, so this might not be needed unless navigating directly here.
// onMounted(() => {
//   if (!activeBattle.value) { 
//      gameStore.fetchUsers();
//   }
// });

</script>

<style scoped>
/* Apply base panel styles if not inherited globally */
.panel {
    background-color: var(--color-panel-bg);
    border: var(--border-width) solid var(--color-border);
    padding: var(--panel-padding);
    box-shadow: inset 0 0 0 2px var(--color-bg), 3px 3px 0px var(--color-border);
    border-radius: 0;
    margin-bottom: var(--element-gap); /* Consistent spacing */
    font-family: var(--font-primary);
}

.actions-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem; /* Keep gap */
}

.action-feedback {
     /* Feedback messages styling */
     margin-bottom: 0;
     order: -1;
}

.error-message, .success-message { 
    padding: 8px 10px;
    border-radius: 0;
    font-weight: normal;
    text-align: center;
    margin-bottom: 10px; 
    border: 1px solid;
    font-size: 0.9em;
}
.error-message {
  background-color: rgba(233, 69, 96, 0.1); /* Use theme colors */
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.success-message {
  background-color: rgba(53, 208, 104, 0.1);
  color: var(--color-hp-high);
  border-color: var(--color-hp-high);
}

/* Generic Loading Placeholder style */
.loading-placeholder {
    padding: 20px;
    text-align: center;
    color: var(--color-log-system);
    font-style: italic;
    border-radius: 0;
    border: 1px dashed var(--color-border);
    background-color: var(--color-bg); /* Match inner bg */
    text-transform: uppercase;
}

.no-active-battle-layout {
    display: flex;
    flex-direction: column;
    gap: 1rem; 
}
</style> 