# Generated by Django 5.1.7 on 2025-04-06 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0014_remove_attack_lua_script_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attack',
            name='hp_amount',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='power',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='stat_mod',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='target',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='target_stat',
        ),
        migrations.RemoveField(
            model_name='battle',
            name='custom_statuses_player1',
        ),
        migrations.RemoveField(
            model_name='battle',
            name='custom_statuses_player2',
        ),
        migrations.AddField(
            model_name='attack',
            name='lua_script_after_opponent',
            field=models.TextField(blank=True, help_text='Lua script to potentially register. Runs after the opponent finishes their next move.', null=True, verbose_name='After Opponent Attacks Script'),
        ),
        migrations.AddField(
            model_name='attack',
            name='lua_script_before_opponent',
            field=models.TextField(blank=True, help_text='Lua script to potentially register. Runs before the opponent makes their next move.', null=True, verbose_name='Before Opponent Attacks Script'),
        ),
        migrations.AddField(
            model_name='attack',
            name='lua_script_on_attack',
            field=models.TextField(blank=True, help_text='Lua script executed when this attack is used. Use API funcs like apply_std_damage(pwr), apply_std_hp_change(amt), apply_std_stat_change(stat, mod), etc.', null=True, verbose_name='On Attack Script'),
        ),
        migrations.AddField(
            model_name='attack',
            name='register_after_opponent',
            field=models.BooleanField(default=False, help_text="If checked, the 'After Opponent Attacks Script' will be registered to run on future opponent turns when this attack is used.", verbose_name="Register 'After Opponent' Script?"),
        ),
        migrations.AddField(
            model_name='attack',
            name='register_before_opponent',
            field=models.BooleanField(default=False, help_text="If checked, the 'Before Opponent Attacks Script' will be registered to run on future opponent turns when this attack is used.", verbose_name="Register 'Before Opponent' Script?"),
        ),
        migrations.AddField(
            model_name='battle',
            name='registered_scripts',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='battle',
            name='turn_number',
            field=models.PositiveIntegerField(default=0, help_text='Current turn number, starts at 1.'),
        ),
        migrations.AlterField(
            model_name='attack',
            name='momentum_cost',
            field=models.PositiveIntegerField(default=1, help_text='Base momentum generated by using this attack'),
        ),
    ]
