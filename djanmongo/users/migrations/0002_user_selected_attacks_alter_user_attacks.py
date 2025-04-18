# Generated by Django 5.1.7 on 2025-04-03 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0009_remove_attack_effort_remove_battle_player1_action_and_more'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='selected_attacks',
            field=models.ManyToManyField(blank=True, related_name='selected_by_users', to='game.attack'),
        ),
        migrations.AlterField(
            model_name='user',
            name='attacks',
            field=models.ManyToManyField(blank=True, related_name='learned_by_users', to='game.attack'),
        ),
    ]
