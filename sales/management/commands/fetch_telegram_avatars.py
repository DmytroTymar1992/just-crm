from django.core.management.base import BaseCommand
from django.core.files import File
from sales.models import User, Contact
from telethon.sync import TelegramClient
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches Telegram avatars for all contacts and saves them to the avatar field'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='ID of the user whose Telegram credentials will be used')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']

        try:
            user = User.objects.get(id=user_id)
            logger.info(f"Використовуємо користувача: {user.username}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
            return

        try:
            profile = user.profile
        except AttributeError:
            self.stdout.write(self.style.ERROR(f"User {user.username} has no profile"))
            return

        api_id = profile.telegram_api_id
        api_hash = profile.telegram_api_hash
        user_phone = profile.telegram_phone
        session_file = getattr(profile, 'telegram_session_file_out', f"{user.username}_out.session")

        if not all([api_id, api_hash, user_phone]):
            self.stdout.write(self.style.ERROR(f"Incomplete Telegram credentials for user {user.username}"))
            return

        client = TelegramClient(session_file, api_id, api_hash)
        try:
            client.start(phone=user_phone)
            if not client.is_user_authorized():
                self.stdout.write(self.style.ERROR(f"Telegram client not authorized for {user_phone}"))
                return
            self.stdout.write(self.style.SUCCESS(f"Telegram client started for {user_phone}"))

            contacts = Contact.objects.filter(telegram_id__isnull=False) | Contact.objects.filter(telegram_username__isnull=False)
            for contact in contacts:
                identifier = contact.telegram_id or contact.telegram_username
                if not identifier:
                    continue

                self.stdout.write(f"Processing contact: {contact} (ID: {identifier})")
                try:
                    # Завантажуємо аватар профілю
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        photo_path = client.download_profile_photo(identifier, file=temp_file.name)
                        if photo_path:
                            with open(temp_file.name, 'rb') as f:
                                file_name = f"avatar_{contact.id}.jpg"
                                contact.avatar.save(file_name, File(f))
                                contact.save()
                            os.unlink(temp_file.name)
                            self.stdout.write(self.style.SUCCESS(f"Avatar saved for {contact}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"No avatar found for {contact}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching avatar for {contact}: {str(e)}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error with Telegram client: {str(e)}"))
        finally:
            client.disconnect()
            self.stdout.write(self.style.SUCCESS("Telegram client disconnected"))