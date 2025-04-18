from django.core.management.base import BaseCommand
from game.models import Attack, Script
import textwrap # For dedenting Lua scripts

class Command(BaseCommand):
    help = 'Adds or updates a predefined set of attacks and their scripts in the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Adding/Updating Attacks and Scripts...'))

        attacks_data = [
            # --- Basic Damage Attacks ---
            {
                'name': 'Quick Jab', 
                'description': 'A very fast jab, low impact.', 
                'emoji': '⚡', 
                'momentum_cost': 10,
                'scripts': [
                    {
                        'name': 'Quick Jab Damage', # Unique script name
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_damage(5, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Punch', 
                'description': 'A standard punch.', 
                'emoji': '👊', 
                'momentum_cost': 20,
                'scripts': [
                    {
                        'name': 'Punch Damage',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_damage(10, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Heavy Slam', 
                'description': 'A slow, powerful slam.', 
                'emoji': '🏋️', 
                'momentum_cost': 40,
                'scripts': [
                    {
                        'name': 'Heavy Slam Damage',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_damage(18, TARGET_ROLE)
                """),
                    }
                ]
            },

            # --- Single Stat Buffs (Self) ---
            {
                'name': 'Bulk Up', 
                'description': "Raises User's Attack.", 
                'emoji': '💪', 
                'momentum_cost': 30,
                'scripts': [
                    {
                        'name': 'Bulk Up Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('attack', 1, ATTACKER_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Iron Defense', 
                'description': "Raises User's Defense.", 
                'emoji': '🛡️', 
                'momentum_cost': 30,
                 'scripts': [
                    {
                        'name': 'Iron Defense Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('defense', 1, ATTACKER_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Agility', 
                'description': "Raises User's Speed.", 
                'emoji': '💨', 
                'momentum_cost': 30,
                 'scripts': [
                    {
                        'name': 'Agility Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('speed', 1, ATTACKER_ROLE)
                """),
                    }
                ]
            },

            # --- Single Stat Debuffs (Enemy) ---
            {
                'name': 'Leer', 
                'description': "Lowers Enemy's Defense.", 
                'emoji': '😠', 
                'momentum_cost': 20,
                'scripts': [
                    {
                        'name': 'Leer Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('defense', -1, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Growl', 
                'description': "Lowers Enemy's Attack.", 
                'emoji': '🗣️', 
                'momentum_cost': 20,
                 'scripts': [
                    {
                        'name': 'Growl Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('attack', -1, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Scary Face', 
                'description': "Lowers Enemy's Speed.", 
                'emoji': '😨', 
                'momentum_cost': 20,
                 'scripts': [
                    {
                        'name': 'Scary Face Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('speed', -1, TARGET_ROLE)
                """),
                    }
                ]
            },

            # --- Damage + Debuff (Enemy) ---
            {
                'name': 'Acid Spray', 
                'description': "Damages and lowers Enemy's Defense.", 
                'emoji': '🧪', 
                'momentum_cost': 30,
                'scripts': [
                    {
                        'name': 'Acid Spray Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_damage(7, TARGET_ROLE)
                    apply_std_stat_change('defense', -1, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Weakening Voice', 
                'description': "Damages and lowers Enemy's Attack.", 
                'emoji': '🎶', 
                'momentum_cost': 30,
                'scripts': [
                    {
                        'name': 'Weakening Voice Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_damage(7, TARGET_ROLE)
                    apply_std_stat_change('attack', -1, TARGET_ROLE)
                """),
                    }
                ]
            },
            
            # --- Healing (Self) ---
            {
                'name': 'Recover', 
                'description': 'Heals a good amount of HP.', 
                'emoji': '❤️‍🩹', 
                'momentum_cost': 40,
                'scripts': [
                    {
                        'name': 'Recover Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_hp_change(30, ATTACKER_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Rest', 
                'description': 'Heals a small amount of HP.', 
                'emoji': '💤', 
                'momentum_cost': 20,
                'scripts': [
                    {
                        'name': 'Rest Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_hp_change(15, ATTACKER_ROLE)
                """),
                    }
                ]
            },

            # --- Stronger Stat Changes (+/- 2) ---
            {
                'name': 'Extreme Speed', 
                'description': "Greatly raises User's Speed.", 
                'emoji': '🚀', 
                'momentum_cost': 50,
                'scripts': [
                    {
                        'name': 'Extreme Speed Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('speed', 2, ATTACKER_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Charm', 
                'description': "Greatly lowers Enemy's Attack.", 
                'emoji': '🥺', 
                'momentum_cost': 40,
                'scripts': [
                    {
                        'name': 'Charm Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('attack', -2, TARGET_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Barrier', 
                'description': "Greatly raises User's Defense.", 
                'emoji': '🧱', 
                'momentum_cost': 50,
                'scripts': [
                    {
                        'name': 'Barrier Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('defense', 2, ATTACKER_ROLE)
                """),
                    }
                ]
            },
            {
                'name': 'Metal Sound', 
                'description': "Greatly lowers Enemy's Defense.", 
                'emoji': '⚙️', 
                'momentum_cost': 40,
                'scripts': [
                    {
                        'name': 'Metal Sound Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                    apply_std_stat_change('defense', -2, TARGET_ROLE)
                """),
                    }
                ]
            },
            {   # Keep Taunt example
                'name': 'Taunt',
                'description': "Lowers the target's Attack but raises their Defense.",
                'emoji': '🤪',
                'momentum_cost': 25,
                'scripts': [
                    {
                        'name': 'Taunt Effect',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                            apply_std_stat_change('attack', -1, TARGET_ROLE)
                            apply_std_stat_change('defense', 1, TARGET_ROLE)
                        """),
                    }
                ]
            },
            
            # --- NEW DEBUGGER ATTACK --- 
            {
                 'name': 'Debugger',
                 'description': 'Logs context and applies various effects for testing.',
                 'emoji': '🐛',
                 'momentum_cost': 5,
                 'scripts': [
                     { # On Attack
                         'name': 'Debugger On Attack',
                         'trigger_on_attack': True,
                         'lua_code': textwrap.dedent("""
                             apply_std_damage(1, TARGET_ROLE)
                             apply_std_stat_change('attack', 1, ATTACKER_ROLE)
                             set_custom_status(ATTACKER_ROLE, 'DebugStatus', true)
                         """),
                     },
                     { # Before Attacker Turn
                         'name': 'Debugger Before Attacker Turn (Regen)',
                         'trigger_before_attacker_turn': True,
                         'lua_code': textwrap.dedent("""
                             apply_std_hp_change(5, SCRIPT_TARGET_ROLE)
                         """),
                     },
                     { # After Target Turn
                         'name': 'Debugger After Target Turn (Poison Tick)',
                         'trigger_after_target_turn': True,
                         'lua_code': textwrap.dedent("""
                             local start_turn = SCRIPT_START_TURN
                             if CURRENT_TURN <= start_turn + 2 then 
                                 apply_std_hp_change(-2, SCRIPT_TARGET_ROLE)
                             end
                             remove_custom_status(ORIGINAL_ATTACKER_ROLE, 'DebugStatus') -- Use original attacker
                             
                             if CURRENT_TURN > start_turn + 2 then
                                 -- Log only on expiration
                                 log("Debugger poison wore off.", "info", SCRIPT_TARGET_ROLE)
                                 unregister_script(CURRENT_REGISTRATION_ID)
                             end
                         """),
                     },
                     { # After Attacker Turn
                         'name': 'Debugger After Attacker Turn (Recoil)',
                         'trigger_after_attacker_turn': True,
                         'lua_code': textwrap.dedent("""
                            apply_std_hp_change(-1, SCRIPT_TARGET_ROLE) 
                            -- No expiration needed for simple recoil, assume it always triggers
                            -- If this needed a duration, add logic similar to poison
                         """),
                     },
                     { # Before Target Turn
                         'name': 'Debugger Before Target Turn (Def Buff)',
                         'trigger_before_target_turn': True,
                         'lua_code': textwrap.dedent("""
                            apply_std_stat_change('defense', 1, SCRIPT_TARGET_ROLE)
                            -- No expiration needed for simple buff, assume it always triggers
                            -- If this needed a duration, add logic similar to poison
                         """),
                     },
                 ]
            },
            # ============================
            # --- NEW PERSISTENT SCRIPTS --- 
            # ============================
            {
                'name': 'Toxic Sting',
                'description': 'Deals minor damage and poisons the target for 4 turns.',
                'emoji': '☠️',
                'momentum_cost': 30,
                'scripts': [
                    { # On Attack
                        'name': 'Toxic Sting Initial Damage',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                            local target = TARGET_ROLE
                            -- Check using custom status
                            if has_custom_status(target, 'Poisoned') then
                                log(get_player_name(target) .. " is already poisoned!", "info", ATTACKER_ROLE)
                            else
                                apply_std_damage(4, target) 
                                log("Poison took hold!", "status_change", target)
                                set_custom_status(target, 'Poisoned', true) -- Set the status flag
                            end
                        """),
                    },
                    { # After Target Turn
                        'name': 'Toxic Sting Poison Tick',
                        'trigger_after_target_turn': True,
                        'lua_code': textwrap.dedent("""
                            local start_turn = SCRIPT_START_TURN
                            if CURRENT_TURN <= start_turn + 3 then 
                                apply_std_hp_change(-3, SCRIPT_TARGET_ROLE)
                            end
                            
                            if CURRENT_TURN > start_turn + 3 then
                                log("The poison wore off.", "info", SCRIPT_TARGET_ROLE)
                                remove_custom_status(SCRIPT_TARGET_ROLE, 'Poisoned') -- Remove the status flag
                                unregister_script(CURRENT_REGISTRATION_ID)
                            end
                        """),
                    }
                ]
            },
            {
                'name': 'Regenerate',
                'description': 'Heals the user over 3 turns, starting strong and weakening.',
                'emoji': '✨',
                'momentum_cost': 50,
                'scripts': [
                     { # On Attack (Optional: Log start)
                        'name': 'Regenerate Start',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                            log("A healing aura surrounds " .. get_player_name(ATTACKER_ROLE) .. "!", "info", ATTACKER_ROLE)
                        """),
                    },
                    { # Before Attacker Turn
                        'name': 'Regenerate Heal Tick',
                        'trigger_before_attacker_turn': True,
                        'lua_code': textwrap.dedent("""
                            local start_turn = SCRIPT_START_TURN
                            local current_turn_offset = CURRENT_TURN - start_turn
                            
                            local max_hp = get_max_hp(SCRIPT_TARGET_ROLE) 
                            local heal_percent = 0
                            if current_turn_offset == 0 then heal_percent = 0.20
                            elseif current_turn_offset == 1 then heal_percent = 0.10
                            elseif current_turn_offset == 2 then heal_percent = 0.05
                            end
                            
                            if heal_percent > 0 and max_hp then
                                local heal_amount = math.floor(max_hp * heal_percent)
                                if heal_amount < 1 then heal_amount = 1 end
                                apply_std_hp_change(heal_amount, SCRIPT_TARGET_ROLE)
                            end
                            
                            if CURRENT_TURN > start_turn + 2 then
                                log("The healing aura faded.", "info", SCRIPT_TARGET_ROLE)
                                unregister_script(CURRENT_REGISTRATION_ID)
                            end
                        """),
                    }
                ]
            },
            {
                'name': 'Overexert',
                'description': "Deals massive damage, but lowers the user's Attack for 2 turns afterwards.",
                'emoji': '💥',
                'momentum_cost': 60,
                'scripts': [
                    { # On Attack
                        'name': 'Overexert Initial Damage',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                            apply_std_damage(25, TARGET_ROLE)
                            log(get_player_name(ATTACKER_ROLE) .. " is weakened from the effort!", "info", ATTACKER_ROLE)
                        """),
                    },
                    { # After Attacker Turn
                        'name': 'Overexert Attack Drop',
                        'trigger_after_attacker_turn': True,
                        'lua_code': textwrap.dedent("""
                            local start_turn = SCRIPT_START_TURN
                            if CURRENT_TURN <= start_turn + 1 then
                                -- Check stage before applying to prevent redundant logs
                                local current_stage = get_stat_stage(SCRIPT_TARGET_ROLE, 'attack')
                                if current_stage > -6 then
                                    apply_std_stat_change('attack', -1, SCRIPT_TARGET_ROLE)
                                -- apply_std_stat_change already logs if maxed out, no else needed
                                end
                            end
                            
                            if CURRENT_TURN > start_turn + 1 then
                                log(get_player_name(SCRIPT_TARGET_ROLE) .. " recovered their strength.", "info", SCRIPT_TARGET_ROLE)
                                unregister_script(CURRENT_REGISTRATION_ID)
                            end
                        """),
                    }
                ]
            },
            {
                'name': 'Burst Speed',
                'description': "Grants +3 Speed instantly, but decays by -1 Speed after each of the user's next turns until gone.",
                'emoji': '👟',
                'momentum_cost': 45,
                'scripts': [
                    { # On Attack
                        'name': 'Burst Speed Initial Buff',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                             -- Check before applying
                            local current_stage = get_stat_stage(ATTACKER_ROLE, 'speed')
                            if current_stage < 6 then
                                apply_std_stat_change('speed', 3, ATTACKER_ROLE)
                            -- else: apply_std_stat_change handles maxed out log
                            end
                        """),
                    },
                    { # After Attacker Turn
                        'name': 'Burst Speed Decay',
                        'trigger_after_attacker_turn': True,
                        'lua_code': textwrap.dedent("""
                            local start_turn = SCRIPT_START_TURN
                            local should_unregister = false
                            
                            -- Check before applying
                            local current_stage = get_stat_stage(SCRIPT_TARGET_ROLE, 'speed')
                            if current_stage > -6 then
                                apply_std_stat_change('speed', -1, SCRIPT_TARGET_ROLE)
                            end
                            
                            -- WORKAROUND: Unregister after 3 turns max
                            if CURRENT_TURN >= start_turn + 2 then
                                 should_unregister = true
                            end
                            
                            if should_unregister then
                                log(get_player_name(SCRIPT_TARGET_ROLE) .. "'s speed returned to normal.", "info", SCRIPT_TARGET_ROLE)
                                unregister_script(CURRENT_REGISTRATION_ID)
                            end
                        """),
                    }
                ]
            },
            {
                'name': 'Fortify',
                'description': 'Grants +6 Defense, lasting until the opponent has attacked twice.',
                'emoji': '🏰',
                'momentum_cost': 55,
                'scripts': [
                    { # On Attack
                        'name': 'Fortify Initial Buff',
                        'trigger_on_attack': True,
                        'lua_code': textwrap.dedent("""
                            local current_stage = get_stat_stage(ATTACKER_ROLE, 'defense')
                            if current_stage < 6 then
                                apply_std_stat_change('defense', 6, ATTACKER_ROLE)
                                set_custom_status(ATTACKER_ROLE, 'Fortified', 2) 
                            -- else: apply_std_stat_change handles maxed out log
                            end
                        """),
                    },
                    { # After Target Turn
                        'name': 'Fortify Counter Check',
                        'trigger_after_target_turn': True,
                        'lua_code': textwrap.dedent("""
                            local should_unregister = false
                            if has_custom_status(SCRIPT_TARGET_ROLE, 'Fortified') then
                                local current_stacks = get_custom_status(SCRIPT_TARGET_ROLE, 'Fortified')
                                modify_custom_status(SCRIPT_TARGET_ROLE, 'Fortified', -1)
                                current_stacks = current_stacks - 1 
                                
                                if current_stacks <= 0 then
                                    remove_custom_status(SCRIPT_TARGET_ROLE, 'Fortified')
                                    -- Check before removing buff
                                    local current_stage = get_stat_stage(SCRIPT_TARGET_ROLE, 'defense')
                                    if current_stage > -6 then
                                        apply_std_stat_change('defense', -6, SCRIPT_TARGET_ROLE) -- Remove the buff
                                    end
                                    log(get_player_name(SCRIPT_TARGET_ROLE) .. "'s defenses weakened.", "info", SCRIPT_TARGET_ROLE)
                                    should_unregister = true
                                end
                            else
                                 should_unregister = true -- Status gone, stop checking
                            end
                            
                            if should_unregister then
                                unregister_script(CURRENT_REGISTRATION_ID)
                            end
                        """),
                    }
                ]
            }
            # --- END NEW PERSISTENT SCRIPTS ---
        ]

        created_attacks = 0
        updated_attacks = 0
        created_scripts = 0
        updated_scripts = 0
        deleted_scripts = 0

        # Keep track of script names defined in this run for cleanup
        defined_script_names_for_attack = {}

        for attack_data in attacks_data:
            attack_name = attack_data.pop('name')
            scripts_list = attack_data.pop('scripts', [])
            
            attack_defaults = {
                 'description': attack_data.get('description', ''),
                 'emoji': attack_data.get('emoji'),
                 'momentum_cost': attack_data.get('momentum_cost', 10),
             }
            attack_obj, attack_created = Attack.objects.update_or_create(
                name=attack_name,
                defaults=attack_defaults
            )

            if attack_created:
                created_attacks += 1
                self.stdout.write(f'  Created Attack: {attack_name}')
            else:
                updated_attacks += 1
                self.stdout.write(f'  Found Attack: {attack_name}')
            
            # Process scripts for this attack
            current_attack_script_names = set()
            for script_data in scripts_list:
                script_name = script_data.pop('name')
                script_code = script_data.pop('lua_code')
                script_triggers = script_data
                current_attack_script_names.add(script_name)

                script_defaults = {
                    'lua_code': script_code,
                    **script_triggers
                }
                
                script_obj, script_created = Script.objects.update_or_create(
                    attack=attack_obj,
                    name=script_name,
                    defaults=script_defaults
                )
                
                if script_created:
                    created_scripts += 1
                    self.stdout.write(f'    - Created Script: {script_name}')
                else:
                    updated_scripts += 1
                    self.stdout.write(f'    - Updated Script: {script_name}')

            # Clean up old scripts associated with this attack but not defined in this run
            stale_scripts = attack_obj.scripts.exclude(name__in=current_attack_script_names)
            deleted_count, _ = stale_scripts.delete()
            if deleted_count > 0:
                deleted_scripts += deleted_count
                self.stdout.write(f'    - Deleted {deleted_count} stale script(s) for {attack_name}')

        self.stdout.write(self.style.SUCCESS(
            f'Finished. Attacks (Created: {created_attacks}, Updated: {updated_attacks}) | ' 
            f'Scripts (Created: {created_scripts}, Updated: {updated_scripts}, Deleted: {deleted_scripts})'
        )) 