# sales/management/commands/normalize_contact_phones.py
import logging
from django.core.management.base import BaseCommand
from sales.models import Contact
from main.utils import normalize_phone_number

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Нормалізує номери телефонів усіх контактів до формату +380XXXXXXXXX"

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо нормалізацію номерів телефонів контактів...")
        logger.info("Starting phone number normalization for all contacts")

        # Отримуємо всі контакти з номерами телефонів
        contacts = Contact.objects.filter(phone__isnull=False)
        total_contacts = contacts.count()
        self.stdout.write(f"Знайдено {total_contacts} контактів із номерами для обробки")
        logger.info(f"Found {total_contacts} contacts with phone numbers")

        updated_count = 0
        for idx, contact in enumerate(contacts, 1):
            original_phone = contact.phone
            normalized_phone = normalize_phone_number(original_phone)

            if normalized_phone and normalized_phone != original_phone:
                # Якщо номер нормалізовано і він відрізняється від оригінального
                contact.phone = normalized_phone
                contact.save(update_fields=['phone'])
                updated_count += 1
                self.stdout.write(f"Оновлено контакт #{contact.id}: {original_phone} -> {normalized_phone}")
                logger.info(f"Updated contact #{contact.id}: {original_phone} -> {normalized_phone}")
            elif not normalized_phone:
                # Якщо номер некоректний
                self.stdout.write(f"[WARNING] Некоректний номер у контакті #{contact.id}: {original_phone}")
                logger.warning(f"Invalid phone number for contact #{contact.id}: {original_phone}")
            # Якщо номер уже нормалізований, пропускаємо без повідомлення

            # Виводимо прогрес кожні 100 записів або в кінці
            if idx % 100 == 0 or idx == total_contacts:
                self.stdout.write(f"Оброблено {idx}/{total_contacts} контактів (оновлено: {updated_count})")
                logger.info(f"Processed {idx}/{total_contacts} contacts (updated: {updated_count})")

        self.stdout.write(f"Нормалізація завершена. Оновлено {updated_count} із {total_contacts} номерів.")
        logger.info(f"Normalization completed. Updated {updated_count} out of {total_contacts} phone numbers.")