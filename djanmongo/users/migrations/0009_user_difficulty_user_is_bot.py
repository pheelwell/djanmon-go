# Generated by Django 5.1.7 on 2025-04-18 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_remove_user_difficulty_remove_user_is_bot'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='difficulty',
            field=models.CharField(blank=True, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], help_text='Difficulty level if this user is a bot.', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_bot',
            field=models.BooleanField(default=False, help_text='Identifies if this user is an AI-controlled bot.'),
        ),
    ]
