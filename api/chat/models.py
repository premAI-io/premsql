from django.db import models


class Session(models.Model):
    # make chat_id auto increment
    chat_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    llm = models.CharField(max_length=255, null=True, blank=True)
    db_type = models.CharField(
        max_length=255,
        choices=[("PostgreSQL", "postgres"), ("SQLite", "sqlite")],
        default="sqlite",
    )
    db_connection_uri = models.CharField(max_length=255, null=True, blank=True)


class TableFilter(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="table_filters"
    )
    table_name = models.CharField(max_length=255)
    include = models.BooleanField(default=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="messages"
    )
    query = models.TextField()
    response = models.TextField()
    sql = models.TextField(null=True, blank=True)

    llm = models.CharField(max_length=255, null=True, blank=True)
    table = models.JSONField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    max_new_tokens = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
