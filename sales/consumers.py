import json
import asyncio
import datetime
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import close_old_connections
from channels.db import database_sync_to_async
from django.db.models import Max, Count, Q
from .models import Room, Interaction, TelegramMessage, EmailMessage
from sales.tasks import send_outgoing_email_task, send_outgoing_telegram_task
from channels.layers import get_channel_layer
from sales.utils import render_email_template

# Idle timeout – 1 година (3600 секунд)
IDLE_TIMEOUT = 3600

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"sales_room_{self.room_id}"

        await asyncio.to_thread(close_old_connections)
        await self.accept()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.last_activity = datetime.datetime.now()
        self.idle_task = asyncio.create_task(self.idle_checker())

    async def disconnect(self, close_code):
        if hasattr(self, 'idle_task'):
            self.idle_task.cancel()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        self.last_activity = datetime.datetime.now()
        try:
            data = json.loads(text_data)
        except Exception as e:
            logger.error(f"Failed to parse text_data: {e}")
            return

        message = data.get("message", "").strip()
        channel_type = data.get("channel_type", "unknown")
        logger.debug(f"Received message: channel_type={channel_type}, message={message}")

        if channel_type == "telegram":
            interaction = await self.save_outgoing_telegram_message(self.scope["user"], self.room_id, message)
            payload = {
                "msg_type": "telegram",
                "body": message,
                "created_at": interaction.created_at.strftime("%H:%M"),
                "sender_type": "user",
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "payload": payload,
                    "username": self.scope["user"].username,
                }
            )
            room = await database_sync_to_async(Room.objects.get)(id=self.room_id, user=self.scope["user"])
            contact = await database_sync_to_async(lambda: room.contact)()
            contact_data = {
                "phone": contact.phone,
                "telegram_username": contact.telegram_username,
                "telegram_id": contact.telegram_id,
            }
            send_outgoing_telegram_task.delay(self.scope["user"].id, contact_data, message)

        elif channel_type == "email":
            subject = data.get("subject", "Без теми")
            interaction = await self.save_outgoing_email_message(self.scope["user"], self.room_id, subject, message)
            payload = {
                "msg_type": "email",
                "subject": subject,
                "body": message,
                "created_at": interaction.created_at.strftime("%H:%M"),
                "sender_type": "user",
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "payload": payload,
                    "username": self.scope["user"].username,
                }
            )
            room = await database_sync_to_async(Room.objects.get)(id=self.room_id, user=self.scope["user"])
            contact = await database_sync_to_async(lambda: room.contact)()
            if contact.email:
                logger.info(f"Sending plain email to {contact.email} with subject '{subject}'")
                send_outgoing_email_task.delay(self.scope["user"].id, subject, message, contact.email, email_type="plain")

        elif channel_type == "email_template":
            subject = data.get("subject", "Ласкаво просимо!")
            message = await database_sync_to_async(render_email_template)(self.scope["user"])
            interaction = await self.save_outgoing_email_message(self.scope["user"], self.room_id, subject, message)
            payload = {
                "msg_type": "email",
                "subject": subject,
                "body": message,
                "created_at": interaction.created_at.strftime("%H:%M"),
                "sender_type": "user",
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "payload": payload,
                    "username": self.scope["user"].username,
                }
            )
            room = await database_sync_to_async(Room.objects.get)(id=self.room_id, user=self.scope["user"])
            contact = await database_sync_to_async(lambda: room.contact)()
            if contact.email:
                logger.info(f"Sending HTML email template to {contact.email} with subject '{subject}'")
                send_outgoing_email_task.delay(self.scope["user"].id, subject, message, contact.email, email_type="html")

        else:
            logger.warning(f"Unknown channel_type: {channel_type}")

    async def chat_message(self, event):
        payload = event.get("payload", {})
        username = event.get("username", "User")
        await self.send(text_data=json.dumps({
            "username": username,
            "payload": payload,
        }))

    async def idle_checker(self):
        try:
            while True:
                await asyncio.sleep(10)
                now = datetime.datetime.now()
                elapsed = (now - self.last_activity).total_seconds()
                if elapsed >= IDLE_TIMEOUT:
                    await self.close(code=4001)
                    break
        except asyncio.CancelledError:
            pass

    @database_sync_to_async
    def save_outgoing_telegram_message(self, user, room_id, message):
        room = Room.objects.get(id=room_id, user=user)
        interaction = Interaction.objects.create(
            interaction_type="telegram",
            room=room,
            sender="user",
            is_read=True,
        )
        TelegramMessage.objects.create(
            interaction=interaction,
            message_id=None,
            chat_id=None,
            text=message,
        )
        return interaction

    @database_sync_to_async
    def save_outgoing_email_message(self, user, room_id, subject, message):
        room = Room.objects.get(id=room_id, user=user)
        interaction = Interaction.objects.create(
            interaction_type="email",
            room=room,
            sender="user",
            is_read=True,
        )
        EmailMessage.objects.create(
            interaction=interaction,
            subject=subject,
            body=message,
        )
        return interaction


class RoomListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            logger.warning("RoomListConsumer.connect() => user is anonymous, closing.")
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_group_name = f"user_{self.user.id}"
        logger.info(f"RoomListConsumer.connect() => user_id={self.user.id}, group={self.user_group_name}")

        try:
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()
            logger.info(f"Accepted WS for user_{self.user.id}. Sending initial room list.")
            await self.send_room_list_update()
        except Exception as e:
            logger.error(f"Error in RoomListConsumer.connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        logger.info(f"RoomListConsumer.disconnect() => group={self.user_group_name}, code={close_code}")
        try:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception as e:
            logger.error(f"Error during RoomListConsumer.disconnect: {e}")
        logger.info("Disconnected from user group")

    async def receive(self, text_data):
        logger.debug(f"RoomListConsumer.receive() => raw data: {text_data}")
        await self.send_room_list_update()

    async def room_list_update(self, event):
        logger.debug(f"room_list_update triggered with event: {event}")
        await self.send_room_list_update()

    @database_sync_to_async
    def get_rooms_for_user(self):
        logger.debug(f"get_rooms_for_user() => computing rooms for user_id={self.user.id}")
        qs = (
            self.user.rooms
            .select_related('contact', 'contact__company')
            .annotate(
                latest_interaction=Max('interactions__created_at'),
                unread_count=Count(
                    'interactions',
                    filter=Q(interactions__is_read=False, interactions__sender='contact'),
                    distinct=True
                )
            )
            .order_by('-latest_interaction')
        )
        return list(qs)

    async def send_room_list_update(self):
        logger.debug("send_room_list_update() => calling get_rooms_for_user()")
        try:
            rooms = await self.get_rooms_for_user()
            logger.debug(f"Got {len(rooms)} rooms. Building payload...")
            rooms_data = []
            for r in rooms:
                c = r.contact
                rooms_data.append({
                    "room_id": r.id,
                    "first_name": c.first_name,
                    "last_name": c.last_name or "",
                    "company_name": c.company.name if c.company else "",
                    "unread_count": r.unread_count or 0,
                })

            payload = {
                "type": "room_list",
                "rooms": rooms_data
            }
            logger.debug(f"Sending room_list: {rooms_data}")
            await self.send(text_data=json.dumps(payload))
            logger.debug("send_room_list_update done")
        except Exception as e:
            logger.error(f"Error in send_room_list_update: {e}")