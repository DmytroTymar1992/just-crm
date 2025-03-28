# transcription/consumers.py

import json
import logging # Краще використовувати логгер
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model # Кращий спосіб отримати модель User

# Отримуємо модель користувача (стандартну або кастомну)
User = get_user_model()

# Налаштовуємо логгер
logger = logging.getLogger(__name__)

# !!! ВАЖЛИВО: Це ТИМЧАСОВИЙ словник для тестів. !!!
# Вам потрібно реалізувати БЕЗПЕЧНУ систему автентифікації агентів.
# Можливі варіанти:
# 1. API Токени (напр., Django REST Framework TokenAuthentication): Агент надсилає токен.
# 2. Сесії Django: Якщо агент може якось отримати сесійний cookie.
# 3. JWT токени.
# Цей словник лише для перевірки роботи WebSocket.
class DesktopAgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = None
        self.group_name = None

        try:
            # --- ЗМІНА: Отримуємо user_id замість token ---
            query_string = self.scope['query_string'].decode()
            params = dict(q.split('=') for q in query_string.split('&') if '=' in q)
            user_id_str = params.get('user_id') # Очікуємо параметр user_id

            logger.info(f"[AgentConsumer] Attempting connection for user_id: {user_id_str}")

            # --- ЗМІНА: Валідація user_id ---
            if user_id_str:
                try:
                    user_id = int(user_id_str)
                    # Використовуємо існуючий метод для пошуку користувача
                    self.user = await self.get_user_by_id(user_id)
                except ValueError:
                    logger.warning(f"[AgentConsumer] Invalid user_id format received: {user_id_str}")
                except Exception as e:
                    logger.error(f"[AgentConsumer] Error looking up user for ID {user_id_str}: {e}")
            # ------------------------------------

            if self.user:
                # Успішна автентифікація за User ID
                self.group_name = f'agent_{self.user.id}'
                await self.channel_layer.group_add(
                    self.group_name,
                    self.channel_name
                )
                await self.accept()
                logger.info(f"[AgentConsumer] Agent connected: User {self.user.username} (ID: {self.user.id}), Group {self.group_name}, Channel {self.channel_name}")
                await self.send(text_data=json.dumps({
                    'type': 'connection_established',
                    'message': f'Welcome Agent for user {self.user.username}!'
                }))
            else:
                # Користувача не знайдено або ID невалідний
                logger.warning(f"[AgentConsumer] Connection rejected: Invalid or non-existent user_id ('{user_id_str}').")
                await self.close(code=4001)

        except Exception as e:
            logger.error(f"[AgentConsumer] Error during connect: {e}", exc_info=True)
            await self.close()

    # ... (решта методів: disconnect, receive, send_command, get_user_by_id - залишаються без змін) ...

    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Безпечно отримує користувача за ID з бази даних."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} not found.")
            return None
        except Exception as e:
             logger.error(f"Database error fetching user {user_id}: {e}")
             return None
