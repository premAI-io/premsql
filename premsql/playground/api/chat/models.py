from django.db import models

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    session_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    agent_name = models.CharField(max_length=255, default="simple_agent")

    db_type = models.CharField(
        max_length=255,
        choices=[("postgres", "PostgreSQL"), ("sqlite", "SQLite")],
        default="sqlite"
    )

    db_connection_uri = models.CharField(
        max_length=255, null=True, blank=True
    )

    include = models.TextField(blank=True, default="")
    exclude = models.TextField(blank=True, default="")

    config_path = models.TextField(blank=True, null=True)
    env_path = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["created_at"]


class ChatMessage(models.Model):
    message_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    query = models.TextField()
    additional_knowledge = models.TextField(null=True, blank=True)
    few_shot_examples = models.JSONField(null=True, blank=True)

    # All the responses 
    sql_string = models.TextField()
    bot_message = models.TextField(null=True, blank=True)
    dataframe = models.JSONField(null=True, blank=True)
    plot_image = models.TextField(null=True, blank=True) # Base64
    plot_dataframe = models.JSONField(null=True, blank=True) # A dataframe instead of image is also possible 
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]