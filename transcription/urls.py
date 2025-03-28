from django.urls import path
from . import views

urlpatterns = [
    path('agent-audio/', views.agent_audio_view, name='agent_audio'),
]