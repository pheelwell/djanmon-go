import { defineStore } from 'pinia';
import { ref } from 'vue';
import apiClient from '@/services/api';
import { useAuthStore } from './auth'; // To access user info if needed

export const useGameStore = defineStore('game', () => {
  // --- State --- 
  const users = ref([]); // List of other users available to challenge
  const pendingBattles = ref([]); // List of battles awaiting response from logged-in user
  const activeBattle = ref(null); // Will hold full battle details if active
  const isLoadingUsers = ref(false);
  const isLoadingPendingBattles = ref(false);
  const isLoadingActiveBattle = ref(false); // Added loading state
  const actionError = ref(null); // General error for challenge/respond actions
  const actionSuccessMessage = ref(null);
  const battleError = ref(null); // Specific error for battle actions
  const battleMessage = ref(null); // Specific message for battle updates
  const turnSummary = ref([]); // Store turn summary messages
  const isConceding = ref(false); // Added state for concede loading

  // --- Actions --- 

  // Fetch users (excluding self)
  async function fetchUsers(isPolling = false) {
    if (!isPolling) {
        isLoadingUsers.value = true;
        actionError.value = null;
    }
    try {
      const response = await apiClient.get('/users/');
      if (JSON.stringify(users.value) !== JSON.stringify(response.data)) {
          users.value = response.data;
      }
    } catch (error) {
      if (!isPolling || !error.response) { 
          console.error('Failed to fetch users:', error.response?.data || error.message);
          actionError.value = 'Could not load users.';
          users.value = []; 
      }
    } finally {
      if (!isPolling) {
          isLoadingUsers.value = false;
      }
    }
  }

  // Fetch pending battle requests for the logged-in user
  async function fetchPendingBattles(isPolling = false) {
    if (!isPolling) {
        isLoadingPendingBattles.value = true;
        actionError.value = null;
    }
    try {
      const response = await apiClient.get('/game/battles/requests/');
      if (JSON.stringify(pendingBattles.value) !== JSON.stringify(response.data)) {
          pendingBattles.value = response.data;
      }
    } catch (error) {
      if (!isPolling || !error.response) {
          console.error('Failed to fetch pending battles:', error.response?.data || error.message);
          actionError.value = 'Could not load pending battles.';
          pendingBattles.value = [];
      }
    } finally {
      if (!isPolling) {
          isLoadingPendingBattles.value = false;
      }
    }
  }

  // Initiate a battle challenge
  async function challengeUser(opponentId) {
    actionError.value = null;
    actionSuccessMessage.value = null;
    try {
      const response = await apiClient.post('/game/battles/initiate/', { opponent_id: opponentId });
      // Maybe update UI slightly, show success message
      actionSuccessMessage.value = `Challenge sent to user ${opponentId}!`; 
      // No need to add to pendingBattles here, the opponent will see it.
      console.log('Challenge response:', response.data);
      return true;
    } catch (error) {
      console.error('Failed to initiate battle:', error.response?.data || error.message);
      actionError.value = error.response?.data?.error || 'Failed to send challenge.';
      return false;
    }
  }

  // Respond to a battle request
  async function respondToBattle(battleId, responseAction) { // responseAction: 'accept' or 'decline'
    actionError.value = null;
    actionSuccessMessage.value = null;
    try {
      const response = await apiClient.post(`/game/battles/${battleId}/respond/`, { action: responseAction });
      actionSuccessMessage.value = `Battle request ${responseAction}ed.`;
      // Remove the battle from the pending list
      pendingBattles.value = pendingBattles.value.filter(b => b.id !== battleId);
      
      // If accepted, set the active battle state immediately from response
      if (responseAction === 'accept' && response.data.battle) {
         console.log('Battle accepted, setting active battle state:', response.data.battle);
         activeBattle.value = response.data.battle; 
         // TODO: Need to navigate user to the battle view from the component
         return { accepted: true, battle: response.data.battle }; // Return battle data
      }
       return { accepted: false };
    } catch (error) {
      console.error(`Failed to ${responseAction} battle:`, error.response?.data || error.message);
      actionError.value = error.response?.data?.error || `Failed to ${responseAction} challenge.`;
      return { accepted: false, error: true };
    }
  }

  // Fetch active battle (Updated to clear battle-specific messages)
  async function fetchActiveBattle(isPolling = false) {
      if (!isPolling) {
          isLoadingActiveBattle.value = true;
          // Clear previous battle-specific state only on non-polling fetch
          battleError.value = null; 
          battleMessage.value = null;
          turnSummary.value = [];
      }
      try {
          const response = await apiClient.get('/game/battles/active/');
          const oldBattleState = JSON.stringify(activeBattle.value);
          const newBattleState = JSON.stringify(response.data);
          // Only update if state actually changed to avoid needless reactivity triggers
          if (oldBattleState !== newBattleState) { 
              activeBattle.value = response.data;
          }
      } catch (error) {
          if (error.response && error.response.status === 404) {
              activeBattle.value = null;
          } else {
              console.error('Failed to fetch active battle:', error.response?.data || error.message);
              // Maybe set a specific error if needed, but avoid overwriting actionError
          }
      } finally {
           if (!isPolling) {
                isLoadingActiveBattle.value = false;
           }
      }
  }

  // Submit an action for the current battle turn (Updated for Momentum logic)
  async function submitBattleAction(battleId, attackId) {
    battleError.value = null;
    battleMessage.value = 'Submitting action...';
    try {
      const response = await apiClient.post(`/game/battles/${battleId}/action/`, { attack_id: attackId });
      battleMessage.value = response.data.message; 
      
      // Always update the battle state from the response
      if (response.data.battle_state) {
          activeBattle.value = response.data.battle_state;
          // Optional: Check status in response and clear message if finished?
          if (response.data.battle_state.status === 'finished') {
              battleMessage.value = "Battle Finished!";
          }
      } else {
          // Fallback or error handling if battle_state is missing
          console.warn('Battle state missing from action response', response.data);
          // Fetch manually as a fallback? 
          // await fetchBattleById(battleId); 
      }
      return true;
    } catch (error) {
        console.error('Battle action failed:', error.response?.data || error.message);
        battleError.value = error.response?.data?.error || 'Failed to submit action.';
        battleMessage.value = null;
        return false;
    }
  }

 // Fetch Battle by ID (Added for potentially refreshing BattleView directly)
 async function fetchBattleById(battleId) {
     isLoadingActiveBattle.value = true; // Reuse loading state for simplicity
     battleError.value = null;
     battleMessage.value = null;
     turnSummary.value = [];
     try {
         const response = await apiClient.get(`/game/battles/${battleId}/`);
         // Update activeBattle only if it matches the requested ID 
         // or if there's no current active battle set
         if (!activeBattle.value || activeBattle.value.id === response.data.id) {
            activeBattle.value = response.data; 
         }
         return response.data; // Return fetched data
     } catch (error) {
         console.error(`Failed to fetch battle ${battleId}:`, error.response?.data || error.message);
         battleError.value = "Could not load battle details.";
         if (activeBattle.value && activeBattle.value.id === parseInt(battleId)) {
             activeBattle.value = null; // Clear if active battle failed to load
         }
         throw error; // Re-throw for component handling
     } finally {
         isLoadingActiveBattle.value = false;
     }
 }

  // Concede the current battle
  async function concedeBattle(battleId) {
      isConceding.value = true;
      battleError.value = null;
      battleMessage.value = 'Conceding...';
      turnSummary.value = []; 
      try {
          const response = await apiClient.post(`/game/battles/${battleId}/concede/`);
          // Update battle state with the final state from response
          activeBattle.value = response.data.final_state;
          battleMessage.value = response.data.message; // e.g., "You conceded. Opponent wins!"
          // Turn summary might not be relevant on concede, but clear it
          turnSummary.value = []; 
          return true;
      } catch (error) {
          console.error('Concede failed:', error.response?.data || error.message);
          battleError.value = error.response?.data?.error || 'Failed to concede.';
          battleMessage.value = null;
          return false;
      } finally {
          isConceding.value = false;
      }
  }

  // --- Helpers --- 
  function clearMessages() {
      actionError.value = null;
      actionSuccessMessage.value = null;
      battleError.value = null;
      battleMessage.value = null;
      // turnSummary.value = []; // Decide if this should be cleared here
  }

  return {
    // State
    users,
    pendingBattles,
    activeBattle,
    isLoadingUsers,
    isLoadingPendingBattles,
    isLoadingActiveBattle, // Exported loading state
    actionError,
    actionSuccessMessage,
    battleError, // Battle view errors
    battleMessage, // Battle view messages
    turnSummary, // Battle turn summary
    isConceding, // Export loading state

    // Actions
    fetchUsers,
    fetchPendingBattles,
    challengeUser,
    respondToBattle,
    fetchActiveBattle,
    submitBattleAction, // Added action
    fetchBattleById, // Added action
    concedeBattle, // Export new action
    clearMessages,
  };
}); 