import os
import django

# Adjust the relative path ('..') if your script is located differently
# relative to manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Now you can import your models
from game.models import Attack

def populate():
    """Populates the database with initial attacks."""
    attacks_data = [
        # Physical Attacks
        {'name': 'Punch', 'power': 40, 'target': 'enemy', 'emoji': '💥', 'description': 'A basic punch.'},
        {'name': 'Kick', 'power': 50, 'target': 'enemy', 'emoji': '👟', 'description': 'A standard kick.'},
        {'name': 'Bite', 'power': 60, 'target': 'enemy', 'emoji': '🦷', 'description': 'A sharp bite.'},
        {'name': 'Scratch', 'power': 35, 'target': 'enemy', 'emoji': '🐾', 'description': 'Quick scratches with sharp claws.'},
        {'name': 'Slam', 'power': 80, 'target': 'enemy', 'emoji': '👊', 'description': 'Slams the target with force.'},
        {'name': 'Tackle', 'power': 40, 'target': 'enemy', 'emoji': '🐏', 'description': 'A full-body charge.'},
        {'name': 'Headbutt', 'power': 70, 'target': 'enemy', 'emoji': '들이받다', 'description': 'A powerful headbutt.'}, # Replace emoji if needed
        {'name': 'Quick Attack', 'power': 40, 'target': 'enemy', 'emoji': '⚡️', 'description': 'An attack that always strikes first (mechanic not implemented).'}, # Priority mechanic note

        # Elemental Attacks
        {'name': 'Ember', 'power': 40, 'target': 'enemy', 'emoji': '🔥', 'description': 'A small burst of flame.'},
        {'name': 'Water Gun', 'power': 40, 'target': 'enemy', 'emoji': '💧', 'description': 'Shoots a jet of water.'},
        {'name': 'Zap', 'power': 40, 'target': 'enemy', 'emoji': '⚡️', 'description': 'A weak electric shock.'},
        {'name': 'Gust', 'power': 40, 'target': 'enemy', 'emoji': '💨', 'description': 'A blast of wind.'},
        {'name': 'Rock Throw', 'power': 50, 'target': 'enemy', 'emoji': '🪨', 'description': 'Throws a small rock.'},

        # Stat Modifying Attacks
        {'name': 'Growl', 'power': 0, 'target': 'enemy', 'target_stat': 'ATK', 'stat_mod': -1, 'emoji': '🗣️', 'description': 'Lowers the opponent\'s Attack.'},
        {'name': 'Tail Whip', 'power': 0, 'target': 'enemy', 'target_stat': 'DEF', 'stat_mod': -1, 'emoji': '🐕', 'description': 'Lowers the opponent\'s Defense.'},
        {'name': 'Harden', 'power': 0, 'target': 'self', 'target_stat': 'DEF', 'stat_mod': 1, 'emoji': '🛡️', 'description': 'Raises the user\'s Defense.'},
        {'name': 'Agility', 'power': 0, 'target': 'self', 'target_stat': 'SPEED', 'stat_mod': 2, 'emoji': '🚀', 'description': 'Sharply raises the user\'s Speed.'},

        # HP / Other Attacks
        {'name': 'Recover', 'power': 0, 'target': 'self', 'hp_amount': 30, 'emoji': '❤️‍🩹', 'description': 'Heals the user by 30 HP.'},
        {'name': 'Stomp', 'power': 65, 'target': 'enemy', 'emoji': '🦶', 'description': 'Stomps down hard on the opponent.'},
        {'name': 'Bubble', 'power': 40, 'target': 'enemy', 'target_stat': 'SPEED', 'stat_mod': -1, 'emoji': '🫧', 'description': 'May lower the opponent\'s Speed.'}, # Added 'May'
    ]

    print("Populating attacks...")
    created_count = 0
    updated_count = 0
    for attack_data in attacks_data:
        obj, created = Attack.objects.update_or_create(
            name=attack_data['name'], # Use name as the unique key
            defaults=attack_data      # Data to set or update
        )
        if created:
            created_count += 1
            print(f"  Created: {obj.name}")
        else:
            updated_count += 1
            # Optional: print updated only if you want to see them
            # print(f"  Updated: {obj.name}")

    print(f"\nPopulation complete. {created_count} created, {updated_count} updated.")

if __name__ == '__main__':
    populate()