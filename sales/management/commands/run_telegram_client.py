#sales/management/commands/run_telegram_client.py
import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from telethon import TelegramClient, events
from sales.tasks import process_telegram_message

User = get_user_model()

class Command(BaseCommand):
    help = "Запуск Telegram клієнта для заданого користувача"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user_id',
            type=int,
            required=True,
            help='ID користувача, для якого запускається Telegram клієнт'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Користувача з id {user_id} не знайдено."))
            return

        # Отримуємо дані з профілю користувача (при умові, що зв’язок OneToOne має ім'я profile)
        user_profile = user.profile
        api_id = user_profile.telegram_api_id
        api_hash = user_profile.telegram_api_hash
        phone = user_profile.telegram_phone
        session_file = user_profile.telegram_session_file or f"{user.username}.session"

        if not all([api_id, api_hash, phone]):
            self.stdout.write(self.style.ERROR("Невірно заповнені дані Telegram у профілі користувача."))
            return

        client = TelegramClient(session_file, api_id, api_hash)

        @client.on(events.NewMessage)
        async def handler(event):
            # Формуємо дані повідомлення для подальшої обробки
            message_data = {
                'message_id': event.message.id,
                'chat_id': event.message.chat_id,
                'text': event.message.message,
                'sender_id': None,
                'sender_first_name': '',
                'sender_last_name': '',
                'sender_username': '',
                'sender_phone': None,
                'receiver_user_id': user_id,  # ID користувача, якому належить сесія
            }
            sender = await event.get_sender()
            if sender:
                message_data['sender_id'] = sender.id
                message_data['sender_first_name'] = getattr(sender, 'first_name', '')
                message_data['sender_last_name'] = getattr(sender, 'last_name', '')
                message_data['sender_username'] = getattr(sender, 'username', '')
                message_data['sender_phone'] = getattr(sender, 'phone', None)

            # Викликаємо Celery задачу для обробки повідомлення
            process_telegram_message.delay(message_data)

        async def main():
            await client.start(phone=phone)
            self.stdout.write(self.style.SUCCESS("Telegram клієнт запущено, очікування повідомлень..."))
            await client.run_until_disconnected()

        asyncio.run(main())
