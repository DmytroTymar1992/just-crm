# sales/management/commands/import_all_telegram_contacts.py
import logging
from django.core.management.base import BaseCommand
from sales.models import Room
from sales.tasks import import_telegram_contact_task
from main.utils import normalize_phone_number

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Синхронно імпортує всі номери телефонів із існуючих Room до Telegram-списків користувачів"

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо імпорт контактів до Telegram...")
        logger.info("Starting import for all existing rooms")

        # Отримуємо всі Room із номерами телефонів у контактів
        rooms = Room.objects.select_related('user', 'contact').filter(contact__phone__isnull=False)
        total_rooms = rooms.count()
        self.stdout.write(f"Знайдено {total_rooms} чатів для обробки")
        logger.info(f"Starting import for {total_rooms} rooms")

        for idx, room in enumerate(rooms, 1):
            user = room.user
            contact = room.contact
            normalized_phone = normalize_phone_number(contact.phone)

            if normalized_phone:
                self.stdout.write(f"Обробка контакту {normalized_phone} (Room #{room.id}, User: {user.username})")
                logger.info(f"Processing contact {normalized_phone} (Room #{room.id}, User: {user.username})")
                try:
                    # Синхронно викликаємо функцію імпорту
                    import_telegram_contact_task(user.id, normalized_phone, contact.first_name, contact.last_name)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Помилка імпорту для {normalized_phone}: {str(e)}"))
                    logger.error(f"Error processing {normalized_phone}: {str(e)}")
            else:
                self.stdout.write(f"Пропущено Room #{room.id} - некоректний номер: {contact.phone}")
                logger.warning(f"Skipping Room #{room.id} - invalid phone: {contact.phone}")

            # Виводимо прогрес
            if idx % 10 == 0 or idx == total_rooms:
                self.stdout.write(f"Оброблено {idx}/{total_rooms} чатів")
                logger.info(f"Processed {idx}/{total_rooms} rooms")

        self.stdout.write(self.style.SUCCESS("Імпорт завершено"))
        logger.info("Finished importing all existing rooms")