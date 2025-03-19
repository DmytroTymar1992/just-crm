# sales/management/commands/authorize_telegram_session.py
import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from telethon import TelegramClient

User = get_user_model()

class Command(BaseCommand):
    help = "Авторизовує Telegram сесію для заданого користувача"

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, required=True, help='ID користувача')
        parser.add_argument('--session_type', type=str, default='in', choices=['in', 'out'],
                            help='Тип сесії: "in" для прийому або "out" для відправки')

    def handle(self, *args, **options):
        user_id = options['user_id']
        session_type = options['session_type']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Користувача з id {user_id} не знайдено."))
            return

        profile = user.profile
        api_id = profile.telegram_api_id
        api_hash = profile.telegram_api_hash
        phone = profile.telegram_phone

        if session_type == 'in':
            session_file = profile.telegram_session_file or f"{user.username}.session"
        else:
            session_file = profile.telegram_session_file_out or f"{user.username}_out.session"

        async def main():
            client = TelegramClient(session_file, api_id, api_hash)
            await client.start(phone=phone)
            self.stdout.write(self.style.SUCCESS(f"Сесія ({session_type}) авторизована та збережена у файлі {session_file}"))
            await client.disconnect()

        asyncio.run(main())

        # Зберігаємо ім'я сесії в базі, якщо ще не збережено
        if session_type == 'in':
            profile.telegram_session_file = session_file
        else:
            profile.telegram_session_file_out = session_file
        profile.save()
