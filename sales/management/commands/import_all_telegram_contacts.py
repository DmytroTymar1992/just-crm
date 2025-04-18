# sales/management/commands/import_all_telegram_contacts.py
import asyncio
import logging
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from sales.models import Room, Contact
from main.utils import normalize_phone_number  # Змінено на sales.utils
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Асинхронні обгортки для операцій із базою
async_get_rooms = sync_to_async(
    lambda: list(Room.objects.select_related('user', 'contact').filter(contact__phone__isnull=False)))
async_save_contact = sync_to_async(lambda contact: contact.save())


async def import_contact(user, contact, stdout):
    # Профіль уже перевірено в handle
    profile = user.profile
    api_id = profile.telegram_api_id
    api_hash = profile.telegram_api_hash
    user_phone = profile.telegram_phone
    session_file = getattr(profile, 'telegram_session_file_out', f"{user.username}_out.session")

    if not all([api_id, api_hash, user_phone]):
        stdout.write(f"[ERROR] Неповні Telegram дані для {user.username}")
        logger.error(f"Incomplete Telegram credentials for user {user.username}")
        return

    client = TelegramClient(session_file, api_id, api_hash)
    await client.start(phone=user_phone)

    normalized_phone = normalize_phone_number(contact.phone)
    if not normalized_phone:
        stdout.write(f"[WARNING] Пропущено контакт із некоректним номером: {contact.phone}")
        logger.warning(f"Invalid phone number: {contact.phone}")
        return
    telegram_phone = normalized_phone  # Уже з '+'

    contact_input = InputPhoneContact(
        client_id=0,
        phone=telegram_phone,
        first_name=contact.first_name or "Contact",
        last_name=contact.last_name or ""
    )
    try:
        logger.info(f"Importing contact: {telegram_phone}")
        import_result = await client(ImportContactsRequest([contact_input]))
        stdout.write(f"Імпортовано контакт: {telegram_phone}")
        logger.info(f"Imported contact {telegram_phone}: {import_result}")

        entity = await client.get_entity(telegram_phone)
        telegram_id = entity.id
        telegram_username = getattr(entity, 'username', None)
        stdout.write(f"Отримано telegram_id={telegram_id}, username={telegram_username} для {telegram_phone}")
        logger.info(f"Retrieved telegram_id={telegram_id}, username={telegram_username} for {telegram_phone}")

        # Завжди оновлюємо обидва поля, якщо вони отримані
        needs_save = False
        if telegram_id and contact.telegram_id != telegram_id:
            contact.telegram_id = telegram_id
            needs_save = True
        if telegram_username and contact.telegram_username != telegram_username:
            contact.telegram_username = telegram_username
            needs_save = True
        if needs_save:
            await async_save_contact(contact)
            stdout.write(
                f"Оновлено Contact {normalized_phone} з telegram_id={telegram_id}, username={telegram_username}")
            logger.info(
                f"Updated Contact {normalized_phone} with telegram_id={telegram_id}, username={telegram_username}")
        else:
            stdout.write(f"Контакт {normalized_phone} уже має актуальні дані")
            logger.info(f"Contact {normalized_phone} already has up-to-date data")

    except ValueError as e:
        stdout.write(f"[WARNING] Не вдалося отримати entity для {telegram_phone}: {str(e)}")
        logger.warning(f"Could not retrieve entity for {telegram_phone}: {str(e)}")
    except Exception as e:
        stdout.write(f"[ERROR] Помилка імпорту для {telegram_phone}: {str(e)}")
        logger.error(f"Error importing contact {telegram_phone}: {str(e)}")
    finally:
        await client.disconnect()


class Command(BaseCommand):
    help = "Синхронно імпортує всі номери телефонів із існуючих Room до Telegram-списків користувачів"

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо імпорт контактів до Telegram...")
        logger.info("Starting import for all existing rooms")

        loop = asyncio.get_event_loop()
        rooms = loop.run_until_complete(async_get_rooms())
        total_rooms = len(rooms)
        self.stdout.write(f"Знайдено {total_rooms} чатів для обробки")
        logger.info(f"Starting import for {total_rooms} rooms")

        for idx, room in enumerate(rooms, 1):
            user = room.user
            contact = room.contact
            normalized_phone = normalize_phone_number(contact.phone)

            if normalized_phone:
                if not hasattr(user, 'profile'):
                    self.stdout.write(f"[WARNING] Пропущено Room #{room.id}: Користувач {user.username} не має профілю")
                    logger.warning(f"Skipping Room #{room.id} - User {user.username} has no profile")
                    continue

                self.stdout.write(f"Обробка контакту {normalized_phone} (Room #{room.id}, User: {user.username})")
                logger.info(f"Processing contact {normalized_phone} (Room #{room.id}, User: {user.username})")
                loop.run_until_complete(import_contact(user, contact, self.stdout))
            else:
                self.stdout.write(f"[WARNING] Пропущено Room #{room.id} - некоректний номер: {contact.phone}")
                logger.warning(f"Skipping Room #{room.id} - invalid phone: {contact.phone}")

            if idx % 10 == 0 or idx == total_rooms:
                self.stdout.write(f"Оброблено {idx}/{total_rooms} чатів")
                logger.info(f"Processed {idx}/{total_rooms} rooms")

        self.stdout.write("Імпорт завершено")
        logger.info("Finished importing all existing rooms")