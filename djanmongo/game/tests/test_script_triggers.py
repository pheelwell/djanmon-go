import os
import json
import random
from django.test import TestCase
from django.utils import timezone
from django.conf import settings # To get AUTH_USER_MODEL

from users.models import User
from game.models import Attack, Script, Battle
from game.battle_logic import apply_attack

# Define the log file path (e.g., in the project root)
# LOG_FILE_PATH = os.path.join(settings.BASE_DIR, "script_trigger_test_log.txt") # REMOVED

class ScriptTriggerTest(TestCase):
    """
    Tests each Lua script trigger point individually by simulating short battles
    and asserting the expected log message appears.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user1 = User.objects.create_user(username='trigger_test_user1', password='password', hp=100, attack=10, defense=10, speed=10)
        cls.user2 = User.objects.create_user(username='trigger_test_user2', password='password', hp=100, attack=10, defense=10, speed=10)

        # Clear the log file at the start of the test suite run
        # if os.path.exists(LOG_FILE_PATH):
        #    os.remove(LOG_FILE_PATH) # REMOVED

    def _run_battle_simulation(self, battle, test_attack, num_turns=3): # Default to 3 turns
        """Simulates turns for a given battle, focusing on the test_attack."""
        all_logs = []
        current_turn = 1
        
        # Ensure both players have only the test attack selected for simplicity
        self.user1.selected_attacks.set([test_attack])
        self.user2.selected_attacks.set([test_attack])

        while battle.status == 'active' and current_turn <= num_turns:
            if battle.whose_turn == 'player1':
                attacker = self.user1
            else:
                attacker = self.user2

            attack_to_use = test_attack
            
            try:
                turn_logs, battle_ended = apply_attack(battle, attacker, attack_to_use)
                all_logs.extend(turn_logs)
                if battle_ended:
                    break
            except Exception as e:
                print(f"!!! EXCEPTION during apply_attack on Turn {current_turn}: {e}")
                all_logs.append({"source": "TEST_ERROR", "text": f"Exception applying {attack_to_use.name}: {e}", "effect_type": "error"})
                break # Stop simulation on error

            current_turn += 1
            battle.refresh_from_db()

        return all_logs

    def _assert_log_contains(self, logs, expected_text_fragment):
        """Helper assertion to check if any log entry contains the expected text."""
        found = any(expected_text_fragment in entry.get('text', '') 
                    for entry in logs if isinstance(entry, dict))
        self.assertTrue(found, f"Expected log containing '{expected_text_fragment}' not found.")

    def test_script_triggers(self):
        """
        Iterates through trigger types, creates specific attacks/scripts,
        runs simulations, and asserts the correct trigger log appears.
        """
        trigger_fields = [
            'trigger_on_attack',
            'trigger_before_attacker_turn',
            'trigger_after_attacker_turn',
            'trigger_before_target_turn',
            'trigger_after_target_turn',
        ]

        for trigger_field in trigger_fields:
            # Use subtests to isolate failures per trigger
            with self.subTest(trigger=trigger_field):
                print(f"\n--- Testing Trigger: {trigger_field} ---")
                
                # 1. Create unique Attack and Script for this trigger
                attack_name = f"TestAttack_{trigger_field}"
                script_name = f"TestScript_{trigger_field}"
                
                # Lua code to log which trigger fired
                # Construct the Lua code string ensuring Lua does the concatenation
                trigger_name = trigger_field # Get the Python string value
                # Simplified log message just containing the trigger name for easier assertion
                lua_code = f'log("SCRIPT_TEST_FIRED: {trigger_name}")' 

                script_kwargs = {field: (field == trigger_field) for field in trigger_fields}
                
                test_attack = Attack.objects.create(
                    name=attack_name, 
                    description=f"Attack to test {trigger_field}",
                    momentum_cost=10
                )
                
                test_script = Script.objects.create(
                    attack=test_attack,
                    name=script_name,
                    lua_code=lua_code,
                    **script_kwargs
                )
                print(f"  Created Attack '{attack_name}' and Script '{script_name}' with {trigger_field}=True")

                # 2. Set up Battle
                battle = Battle.objects.create(player1=self.user1, player2=self.user2, status='active')
                battle.initialize_battle_state() 
                print(f"  Created Battle {battle.id}. Initial Turn: {battle.turn_number}, Starts: {battle.whose_turn}")

                # 3. Run Simulation (3 turns)
                battle_logs = self._run_battle_simulation(battle, test_attack)
                print(f"  Simulation finished. Collected {len(battle_logs)} log entries.")

                # 4. Assert log presence
                expected_log_fragment = f"SCRIPT_TEST_FIRED: {trigger_field}"
                self._assert_log_contains(battle_logs, expected_log_fragment)
                print(f"  Assertion Passed: Found log for {trigger_field}.")

            # No file writing needed
            # try:
            #    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            # ... (removed file writing code) ...
            # except Exception as e:
            #    print(f"!!! ERROR writing logs to file for {trigger_field}: {e}")

            # DB automatically rolled back by TestCase

            # Clean up battle (optional, TestCase rollback handles DB)
            # battle.delete() 
            # test_attack.delete() # Deleting attack cascades to script 