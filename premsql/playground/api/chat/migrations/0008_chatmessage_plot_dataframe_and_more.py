# Generated by Django 5.1.1 on 2024-10-18 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0007_alter_session_db_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="plot_dataframe",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="few_shot_examples",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
