from django.contrib import admin

from .models import ChatMessage, Session

admin.site.register(Session)
admin.site.register(ChatMessage)
