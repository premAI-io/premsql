# Generated by Django 5.1.1 on 2024-09-25 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_alter_session_db_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="table",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
