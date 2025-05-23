from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from sales.models import Room, Contact
from celery.result import AsyncResult
from django.core.cache import cache
from sales.tasks import import_telegram_contact_task
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates a chat room for a user and contact, and retrieves Telegram data asynchronously'

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

        # Очікуємо результат задачі
        task_id = cache.get(f"telegram_import_task_{room.pk}")
        if not task_id:
            error = cache.get(f"telegram_import_task_{room.pk}_error")
            if error:
                self.stdout.write(self.style.ERROR(f"Error: {error}"))
            else:
                self.stdout.write(self.style.WARNING("No task ID found in cache"))
            return

        self.stdout.write(f"Waiting for Telegram import task (task_id={task_id})...")
        task_result = AsyncResult(task_id, app=import_telegram_contact_task.app)

        # Очікуємо завершення задачі (максимум 60 секунд)
        timeout = 60
        start_time = time.time()
        while not task_result.ready() and (time.time() - start_time) < timeout:
            self.stdout.write(f"Task state: {task_result.state}")
            time.sleep(1)

        if task_result.ready():
            self.stdout.write(f"Task state: {task_result.state}")
            if task_result.state == 'FAILURE':
                exception = task_result.get(propagate=False)
                self.stdout.write(self.style.ERROR(f"Task failed with exception: {exception}"))
            else:
                result = task_result.result
                self.stdout.write(f"Raw task result: {result} (type: {type(result)})")
                if result and isinstance(result, dict):
                    if result.get('imported'):
                        self.stdout.write(self.style.SUCCESS(f"Contact was successfully added to Telegram contacts"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Contact was not added to Telegram contacts"))
                    if result.get('success'):
                        self.stdout.write(self.style.SUCCESS(
                            f"Telegram data retrieved: ID={result['telegram_id']}, Username={result['telegram_username']}"
                        ))
                    else:
                        self.stdout.write(self.style.ERROR(f"Telegram import failed: {result.get('message', 'Unknown error')}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Invalid task result format: {result}"))
        else:
            self.stdout.write(self.style.WARNING("Task did not complete within 60 seconds"))
            self.stdout.write("Check worker logs for task status")