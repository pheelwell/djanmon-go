# Generated by Django 5.1.7 on 2025-04-06 18:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0017_attack_lua_script_on_targeted_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attack',
            name='lua_script_on_targeted',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='register_on_targeted',
        ),
    ]
