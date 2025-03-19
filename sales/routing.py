# sales/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/sales/<int:room_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/rooms/', consumers.RoomListConsumer.as_asgi()),
]