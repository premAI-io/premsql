from django.db import models

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    db_connection_uri = models.URLField()
    session_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    base_url = models.URLField()
    session_db_path = models.CharField(max_length=255) 
    class Meta:
        ordering = ["created_at"]

class Completions(models.Model):
    message_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE,
        related_name="messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["created_at"]


