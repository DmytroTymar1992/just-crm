from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from sales.models import Room, Contact
from celery.result import AsyncResult
import logging
import time
from django.core.cache import cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creates a chat room for a user and contact, and retrieves Telegram data'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='ID of the user')
        parser.add_argument('contact_id', type=int, help='ID of the contact')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']
        contact_id = kwargs['contact_id']

        try:
            user = User.objects.get(id=user_id)
            contact = Contact.objects.get(id=contact_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
            return
        except Contact.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Contact with ID {contact_id} not found"))
            return

        self.stdout.write(f"Creating chat room for User: {user.username}, Contact: {contact}")
        room = Room.objects.create(user=user, contact=contact)
        self.stdout.write(self.style.SUCCESS(f"Chat room #{room.pk} created successfully"))

        # Очікуємо результат задачі (оскільки вона запускається асинхронно в save())
        task_id = cache.get(f"telegram_import_task_{room.pk}")
        if not task_id:
            error = cache.get(f"telegram_import_task_{room.pk}_error")
            if error:
                self.stdout.write(self.style.ERROR(f"Error: {error}"))
            else:
                self.stdout.write(self.style.WARNING("No task ID found in cache"))
            return

        self.stdout.write(f"Waiting for Telegram import task (task_id={task_id})...")
        task_result = AsyncResult(task_id)

        # Очікуємо завершення задачі (максимум 30 секунд)
        timeout = 30
        start_time = time.time()
        while not task_result.ready() and (time.time() - start_time) < timeout:
            time.sleep(1)

        if task_result.ready():
            result = task_result.result
            if result['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"Telegram data retrieved: ID={result['telegram_id']}, Username={result['telegram_username']}"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"Telegram import failed: {result['message']}"))
        else:
            self.stdout.write(self.style.WARNING("Task did not complete within 30 seconds"))