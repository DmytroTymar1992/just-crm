import asyncio
import json
import logging
import datetime

import websockets  # Бібліотека websockets (pip install websockets)
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import close_old_connections

# Можете викликати Celery-таску, яка створить Interaction + CallMessage,
# або зробити це прямо тут. Приклад із Celery-таскою:
from sales.tasks import process_phonet_call

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запуск Phonet WebSocket клієнта для заданого користувача"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user_id',
            type=int,
            required=True,
            help='ID користувача, для якого запускається Phonet клієнт'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Користувача з id={user_id} не знайдено."))
            return

        profile = user.profile
        if not profile.phonet_enabled:
            self.stdout.write(
                self.style.ERROR(f"Phonet не увімкнено для користувача id={user_id} (phonet_enabled=False)."))
            return

        # Припустимо, зберігаємо налаштування в полі, напр. phonet_domain та phonet_api_key
        domain = "contactlogistic.phonet.com.ua"
        api_key = "ZvQFVmZF6a0EthybFi8HsS5bH7mzU0eJ"
        subscriber = profile.phonet_ext  # внутрішній номер
        if not all([domain, api_key, subscriber]):
            self.stdout.write(
                self.style.ERROR("Невірно заповнені поля phonet_domain / phonet_api_key / phonet_ext у профілі."))
            return

        wss_url = f"wss://{domain}/live/connector/v3/easy?domain={domain}&apiKey={api_key}&subscriber={subscriber}"
        self.stdout.write(self.style.SUCCESS(f"Підключення до Phonet: {wss_url}"))

        # Запускаємо асинхронний метод
        asyncio.run(self.run_phonet_client(user.id, wss_url))

    async def run_phonet_client(self, user_id, wss_url):
        """
        Головна асинхронна функція:
        - Підключається до WSS
        - Читає повідомлення
        - Якщо отримує call.dial / call.bridge / call.hangup -> відправляє у Celery-таску
        - При розриві з'єднання - намагається перепідключитись
        """
        while True:
            try:
                async with websockets.connect(wss_url) as websocket:
                    logger.info(f"[User {user_id}] Підключено успішно до {wss_url}")
                    self.stdout.write(self.style.SUCCESS(f"[User {user_id}] Підключено успішно."))

                    # Нескінченний цикл читання повідомлень
                    while True:
                        message = await websocket.recv()  # чекаємо вхідне повідомлення
                        close_old_connections()
                        await self.handle_phonet_message(user_id, message)

                    async for message in websocket:
                        print("Got message from Phonet:", message)

            except (OSError, websockets.exceptions.ConnectionClosed) as e:
                logger.warning(f"[User {user_id}] З'єднання втрачено: {e}. Перепідключення через 5с...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[User {user_id}] Непередбачувана помилка: {e}", exc_info=True)
                await asyncio.sleep(10)



    async def handle_phonet_message(self, user_id, raw_message):
        """
        Обробка одного JSON-повідомлення від Phonet. Якщо це подія типу "call.*", відправляємо у Celery.
        """
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            logger.warning(f"[User {user_id}] Невірний JSON: {raw_message}")
            return

        event_type = data.get("event")
        if event_type in ["call.dial", "call.bridge", "call.hangup"]:
            # Приклад: викликаємо Celery-таску, що створить Interaction + CallMessage
            call_data = data.copy()
            call_data["receiver_user_id"] = user_id  # Щоб у тасці знати, кому належить виклик
            process_phonet_call.delay(call_data)

            # (Якщо хочете – можна одразу відправляти group_send тут,
            #  але зазвичай усе роблять усередині Celery-таски.)
            logger.info(f"[User {user_id}] Отримано дзвінок {event_type}, викликаємо Celery.")
        elif event_type == "error":
            logger.error(f"[User {user_id}] Phonet повідомив про помилку: {data}")
        else:
            logger.debug(f"[User {user_id}] Інша подія: {data}")
