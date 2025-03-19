import time
import imaplib
import email
from email.header import decode_header
import re

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from sales.tasks import process_email_message

User = get_user_model()


class Command(BaseCommand):
    help = "Запуск email клієнта для заданого користувача"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user_id',
            type=int,
            required=True,
            help='ID користувача, для якого запускається email клієнт'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Користувача з id {user_id} не знайдено."))
            return

        # Отримуємо дані email з профілю користувача
        user_profile = user.profile
        if not user_profile.email_enabled:
            self.stdout.write(self.style.ERROR("Email не увімкнено для цього користувача."))
            return

        imap_host = user_profile.email_imap_host
        imap_port = user_profile.email_imap_port
        imap_user = user_profile.email_imap_user
        imap_password = user_profile.email_imap_password
        use_ssl = user_profile.email_imap_ssl

        if not all([imap_host, imap_port, imap_user, imap_password]):
            self.stdout.write(self.style.ERROR("Невірно заповнені email дані у профілі користувача."))
            return

        # Підключення до IMAP сервера
        try:
            if use_ssl:
                mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            else:
                mail = imaplib.IMAP4(imap_host, imap_port)
            mail.login(imap_user, imap_password)
            self.stdout.write(self.style.SUCCESS("Підключення до IMAP сервера встановлено."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Помилка підключення до IMAP сервера: {e}"))
            return

        # Вибір папки "INBOX"
        mail.select("inbox")
        self.stdout.write(self.style.SUCCESS("Email клієнт запущено, очікування повідомлень..."))

        while True:
            try:
                # Пошук непрочитаних листів
                status, messages = mail.search(None, '(UNSEEN)')
                if status != "OK":
                    self.stdout.write("Помилка пошуку листів.")
                    time.sleep(10)
                    continue

                mail_ids = messages[0].split()
                for mail_id in mail_ids:
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status != "OK":
                        self.stdout.write("Помилка отримання листа.")
                        continue

                    for response in msg_data:
                        if isinstance(response, tuple):
                            msg = email.message_from_bytes(response[1])
                            # Розбір Subject
                            subject, encoding = decode_header(msg.get("Subject"))[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8", errors="replace")

                            # Розбір From (наприклад, "Name <email@example.com>")
                            from_ = msg.get("From")
                            sender_email = None
                            sender_name = ""
                            if from_:
                                match = re.match(r'(.*)<(.+?)>', from_)
                                if match:
                                    sender_name = match.group(1).strip().strip('"')
                                    sender_email = match.group(2).strip()
                                else:
                                    sender_email = from_.strip()

                            # Отримання тіла листа
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        try:
                                            body_bytes = part.get_payload(decode=True)
                                            charset = part.get_content_charset()
                                            body = body_bytes.decode(charset if charset else "utf-8", errors="replace")
                                            break
                                        except Exception:
                                            continue
                            else:
                                body_bytes = msg.get_payload(decode=True)
                                charset = msg.get_content_charset()
                                body = body_bytes.decode(charset if charset else "utf-8", errors="replace")

                            email_data = {
                                "subject": subject,
                                "body": body,
                                "sender_email": sender_email,
                                "sender_name": sender_name,
                                "receiver_user_id": user_id,
                            }
                            # Викликаємо Celery задачу для обробки email
                            process_email_message.delay(email_data)
                            # Позначаємо лист як прочитаний
                            mail.store(mail_id, '+FLAGS', '\\Seen')
                time.sleep(10)  # Перевірка нових листів кожні 10 секунд
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Помилка під час перевірки листів: {e}"))
                time.sleep(10)
