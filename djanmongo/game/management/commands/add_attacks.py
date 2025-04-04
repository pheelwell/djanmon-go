from django.core.management.base import BaseCommand
from game.models import Attack

class Command(BaseCommand):
    help = 'Adds or updates a predefined set of attacks in the database with rebalanced values'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Adding/Updating Rebalanced Attacks...'))

        attacks_data = [
            # --- Basic Damage (Momentum/Power Trade-off) ---
            {
                'name': 'Quick Jab', 'description': 'A very fast jab, low impact.', 'power': 5, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'NONE', 'stat_mod': 0, 'emoji': '⚡', 'momentum_cost': 10 # 1 * 10
            },
            {
                'name': 'Punch', 'description': 'A standard punch.', 'power': 10, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'NONE', 'stat_mod': 0, 'emoji': '👊', 'momentum_cost': 20 # 2 * 10
            },
            {
                'name': 'Heavy Slam', 'description': 'A slow, powerful slam.', 'power': 18, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'NONE', 'stat_mod': 0, 'emoji': '🏋️', 'momentum_cost': 40 # 4 * 10
            },

            # --- Single Stat Buffs (+1 User) ---
            {
                'name': 'Bulk Up', 'description': "Raises User's Attack.", 'power': 0, 'target': 'self',
                'hp_amount': 0, 'target_stat': 'ATK', 'stat_mod': 1, 'emoji': '💪', 'momentum_cost': 30 # 3 * 10
            },
            {
                'name': 'Iron Defense', 'description': "Raises User's Defense.", 'power': 0, 'target': 'self',
                'hp_amount': 0, 'target_stat': 'DEF', 'stat_mod': 1, 'emoji': '🛡️', 'momentum_cost': 30 # 3 * 10
            },
            {
                'name': 'Agility', 'description': "Raises User's Speed.", 'power': 0, 'target': 'self',
                'hp_amount': 0, 'target_stat': 'SPEED', 'stat_mod': 1, 'emoji': '💨', 'momentum_cost': 30 # 3 * 10
            },

            # --- Single Stat Debuffs (-1 Enemy) ---
            {
                'name': 'Leer', 'description': "Lowers Enemy's Defense.", 'power': 0, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'DEF', 'stat_mod': -1, 'emoji': '😠', 'momentum_cost': 20 # 2 * 10
            },
            {
                'name': 'Growl', 'description': "Lowers Enemy's Attack.", 'power': 0, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'ATK', 'stat_mod': -1, 'emoji': '🗣️', 'momentum_cost': 20 # 2 * 10
            },
            {
                'name': 'Scary Face', 'description': "Lowers Enemy's Speed.", 'power': 0, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'SPEED', 'stat_mod': -1, 'emoji': '😨', 'momentum_cost': 20 # 2 * 10
            },

            # --- Damage + Debuff (-1 Enemy) ---
            {
                'name': 'Acid Spray', 'description': "Damages and lowers Enemy's Defense.", 'power': 7, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'DEF', 'stat_mod': -1, 'emoji': '🧪', 'momentum_cost': 30 # 3 * 10
            },
            {
                'name': 'Weakening Voice', 'description': "Damages and lowers Enemy's Attack.", 'power': 7, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'ATK', 'stat_mod': -1, 'emoji': '🎶', 'momentum_cost': 30 # 3 * 10
            },
            
            # --- Healing ---
            {
                'name': 'Recover', 'description': 'Heals a good amount of HP.', 'power': 0, 'target': 'self',
                'hp_amount': 30, 'target_stat': 'NONE', 'stat_mod': 0, 'emoji': '❤️‍🩹', 'momentum_cost': 40 # 4 * 10
            },
            {
                'name': 'Rest', 'description': 'Heals a small amount of HP.', 'power': 0, 'target': 'self',
                'hp_amount': 15, 'target_stat': 'NONE', 'stat_mod': 0, 'emoji': '💤', 'momentum_cost': 20 # 2 * 10
            },

            # --- Stronger Stat Changes (+/- 2) ---
            {
                'name': 'Extreme Speed', 'description': "Greatly raises User's Speed.", 'power': 0, 'target': 'self',
                'hp_amount': 0, 'target_stat': 'SPEED', 'stat_mod': 2, 'emoji': '🚀', 'momentum_cost': 50 # Rebalanced: (3+2)*10 = 50
            },
            {
                'name': 'Charm', 'description': "Greatly lowers Enemy's Attack.", 'power': 0, 'target': 'enemy',
                'hp_amount': 0, 'target_stat': 'ATK', 'stat_mod': -2, 'emoji': '🥺', 'momentum_cost': 40 # Rebalanced: (2+2)*10 = 40
            },
            {
                'name': 'Barrier', 'description': "Greatly raises User's Defense.", 'power': 0, 'target': 'self', 
                'hp_amount': 0, 'target_stat': 'DEF', 'stat_mod': 2, 'emoji': '🧱', 'momentum_cost': 50 # Rebalanced: (3+2)*10 = 50
            },
            {
                'name': 'Metal Sound', 'description': "Greatly lowers Enemy's Defense.", 'power': 0, 'target': 'enemy', 
                'hp_amount': 0, 'target_stat': 'DEF', 'stat_mod': -2, 'emoji': '⚙️', 'momentum_cost': 40 # Rebalanced: (2+2)*10 = 40
            },
            # --- New attack ideas? ---
            # Maybe a high-cost, high-power move with recoil?
            # Maybe a move that switches stats?
            # Maybe a fixed damage move?
        ]

        created_count = 0
        updated_count = 0

        for attack_info in attacks_data:
            name = attack_info.pop('name') # Use name as the unique identifier
            defaults = attack_info # The rest are defaults to set/update

            # Use update_or_create to add new attacks or update existing ones by name
            obj, created = Attack.objects.update_or_create(
                name=name,
                defaults=defaults
            )

            if created:
                created_count += 1
                self.stdout.write(f'  Created Attack: {name}')
            else:
                updated_count += 1
                self.stdout.write(f'  Updated Attack: {name}')

        self.stdout.write(self.style.SUCCESS(f'Finished. Created: {created_count}, Updated: {updated_count}')) 