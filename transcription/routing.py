# transcription/routing.py
from django.urls import re_path
from . import consumers # Імпортуємо консюмери з цього ж додатка

websocket_urlpatterns = [
    re_path(r'^ws/desktop_agent/$', consumers.DesktopAgentConsumer.as_asgi()),
    # ^ Маршрут для підключення десктопного агента
]