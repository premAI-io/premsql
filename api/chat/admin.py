from django.contrib import admin 
from .models import Session, ChatMessage, TableFilter

admin.site.register(Session)
admin.site.register(ChatMessage)
admin.site.register(TableFilter)