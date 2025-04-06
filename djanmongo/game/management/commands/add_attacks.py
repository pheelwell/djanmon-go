from django.core.management.base import BaseCommand
from game.models import Attack
import textwrap # For dedenting Lua scripts

class Command(BaseCommand):
    help = 'Adds or updates a predefined set of attacks in the database using Lua scripts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Adding/Updating Lua-based Attacks...'))

        attacks_data = [
            # --- Basic Damage Attacks ---
            {
                'name': 'Quick Jab', 
                'description': 'A very fast jab, low impact.', 
                'emoji': '⚡', 
                'momentum_cost': 10,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_damage(5, TARGET_ROLE)
                """),
            },
            {
                'name': 'Punch', 
                'description': 'A standard punch.', 
                'emoji': '👊', 
                'momentum_cost': 20,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_damage(10, TARGET_ROLE)
                """),
            },
            {
                'name': 'Heavy Slam', 
                'description': 'A slow, powerful slam.', 
                'emoji': '🏋️', 
                'momentum_cost': 40,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_damage(18, TARGET_ROLE)
                """),
            },

            # --- Single Stat Buffs (Self) ---
            {
                'name': 'Bulk Up', 
                'description': "Raises User's Attack.", 
                'emoji': '💪', 
                'momentum_cost': 30,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('attack', 1, ATTACKER_ROLE)
                """),
            },
            {
                'name': 'Iron Defense', 
                'description': "Raises User's Defense.", 
                'emoji': '🛡️', 
                'momentum_cost': 30,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('defense', 1, ATTACKER_ROLE)
                """),
            },
            {
                'name': 'Agility', 
                'description': "Raises User's Speed.", 
                'emoji': '💨', 
                'momentum_cost': 30,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('speed', 1, ATTACKER_ROLE)
                """),
            },

            # --- Single Stat Debuffs (Enemy) ---
            {
                'name': 'Leer', 
                'description': "Lowers Enemy's Defense.", 
                'emoji': '😠', 
                'momentum_cost': 20,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('defense', -1, TARGET_ROLE)
                """),
            },
            {
                'name': 'Growl', 
                'description': "Lowers Enemy's Attack.", 
                'emoji': '🗣️', 
                'momentum_cost': 20,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('attack', -1, TARGET_ROLE)
                """),
            },
            {
                'name': 'Scary Face', 
                'description': "Lowers Enemy's Speed.", 
                'emoji': '😨', 
                'momentum_cost': 20,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('speed', -1, TARGET_ROLE)
                """),
            },

            # --- Damage + Debuff (Enemy) ---
            {
                'name': 'Acid Spray', 
                'description': "Damages and lowers Enemy's Defense.", 
                'emoji': '🧪', 
                'momentum_cost': 30,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_damage(7, TARGET_ROLE)
                    apply_std_stat_change('defense', -1, TARGET_ROLE)
                """),
            },
            {
                'name': 'Weakening Voice', 
                'description': "Damages and lowers Enemy's Attack.", 
                'emoji': '🎶', 
                'momentum_cost': 30,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_damage(7, TARGET_ROLE)
                    apply_std_stat_change('attack', -1, TARGET_ROLE)
                """),
            },
            
            # --- Healing (Self) ---
            {
                'name': 'Recover', 
                'description': 'Heals a good amount of HP.', 
                'emoji': '❤️‍🩹', 
                'momentum_cost': 40,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_hp_change(30, ATTACKER_ROLE)
                """),
            },
            {
                'name': 'Rest', 
                'description': 'Heals a small amount of HP.', 
                'emoji': '💤', 
                'momentum_cost': 20,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_hp_change(15, ATTACKER_ROLE)
                """),
            },

            # --- Stronger Stat Changes (+/- 2) ---
            {
                'name': 'Extreme Speed', 
                'description': "Greatly raises User's Speed.", 
                'emoji': '🚀', 
                'momentum_cost': 50,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('speed', 2, ATTACKER_ROLE)
                """),
            },
            {
                'name': 'Charm', 
                'description': "Greatly lowers Enemy's Attack.", 
                'emoji': '🥺', 
                'momentum_cost': 40,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('attack', -2, TARGET_ROLE)
                """),
            },
            {
                'name': 'Barrier', 
                'description': "Greatly raises User's Defense.", 
                'emoji': '🧱', 
                'momentum_cost': 50,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('defense', 2, ATTACKER_ROLE)
                """),
            },
            {
                'name': 'Metal Sound', 
                'description': "Greatly lowers Enemy's Defense.", 
                'emoji': '⚙️', 
                'momentum_cost': 40,
                'lua_script_on_attack': textwrap.dedent("""
                    apply_std_stat_change('defense', -2, TARGET_ROLE)
                """),
            },
        ]

        created_count = 0
        updated_count = 0

        for attack_info in attacks_data:
            name = attack_info.pop('name') # Use name as the unique identifier
            
            # Set defaults for fields not explicitly defined for every attack
            defaults = {
                'description': attack_info.get('description', ''),
                'emoji': attack_info.get('emoji'),
                'momentum_cost': attack_info.get('momentum_cost', 10), # Default momentum if not specified
                'lua_script_on_attack': attack_info.get('lua_script_on_attack'),
                'lua_script_before_opponent': None, # Default other scripts to None
                'lua_script_after_opponent': None,
                'register_before_opponent': False, # Default registration to False
                'register_after_opponent': False,
            }

            # Use update_or_create to add new attacks or update existing ones by name
            obj, created = Attack.objects.update_or_create(
                name=name,
                defaults=defaults
            )

            if created:
                created_count += 1
                self.stdout.write(f'  Created Attack: {name}')
            else:
                # Check if specific fields were actually updated (optional, needs more logic)
                # For simplicity, just mark as updated if found
                updated_count += 1
                self.stdout.write(f'  Updated Attack: {name}')

        self.stdout.write(self.style.SUCCESS(f'Finished. Created: {created_count}, Updated: {updated_count}')) 