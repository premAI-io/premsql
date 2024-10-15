from django.urls import path
from . import views

urlpatterns = [
    # Session URLs
    path('session/create/', views.create_session, name='create_session'),
    path('session/update/', views.update_session, name='update_session'),
    path('session/delete/', views.delete_session, name='delete_session'),
    path('session/list/', views.list_sessions, name='list_sessions'),
    path('session/<str:session_name>/', views.get_session, name='get_session'),
]