===========================
Lua Scripting Reference
===========================

The game uses Lua scripting via the `lupa`_ library to allow for flexible and custom attack effects beyond simple damage or stat changes. Scripts are associated with :class:`~game.models.Attack` objects and are executed at specific points during the battle flow.

.. _lupa: https://github.com/scoder/lupa

Battle Log System
-----------------

Scripts can interact with the battle log to provide player-facing information about what's happening.

Log Types
~~~~~~~~~

The core Python functions (`apply_std_damage`, `apply_std_hp_change`, etc.) automatically generate log entries when they successfully modify game state. These logs include details like damage dealt, HP change amounts, or stat stage modifications.

Scripts can also generate their own custom log entries using the `log()` API function. These are useful for indicating the start or end of custom effects, or providing specific feedback.

Each log entry has the following structure (simplified):

*   **source**: ``'player1'``, ``'player2'``, or ``'system'``
*   **text**: The message displayed to the user.
*   **effect_type**: A category for the log (e.g., ``'action'``, ``'damage'``, ``'heal'``, ``'stat_change'``, ``'status_change'``, ``'info'``, ``'error'``).
*   **effect_details**: (Optional) A dictionary with more specific data (e.g., ``{'mod': 1, 'stat': 'attack'}`` for a stat change).

Calling `log()` in Lua
~~~~~~~~~~~~~~~~~~~~~

The primary way to add custom log entries from Lua is via the ``log()`` API function.

.. code-block:: lua

   log(message, effect_type, target_role_for_source)

*   ``message`` (string): The text to display.
*   ``effect_type`` (string, optional): The category (defaults to ``'info'``).
*   ``target_role_for_source`` (string, optional): If provided (e.g., ``TARGET_ROLE``), the log source will be attributed to that player. If omitted, the source defaults to ``'script'`` or potentially ``'system'`` depending on the API function that called `log` internally.

**Example:**

.. code-block:: lua

   log("Poison took hold!", "status_change", TARGET_ROLE)
   log("The poison wore off.", "info", SCRIPT_TARGET_ROLE)

Frontend Display
~~~~~~~~~~~~~~~

In ``BattleView.vue``, the ``battle.last_turn_summary`` array (which contains all log entries) is iterated over. Each entry is displayed as a chat bubble:

*   The ``source`` determines alignment (user left, opponent right, system center).
*   The ``text`` is displayed inside the bubble.
*   The ``effect_type`` and ``effect_details`` can be used to apply specific CSS classes (e.g., `bubble-effect-damage`, `bubble-stat-attack`) for visual styling, like adding icons (▲/▼ for stat changes) or changing bubble colors.

Lua API Functions
-----------------

These Python functions are exposed to the Lua environment via the `LUA_API` dictionary and can be called directly from Lua scripts.

Utility Functions
~~~~~~~~~~~~~~~~~

*   ``log(message, effect_type?, source_role?)``
    *   Adds a custom message to the battle log.
*   ``unregister_script(registration_id)``
    *   Removes a persistent script instance from the battle state, preventing it from triggering again. Use ``CURRENT_REGISTRATION_ID`` to unregister the currently running script.
*   ``get_stat_stage(role, stat_name)``
    *   Returns the current stat stage (integer) for the given role ('player1' or 'player2') and stat ('attack', 'defense', 'speed').
*   ``get_max_hp(role)``
    *   Returns the maximum HP for the specified player role.
*   ``get_turn_number()``
    *   Returns the current battle turn number.
*   ``get_battle_status()``
    *   Returns the battle status string ('active', 'finished', etc.).
*   ``get_player_name(role)``
    *   Returns the username string for the specified player role.
*   ``get_player_id(role)``
    *   Returns the database ID (integer) for the specified player role.
*   ``get_log_entries()``
    *   Returns a Lua table representing the list of log entries generated *so far within the current script execution*. Useful for checking previous actions within the same script.
*   ``find_log_entry(filters_table)``
    *   Searches the logs generated *so far within the current script execution* for the first entry matching the filters. Filters is a Lua table, e.g., ``{source='system', effect_type='damage'}``. Returns the log entry table or nil.
*   ``is_script_registered(filters_table)``
    *   Checks the battle's *current full list* of registered scripts for an entry matching the filters. Filters is a Lua table, e.g., ``{name='My Script Name', target_role=TARGET_ROLE}``. Returns true or false.

Effect Functions
~~~~~~~~~~~~~~~

*   ``apply_std_damage(base_power, target_role?)``
    *   Calculates damage based on standard formula (Attack vs Defense, stages, variance) and applies it. Defaults target to ``TARGET_ROLE``. Logs damage taken.
*   ``apply_std_hp_change(hp_change, target_role?)``
    *   Directly adds/removes HP. Positive for heal, negative for damage/cost. Defaults target to ``ATTACKER_ROLE``. Logs HP change.
*   ``apply_std_stat_change(stat, mod, target_role?)``
    *   Changes a stat stage ('attack', 'defense', 'speed') by the modifier amount (`mod`, e.g., +1, -2). Defaults target to ``ATTACKER_ROLE``. Logs the change or if the stat was already at the limit.
*   ``apply_std_momentum_change(momentum_change, target_role?)``
    *   Directly adds/removes momentum. Defaults target to ``TARGET_ROLE``. Logs the change.

Custom Status Functions
~~~~~~~~~~~~~~~~~~~~~~~

*   ``get_custom_status(role, status_name)``
    *   Retrieves the value of a custom status for the given role. Returns the value (any type) or nil.
*   ``has_custom_status(role, status_name)``
    *   Checks if the given role has the specified custom status key. Returns true or false.
*   ``set_custom_status(role, status_name, value)``
    *   Sets or updates a custom status key-value pair for the given role. Logs the change.
*   ``remove_custom_status(role, status_name)``
    *   Removes a custom status key from the given role. Logs the removal.
*   ``modify_custom_status(role, status_name, change)``
    *   Adds a numeric `change` to an existing numeric custom status. If the status doesn't exist, sets it to `change`. Logs the change.

Lua Global Variables
--------------------

These variables are automatically available in the Lua script environment:

*   ``PLAYER1_ROLE`` (string): Always 'player1'.
*   ``PLAYER2_ROLE`` (string): Always 'player2'.
*   ``ATTACKER_ROLE`` (string): The role ('player1' or 'player2') of the player whose turn it currently is when the script executes.
*   ``TARGET_ROLE`` (string): The role of the *opponent* of the current turn player.
*   ``SCRIPT_TARGET_ROLE`` (string): The role ('player1' or 'player2') that this specific script instance is targeting, based on its registration (e.g., who the poison tick is applied to).
*   ``ORIGINAL_ATTACKER_ROLE`` (string): The role of the player who used the Attack that *originally registered* this script instance.
*   ``ORIGINAL_TARGET_ROLE`` (string): The role of the player who was targeted by the Attack that *originally registered* this script instance.
*   ``CURRENT_TRIGGER`` (string): The trigger type that caused this script to execute (e.g., 'on_attack', 'after_target_turn').
*   ``CURRENT_TURN`` (number): The current battle turn number.
*   ``CURRENT_REGISTRATION_ID`` (string): The unique ID assigned to this specific persistent script instance when it was registered. Used with ``unregister_script()``.
*   ``SCRIPT_START_TURN`` (number): The turn number on which this persistent script instance was originally registered.
*   ``P1_HP`` (number): Current HP of player1 (provided for convenience, might be slightly stale if modified earlier in the same script execution).
*   ``P2_HP`` (number): Current HP of player2 (provided for convenience).
