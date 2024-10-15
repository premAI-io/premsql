from django.contrib import admin 
from .models import Session, ChatMessage

admin.site.register(Session)
admin.site.register(ChatMessage)