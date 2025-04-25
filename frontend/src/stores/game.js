import { defineStore } from 'pinia';
import { ref } from 'vue';
import apiClient from '@/services/api';
import { useAuthStore } from './auth'; // To access user info if needed
import { fetchMyStats as apiFetchMyStats, fetchLeaderboard as apiFetchLeaderboard } from '@/services/api';

export const useGameStore = defineStore('game', () => {
  // --- State --- 
  const users = ref([]); // List of other users available to challenge
  const pendingBattles = ref([]); // List of battles awaiting response from logged-in user
  const activeBattle = ref(null); // Will hold full battle details if active
  // NEW: Track outgoing challenges { opponentId: battleId }
  const outgoingPendingChallenges = ref(JSON.parse(sessionStorage.getItem('outgoingPendingChallenges') || '{}')); 
  const isLoadingUsers = ref(false);
  const isLoadingPendingBattles = ref(false);
  const isLoadingActiveBattle = ref(false); // Added loading state
  const actionError = ref(null); // General error for challenge/respond actions
  const actionSuccessMessage = ref(null);
  const battleError = ref(null); // Specific error for battle actions
  const battleMessage = ref(null); // Specific message for battle updates
  const turnSummary = ref([]); // Store turn summary messages
  const isConceding = ref(false); // Added state for concede loading

  // NEW: Leaderboard State
  const myStats = ref(null);
  const leaderboardData = ref([]);
  const isLoadingMyStats = ref(false);
  const isLoadingLeaderboard = ref(false);
  const leaderboardError = ref(null);

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
  async function challengeUser(opponentId, fightAsBot = false) {
    actionError.value = null;
    actionSuccessMessage.value = null;
    try {
      // Include fight_as_bot in the request payload
      const payload = { 
        opponent_id: opponentId,
        fight_as_bot: fightAsBot
      };
      const response = await apiClient.post('/game/battles/initiate/', payload);
      
      // Check response for immediate battle start (when fighting as bot)
      if (response.data.battle && response.data.battle.status === 'active') {
        actionSuccessMessage.value = response.data.message; // e.g., "Battle with Bot started!"
        activeBattle.value = response.data.battle; // Set active battle immediately
        // Clear any potential outgoing challenge entry for this opponent
        delete outgoingPendingChallenges.value[opponentId];
        sessionStorage.setItem('outgoingPendingChallenges', JSON.stringify(outgoingPendingChallenges.value));
        console.log('AI Battle started:', response.data);
        // Need to navigate user to battle view from the component that called this
        return { battleStarted: true, battle: response.data.battle };
      } else {
        // Normal pending challenge - store the battle ID
        const battleId = response.data.battle_id;
        if (battleId) {
             outgoingPendingChallenges.value[opponentId] = battleId;
             sessionStorage.setItem('outgoingPendingChallenges', JSON.stringify(outgoingPendingChallenges.value)); // Persist briefly
        } else {
            console.warn('Pending challenge initiated but no battle_id received in response.');
        }
        actionSuccessMessage.value = `Challenge sent to user ${opponentId}!`; 
        console.log('Challenge sent:', response.data);
        return { battleStarted: false };
      }
    } catch (error) {
      console.error('Failed to initiate battle:', error.response?.data || error.message);
      actionError.value = error.response?.data?.error || 'Failed to send challenge.';
      return { error: true };
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
      
      // Clear any potential outgoing challenge entry if the user responded (less likely scenario)
      const respondedBattle = response.data.battle;
      if (respondedBattle) {
         const opponentId = respondedBattle.player1.id === useAuthStore().currentUser?.id ? respondedBattle.player2.id : respondedBattle.player1.id;
         if (outgoingPendingChallenges.value[opponentId] === battleId) {
            delete outgoingPendingChallenges.value[opponentId];
            sessionStorage.setItem('outgoingPendingChallenges', JSON.stringify(outgoingPendingChallenges.value));
         }
      }

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
          // --- REMOVE DEBUG LOGGING ---
          // console.log(`[fetchActiveBattle Polling=${isPolling}] Status: ${response.status}, Data:`, JSON.stringify(response.data));
          // --- END REMOVE DEBUG ---
          const oldBattleState = JSON.stringify(activeBattle.value);
          const newBattleState = JSON.stringify(response.data);
          // --- REMOVE DEBUG LOGGING ---
          const changed = oldBattleState !== newBattleState;
          // console.log(`[fetchActiveBattle Polling=${isPolling}] State changed? ${changed}`);
          // --- END REMOVE DEBUG ---
          // Only update if state actually changed to avoid needless reactivity triggers
          if (changed) {
              // console.log(`[fetchActiveBattle Polling=${isPolling}] Updating activeBattle.value`); // REMOVE DEBUG
              activeBattle.value = response.data;
              // If a battle became active, clear any related outgoing challenge
              if (activeBattle.value) {
                 const opponentId = activeBattle.value.player1.id === useAuthStore().currentUser?.id ? activeBattle.value.player2.id : activeBattle.value.player1.id;
                 if (outgoingPendingChallenges.value[opponentId] === activeBattle.value.id) {
                     delete outgoingPendingChallenges.value[opponentId];
                     sessionStorage.setItem('outgoingPendingChallenges', JSON.stringify(outgoingPendingChallenges.value));
                 }
              }
          }
      } catch (error) {
          // --- REMOVE DEBUG LOGGING ---
          const status = error.response ? error.response.status : 'N/A';
          // console.log(`[fetchActiveBattle Polling=${isPolling}] Error Status: ${status}`, error.message);
          // --- END REMOVE DEBUG ---
          if (error.response && error.response.status === 404) {
               // --- REMOVE DEBUG LOGGING ---
              if (activeBattle.value !== null) {
                 // console.log(`[fetchActiveBattle Polling=${isPolling}] Clearing activeBattle.value due to 404`); // REMOVE DEBUG
                  // Battle not active, check if we had an outgoing challenge for the player
                  // who was in the now-inactive battle (if activeBattle.value had data)
                  // THIS LOGIC IS GETTING COMPLEX - maybe rely on explicit cancel for now.
                 activeBattle.value = null;
              }
               // --- END REMOVE DEBUG ---
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

  // --- NEW: Leaderboard Actions ---

  async function fetchMyStats() {
    isLoadingMyStats.value = true;
    leaderboardError.value = null;
    try {
      const response = await apiFetchMyStats(); // Use imported function
      myStats.value = response.data;
    } catch (error) {
      console.error('Failed to fetch user stats:', error.response?.data || error.message);
      leaderboardError.value = 'Could not load your stats.';
      myStats.value = null;
    } finally {
      isLoadingMyStats.value = false;
    }
  }

  async function fetchLeaderboard() {
    isLoadingLeaderboard.value = true;
    leaderboardError.value = null;
    try {
      const response = await apiFetchLeaderboard(); // Use imported function
      // Sort leaderboard by wins descending, then username ascending
      leaderboardData.value = response.data.sort((a, b) => {
        if (b.total_wins !== a.total_wins) {
            return b.total_wins - a.total_wins; // Higher wins first
        }
        return a.username.localeCompare(b.username); // Then alphabetical
      });
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error.response?.data || error.message);
      leaderboardError.value = 'Could not load leaderboard.';
      leaderboardData.value = [];
    } finally {
      isLoadingLeaderboard.value = false;
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

  // --- REMOVED: Attack Generation Actions ---

  // Generate new attacks based on concept (and optionally favorites)
  async function generateAttacks(concept, favorite_attack_ids = []) { // Updated signature
    // isLoading can be handled by the component calling this
    try {
      const payload = {
        concept: concept,
        favorite_attack_ids: favorite_attack_ids
      };
          const response = await apiClient.post('/game/attacks/generate/', payload);
      // The response should contain the newly generated attacks and a success message
      // It might implicitly update the user's credits via the auth store refresh in the component
      return response.data; // Return the response { message: '...', attacks: [...] }
      } catch (error) {
      console.error('Failed to generate attacks:', error.response?.data || error.message);
      const errorMessage = error.response?.data?.error || 'Failed to open booster.';
      // Throw the error so the component can catch it and display it
      throw new Error(errorMessage); 
    }
  }

  // --- NEW: Cancel outgoing challenge --- 
  async function cancelChallenge(battleId) {
    actionError.value = null;
    actionSuccessMessage.value = null;
    try {
      await apiClient.post(`/game/battles/${battleId}/cancel/`);
      actionSuccessMessage.value = 'Challenge cancelled.';
      // Remove from local tracking
      const opponentId = Object.keys(outgoingPendingChallenges.value).find(
          key => outgoingPendingChallenges.value[key] === battleId
      );
      if (opponentId) {
          delete outgoingPendingChallenges.value[opponentId];
          sessionStorage.setItem('outgoingPendingChallenges', JSON.stringify(outgoingPendingChallenges.value));
      }
      return true;
    } catch (error) {
      console.error('Failed to cancel challenge:', error.response?.data || error.message);
      actionError.value = error.response?.data?.error || 'Failed to cancel challenge.';
      return false;
    }
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

    // NEW: Leaderboard State Exports
    myStats,
    leaderboardData,
    isLoadingMyStats,
    isLoadingLeaderboard,
    leaderboardError,

    // NEW: Track outgoing challenges { opponentId: battleId }
    outgoingPendingChallenges,

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

    // NEW: Leaderboard Actions Exports
    fetchMyStats, // New action
    fetchLeaderboard, // New action
    generateAttacks, // <-- Export updated action
    cancelChallenge, // <-- Export new action
  };
}); 