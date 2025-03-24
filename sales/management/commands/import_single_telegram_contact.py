# sales/management/commands/import_single_telegram_contact.py
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from main.utils import normalize_phone_number
from sales.models import Contact

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = "Імпортує один контакт до Telegram-списку користувача"

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, required=True, help='ID користувача')
        parser.add_argument('--phone', type=str, required=True, help='Номер телефону контакту')
        parser.add_argument('--first_name', type=str, default="Contact", help='Ім’я контакту')
        parser.add_argument('--last_name', type=str, default="", help='Прізвище контакту')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']
        contact_phone = kwargs['phone']
        first_name = kwargs['first_name']
        last_name = kwargs['last_name']

        self.stdout.write(f"Починаємо імпорт контакту {contact_phone} для користувача {user_id}...")
        logger.info(f"Starting import for user_id={user_id}, phone={contact_phone}")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(f"[ERROR] Користувача з id={user_id} не знайдено")
            logger.error(f"User with id={user_id} not found")
            return

        try:
            profile = user.profile
        except AttributeError:
            self.stdout.write(f"[ERROR] Користувач {user.username} не має профілю")
            logger.error(f"User {user.username} has no profile")
            return

        api_id = profile.telegram_api_id
        api_hash = profile.telegram_api_hash
        user_phone = profile.telegram_phone
        session_file = getattr(profile, 'telegram_session_file_out', f"{user.username}_out.session")

        if not all([api_id, api_hash, user_phone]):
            self.stdout.write(f"[ERROR] Неповні Telegram дані для {user.username}")
            logger.error(f"Incomplete Telegram credentials for user {user.username}")
            return

        client = TelegramClient(session_file, api_id, api_hash)
        try:
            # Синхронний запуск клієнта
            client.loop.run_until_complete(client.start(phone=user_phone))
            self.stdout.write(f"Клієнт Telegram запущено для {user_phone}")

            normalized_phone = normalize_phone_number(contact_phone)
            if not normalized_phone:
                self.stdout.write(f"[WARNING] Некоректний номер: {contact_phone}")
                logger.warning(f"Invalid phone number: {contact_phone}")
                return
            telegram_phone = normalized_phone

            contact_input = InputPhoneContact(
                client_id=0,
                phone=telegram_phone,
                first_name=first_name,
                last_name=last_name
            )

            logger.info(f"Importing contact: {telegram_phone}")
            import_result = client.loop.run_until_complete(client(ImportContactsRequest([contact_input])))
            self.stdout.write(f"Імпортовано контакт: {telegram_phone}")
            logger.info(f"Imported contact {telegram_phone}: {import_result}")

            entity = client.loop.run_until_complete(client.get_entity(telegram_phone))
            telegram_id = entity.id
            telegram_username = getattr(entity, 'username', None)
            self.stdout.write(f"Отримано telegram_id={telegram_id}, username={telegram_username} для {telegram_phone}")
            logger.info(f"Retrieved telegram_id={telegram_id}, username={telegram_username} for {telegram_phone}")

            contact_obj = Contact.objects.filter(phone=normalized_phone).first()
            if contact_obj:
                needs_save = False
                if telegram_id and contact_obj.telegram_id != telegram_id:
                    contact_obj.telegram_id = telegram_id
                    needs_save = True
                if telegram_username and contact_obj.telegram_username != telegram_username:
                    contact_obj.telegram_username = telegram_username
                    needs_save = True
                if needs_save:
                    contact_obj.save()
                    self.stdout.write(f"Оновлено Contact {normalized_phone} з telegram_id={telegram_id}, username={telegram_username}")
                    logger.info(f"Updated Contact {normalized_phone} with telegram_id={telegram_id}, username={telegram_username}")
                else:
                    self.stdout.write(f"Контакт {normalized_phone} уже має актуальні дані")
                    logger.info(f"Contact {normalized_phone} already has up-to-date data")

        except ValueError as e:
            self.stdout.write(f"[WARNING] Не вдалося отримати entity для {telegram_phone}: {str(e)}")
            logger.warning(f"Could not retrieve entity for {telegram_phone}: {str(e)}")
        except Exception as e:
            self.stdout.write(f"[ERROR] Помилка імпорту: {str(e)}")
            logger.error(f"Error during import: {str(e)}")
        finally:
            client.loop.run_until_complete(client.disconnect())
            self.stdout.write("Завершено")