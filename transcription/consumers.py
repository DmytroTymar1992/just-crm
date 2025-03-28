import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

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
        else:
            logger.warning(f"[AgentConsumer] Connection rejected: Invalid or non-existent user_id ('{user_id_str}').")
            await self.close(code=4001)

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[AgentConsumer] Disconnected: User {self.user.username if self.user else 'Unknown'} (Code: {close_code})")

    async def receive(self, text_data):
        logger.info(f"[AgentConsumer] Received message: {text_data}")
        data = json.loads(text_data)
        # Тут можна обробляти дані від агента (наприклад, аудіо)

    async def agent_command(self, event):
        command = event["command"]
        details = event["details"]
        logger.info(f"[AgentConsumer] Sending command to agent: {command}, Details: {details}")
        await self.send(text_data=json.dumps({
            "type": "command",
            "command": command,
            "details": details
        }))

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