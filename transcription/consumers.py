# transcription/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()
logger = logging.getLogger(__name__)

# Тимчасове сховище
agent_audio_data = {}

class DesktopAgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = None
        self.group_name = None

        query_string = self.scope['query_string'].decode()
        params = dict(q.split('=') for q in query_string.split('&') if '=' in q)
        user_id_str = params.get('user_id')

        logger.info(f"[AgentConsumer] Attempting connection for user_id: {user_id_str}")

        if user_id_str:
            try:
                user_id = int(user_id_str)
                self.user = await self.get_user_by_id(user_id)
            except ValueError:
                logger.warning(f"[AgentConsumer] Invalid user_id format received: {user_id_str}")
            except Exception as e:
                logger.error(f"[AgentConsumer] Error looking up user for ID {user_id_str}: {e}")

        if self.user:
            self.group_name = f'agent_{self.user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"[AgentConsumer] Agent connected: User {self.user.username} (ID: {self.user.id}), Group {self.group_name}")
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': f'Welcome Agent for user {self.user.username}!'
            }))
            # Ініціалізація logs, якщо ще не існує
            if self.user.id not in agent_audio_data:
                agent_audio_data[self.user.id] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
            agent_audio_data[self.user.id]["logs"].append({
                "event": "agent_connected",
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            logger.warning(f"[AgentConsumer] Connection rejected: Invalid or non-existent user_id ('{user_id_str}').")
            await self.close(code=4001)

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[AgentConsumer] Disconnected: User {self.user.username if self.user else 'Unknown'} (Code: {close_code})")
        if self.user and self.user.id in agent_audio_data:
            agent_audio_data[self.user.id]["logs"].append({
                "event": "agent_disconnected",
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    async def receive(self, text_data):
        logger.info(f"[AgentConsumer] Received message: {text_data}")
        data = json.loads(text_data)
        if data.get("type") == "audio":
            user_id = self.user.id
            if user_id not in agent_audio_data:
                agent_audio_data[user_id] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
            agent_audio_data[user_id].update({
                "audio_length": len(data["data"]),
                "data": data["data"][:100],  # Обрізаємо для прикладу
                "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            agent_audio_data[user_id]["logs"].append({
                "event": "audio_received",
                "audio_length": len(data["data"]),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            logger.info(f"[AgentConsumer] Audio received from user {user_id}: {len(data['data'])} samples")

    async def agent_command(self, event):
        command = event["command"]
        details = event["details"]
        logger.info(f"[AgentConsumer] Sending command to agent: {command}, Details: {details}")
        await self.send(text_data=json.dumps({
            "type": "command",
            "command": command,
            "details": details
        }))
        if self.user.id in agent_audio_data:
            agent_audio_data[self.user.id]["logs"].append({
                "event": "command_sent",
                "command": command,
                "details": details,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    @database_sync_to_async
    def get_user_by_id(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} not found.")
            return None
        except Exception as e:
            logger.error(f"Database error fetching user {user_id}: {e}")
            return None