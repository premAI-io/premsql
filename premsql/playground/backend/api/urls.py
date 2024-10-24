from django.urls import path
from . import views

urlpatterns = [
    path("session/list/", views.list_sessions, name="list_sessions"),
    path("session/create", views.create_session, name="create_session"),
    path("session/delete/", views.delete_session, name="delete_session"),
    path("session/<str:session_name>/", views.get_session, name="get_session"),

    # Chat urls
    path("chat/completion", views.create_completion, name="completion")
]