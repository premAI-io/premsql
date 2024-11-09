from django.contrib import admin

from .models import Completions, Session

admin.site.register(Session)
admin.site.register(Completions)
