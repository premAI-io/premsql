from django.urls import path

from .views import ChatMessageCreateView, SessionCreateView

urlpatterns = [
    path("session/", SessionCreateView.as_view(), name="create_session"),
    path("sessios/<int:pk>/", SessionCreateView.as_view(), name="retrieve_session"),
    path("chat/", ChatMessageCreateView.as_view(), name="create_chat_message"),
]
