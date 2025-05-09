#sales/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Contact, Room, Interaction, TelegramMessage, EmailMessage, CallMessage, ContactLink
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import get_connection, EmailMessage as DjangoEmailMessage, EmailMultiAlternatives
from telethon import TelegramClient
import datetime
import logging
from django.utils import timezone
from main.utils import normalize_phone_number
from telethon.tl.functions.contacts import ImportContactsRequest  # Імпорт функції
from telethon.tl.types import InputPhoneContact



logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def process_telegram_message(message_data):
    receiver_user_id = message_data.get('receiver_user_id')
    try:
        user = User.objects.get(id=receiver_user_id)
    except User.DoesNotExist:
        return

    # Якщо повідомлення надійшло від самого користувача, ігноруємо його
    sender_phone = message_data.get('sender_phone')
    if sender_phone and sender_phone == user.profile.telegram_phone:
        # Можна додатково перевірити sender_id, якщо він збережений
        return

    sender_username = message_data.get('sender_username')
    sender_id = message_data.get('sender_id')
    sender_first_name = message_data.get('sender_first_name')
    sender_last_name = message_data.get('sender_last_name')

    # Ідентифікація контакту
    contact = None
    if sender_phone:
        contact = Contact.objects.filter(phone=sender_phone).first()
    if not contact and sender_username:
        contact = Contact.objects.filter(telegram_username=sender_username).first()
    if not contact and sender_id:
        contact = Contact.objects.filter(telegram_id=sender_id).first()

    if not contact:
        first_name = sender_first_name or sender_phone or sender_username or (str(sender_id) if sender_id else '')
        contact = Contact.objects.create(
            first_name=first_name,
            last_name=sender_last_name or '',
            telegram_id=sender_id,
            telegram_username=sender_username,
            phone=sender_phone,
        )

    if contact.company and contact.company.slug:
        company_part = contact.company.slug
    else:
        company_part = "null"

        # Формуємо URL
    link_url = f"https://www.just-look.com.ua/?utm_company={company_part}_{contact.id}"

    ContactLink.objects.create(contact=contact, url=link_url)

    # Отримуємо або створюємо кімнату (Room) для зв’язку користувача та контакту
    room, _ = Room.objects.get_or_create(user=user, contact=contact)

    # Створюємо Interaction та запис TelegramMessage у транзакції
    with transaction.atomic():
        interaction = Interaction.objects.create(
            interaction_type='telegram',
            room=room,
            sender='contact',  # повідомлення від контакту
            is_read=False,
        )
        TelegramMessage.objects.create(
            interaction=interaction,
            message_id=message_data.get('message_id'),
            chat_id=message_data.get('chat_id'),
            text=message_data.get('text'),
        )



    # Відправка повідомлення до конкретного чату (room)
    channel_layer = get_channel_layer()
    room_group_name = f"sales_room_{room.id}"
    payload = {
        "msg_type": "telegram",
        "body": message_data.get('text'),
        "created_at": interaction.created_at.strftime("%H:%M"),
        "sender_type": "contact",
    }
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            "type": "chat_message",
            "payload": payload,
            "username": "Telegram",
        }
    )

    # Сповіщення RoomListConsumer про оновлення списку кімнат
    user_group_name = f"user_{user.id}"
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            "type": "room_list_update",
        }
    )


@shared_task
def process_email_message(email_data):
    """
    Обробляє вхідне email повідомлення.
    Параметри email_data (dict):
      - subject, body
      - sender_email, sender_name
      - receiver_user_id: ID користувача, для якого отримане повідомлення
    """
    receiver_user_id = email_data.get("receiver_user_id")
    try:
        user = User.objects.get(id=receiver_user_id)
    except User.DoesNotExist:
        return

    sender_email = email_data.get("sender_email")
    sender_name = email_data.get("sender_name")
    subject = email_data.get("subject")
    body = email_data.get("body")

    # Ідентифікація контакту за email
    contact = None
    if sender_email:
        contact = Contact.objects.filter(email=sender_email).first()
    if not contact and sender_name:
        contact = Contact.objects.filter(first_name=sender_name).first()
    if not contact:
        first_name = sender_name or sender_email or "Невідомий"
        contact = Contact.objects.create(
            first_name=first_name,
            last_name="",
            email=sender_email,
        )

    if contact.company and contact.company.slug:
        company_part = contact.company.slug
    else:
        company_part = "null"

        # Формуємо URL
    link_url = f"https://www.just-look.com.ua/?utm_company={company_part}_{contact.id}"

    ContactLink.objects.create(contact=contact, url=link_url)

    # Отримуємо або створюємо кімнату (Room) для зв’язку користувача та контакту
    room, _ = Room.objects.get_or_create(user=user, contact=contact)

    # Створюємо Interaction та запис EmailMessage у транзакції
    with transaction.atomic():
        interaction = Interaction.objects.create(
            interaction_type="email",
            room=room,
            sender="contact",  # повідомлення від контакту
            is_read=False,
        )
        EmailMessage.objects.create(
            interaction=interaction,
            subject=subject,
            body=body,
        )



    # Відправка повідомлення до конкретного чату (room)
    channel_layer = get_channel_layer()
    room_group_name = f"sales_room_{room.id}"
    payload = {
        "msg_type": "email",
        "subject": subject,
        "body": body,
        "created_at": interaction.created_at.strftime("%H:%M"),
        "sender_type": "contact",
    }
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            "type": "chat_message",
            "payload": payload,
            "username": contact.first_name,  # або інше значення
        }
    )

    # Сповіщення RoomListConsumer про оновлення списку кімнат
    user_group_name = f"user_{user.id}"
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            "type": "room_list_update",
        }
    )


from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import get_connection, EmailMultiAlternatives
from sales.utils import render_email_template  # Якщо потрібно генерувати HTML із шаблону

User = get_user_model()


@shared_task
def send_outgoing_email_task(user_id, subject, message, recipient_email, email_type="plain"):
    from django.core.mail import EmailMessage, EmailMultiAlternatives
    from django.contrib.auth import get_user_model

    logger.info(f"Task started for user_id={user_id}, recipient={recipient_email}, subject={subject}, email_type={email_type}")
    logger.debug(f"Message content:\n{message}")

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"User found: {user.username}")
    except User.DoesNotExist:
        logger.error(f"User with id={user_id} not found")
        return "User not found"

    profile = user.profile
    smtp_settings = {
        'host': profile.smtp_host,
        'port': profile.smtp_port,
        'user': profile.smtp_user,
        'password': profile.smtp_password,
        'use_tls': profile.smtp_use_tls,
        'use_ssl': profile.smtp_use_ssl,
    }
    logger.debug(f"SMTP settings: host={smtp_settings['host']}, port={smtp_settings['port']}, user={smtp_settings['user']}")

    try:
        connection = get_connection(
            host=smtp_settings['host'],
            port=smtp_settings['port'],
            username=smtp_settings['user'],
            password=smtp_settings['password'],
            use_tls=smtp_settings['use_tls'],
            use_ssl=smtp_settings['use_ssl']
        )
        logger.info("SMTP connection established")
    except Exception as e:
        logger.error(f"Failed to establish SMTP connection: {str(e)}")
        return f"SMTP connection error: {str(e)}"

    from_email = profile.smtp_user or "default@example.com"

    if email_type == "html":
        msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[recipient_email],
            connection=connection
        )
        msg.content_subtype = "html"
    else:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[recipient_email],
            connection=connection
        )

    try:
        result = msg.send(fail_silently=False)
        logger.info(f"Email sent successfully to {recipient_email}, result={result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return f"Send error: {str(e)}"


# sales/tasks.py
@shared_task
def send_outgoing_telegram_task(user_id, contact_data, message_text):
    from django.contrib.auth import get_user_model
    from telethon.tl.functions.contacts import ImportContactsRequest
    from telethon.tl.types import InputPhoneContact
    from main.utils import normalize_phone_number
    import logging

    logger = logging.getLogger(__name__)
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User with id={user_id} not found")
        return "User not found"

    profile = user.profile
    api_id = profile.telegram_api_id
    api_hash = profile.telegram_api_hash
    phone = profile.telegram_phone
    session_file = getattr(profile, 'telegram_session_file_out', f"{user.username}_out.session")

    client = TelegramClient(session_file, api_id, api_hash)
    start_result = client.start(phone=phone)
    if hasattr(start_result, '__await__'):
        client.loop.run_until_complete(start_result)

    result = None
    contact_phone = contact_data.get('phone')
    normalized_phone = normalize_phone_number(contact_phone) if contact_phone else None

    try:
        # Якщо є номер телефону
        if normalized_phone:
            # Додаємо '+' до номера, як того вимагає Telegram API
            telegram_phone = f"+{normalized_phone}"
            logger.info(f"Processing phone: {telegram_phone}")

            # Спробуємо отримати entity (перевіряємо, чи номер доступний)
            try:
                entity = client.loop.run_until_complete(client.get_entity(telegram_phone))
                telegram_id = entity.id
                logger.info(f"Found Telegram ID for {telegram_phone}: {telegram_id}")
                # Оновлюємо contact_data і базу, якщо telegram_id відсутній
                if not contact_data.get('telegram_id'):
                    contact = Contact.objects.filter(phone=normalized_phone).first()
                    if contact and not contact.telegram_id:
                        contact.telegram_id = telegram_id
                        contact.save()
                        contact_data['telegram_id'] = telegram_id
                # Відправляємо за номером телефону
                result = client.loop.run_until_complete(
                    client.send_message(telegram_phone, message_text)
                )
                logger.info(f"Message sent to phone: {telegram_phone}")
            except ValueError as e:
                logger.warning(f"Phone {telegram_phone} not found in Telegram: {str(e)}")
                # Імпортуємо контакт, якщо його немає
                contact = InputPhoneContact(
                    client_id=0,
                    phone=telegram_phone,
                    first_name=contact_data.get('first_name', 'Contact'),
                    last_name=contact_data.get('last_name', '')
                )
                import_result = client.loop.run_until_complete(
                    client(ImportContactsRequest([contact]))
                )
                logger.info(f"Imported contact {telegram_phone}: {import_result}")
                # Повторна спроба після імпорту
                try:
                    entity = client.loop.run_until_complete(client.get_entity(telegram_phone))
                    telegram_id = entity.id
                    contact_data['telegram_id'] = telegram_id
                    contact = Contact.objects.filter(phone=normalized_phone).first()
                    if contact and not contact.telegram_id:
                        contact.telegram_id = telegram_id
                        contact.save()
                    result = client.loop.run_until_complete(
                        client.send_message(telegram_phone, message_text)
                    )
                    logger.info(f"Message sent to phone after import: {telegram_phone}")
                except Exception as e:
                    logger.error(f"Failed to send to {telegram_phone} after import: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing phone {telegram_phone}: {str(e)}")

        # Якщо відправка за номером не вдалася, пробуємо telegram_id
        if not result and contact_data.get('telegram_id'):
            try:
                result = client.loop.run_until_complete(
                    client.send_message(int(contact_data['telegram_id']), message_text)
                )
                logger.info(f"Message sent to telegram_id: {contact_data['telegram_id']}")
            except Exception as e:
                logger.error(f"Error sending to telegram_id {contact_data['telegram_id']}: {str(e)}")

        # Якщо немає telegram_id, пробуємо telegram_username
        if not result and contact_data.get('telegram_username'):
            try:
                result = client.loop.run_until_complete(
                    client.send_message(contact_data['telegram_username'], message_text)
                )
                logger.info(f"Message sent to username: {contact_data['telegram_username']}")
            except Exception as e:
                logger.error(f"Error sending to username {contact_data['telegram_username']}: {str(e)}")

    except Exception as e:
        logger.error(f"General error in send_outgoing_telegram_task: {str(e)}")

    # Відключення клієнта
    disconnect_coro = client.disconnect()
    if disconnect_coro is not None and hasattr(disconnect_coro, '__await__'):
        client.loop.run_until_complete(disconnect_coro)

    if result:
        return {
            "message_id": result.id,
            "chat_id": getattr(result.to_id, "channel_id", getattr(result.to_id, "user_id", None))
        }
    logger.warning(f"Failed to send message to contact: {contact_data}")
    return None



@shared_task
def process_phonet_call(call_data):
    event_type = call_data.get("event")
    uuid = call_data.get("uuid")
    parent_uuid = call_data.get("parentUuid-tour")
    direction_code = call_data.get("lgDirection")
    receiver_user_id = call_data.get("receiver_user_id")
    leg = call_data.get("leg", {})
    leg_ext = leg.get("ext")

    logger.info(f"Processing Phonet event={event_type} uuid={uuid} direction={direction_code} receiver_user_id={receiver_user_id} leg_ext={leg_ext}")

    # Перевірка користувача
    try:
        user = User.objects.get(id=receiver_user_id)
        if user.profile.phonet_ext != leg_ext:
            logger.warning(f"User {user.id} phonet_ext={user.profile.phonet_ext} does not match leg.ext={leg_ext}")
    except User.DoesNotExist:
        logger.error(f"User with ID={receiver_user_id} does not exist. Skipping call.")
        return

    other_legs = call_data.get("otherLegs", [])
    client_phone = None
    if other_legs and isinstance(other_legs, list):
        client_phone = other_legs[0].get("num")
    if not client_phone:
        client_phone = call_data.get("trunkNum")

    if not client_phone:
        logger.warning(f"No client_phone found in otherLegs/trunkNum for uuid={uuid}, skipping.")
        return

    sender = "contact" if direction_code == 4 else "user"
    activity_type = 'call_in' if direction_code == 4 else 'call_out'

    def ts_to_dt(ts):
        if not ts:
            return None
        return datetime.datetime.utcfromtimestamp(ts / 1000.0).replace(tzinfo=datetime.timezone.utc)

    dial_ts = call_data.get("dialAt")
    bridge_ts = call_data.get("bridgeAt")
    hangup_ts = call_data.get("hangupAt")
    server_ts = call_data.get("serverTime")

    dial_dt = ts_to_dt(dial_ts)
    bridge_dt = ts_to_dt(bridge_ts)
    hangup_dt = ts_to_dt(hangup_ts) or ts_to_dt(server_ts)

    leg_id = leg.get("id")
    leg_name = leg.get("displayName")

    with transaction.atomic():
        contact, created = Contact.objects.get_or_create(
            phone=client_phone,
            defaults={"first_name": client_phone}
        )

        if created:
            if contact.company and contact.company.slug:
                company_part = contact.company.slug
            else:
                company_part = "null"
            link_url = f"https://www.just-look.com.ua/?utm_company={company_part}_{contact.id}"
            ContactLink.objects.create(contact=contact, url=link_url)

        room, _ = Room.objects.get_or_create(user=user, contact=contact)

        try:
            call_msg = CallMessage.objects.select_related('interaction').get(phonet_uuid=uuid)
        except CallMessage.DoesNotExist:
            call_msg = None

        if event_type == "call.dial" and not call_msg:
            interaction = Interaction.objects.create(
                interaction_type="call",
                room=room,
                sender=sender,
                is_read=False,
            )
            call_msg = CallMessage.objects.create(
                interaction=interaction,
                phonet_uuid=uuid,
                parent_uuid=parent_uuid,
                direction=direction_code,
                leg_id=leg_id,
                leg_ext=leg_ext,
                leg_name=leg_name,
                client_phone=client_phone,
                dial_at=dial_dt,
                bridge_at=None,
                hangup_at=None,
            )
            logger.info(f"Created new Interaction+CallMessage for dial uuid={uuid}.")
        elif call_msg:
            interaction = call_msg.interaction
            if event_type == "call.bridge":
                call_msg.bridge_at = bridge_dt or call_msg.bridge_at
                logger.info(f"Updated call.bridge for uuid={uuid}. bridge_at={bridge_dt}")
            elif event_type == "call.hangup":
                call_msg.hangup_at = hangup_dt or call_msg.hangup_at
                logger.info(f"Updated call.hangup for uuid={uuid}. hangup_at={hangup_dt}")
            call_msg.save()
        else:
            interaction = Interaction.objects.create(
                interaction_type="call",
                room=room,
                sender=sender,
                is_read=False,
            )
            call_msg = CallMessage.objects.create(
                interaction=interaction,
                phonet_uuid=uuid,
                parent_uuid=parent_uuid,
                direction=direction_code,
                leg_id=leg_id,
                leg_ext=leg_ext,
                leg_name=leg_name,
                client_phone=client_phone,
                dial_at=dial_dt,
                bridge_at=bridge_dt if event_type == "call.bridge" else None,
                hangup_at=hangup_dt if event_type == "call.hangup" else None,
            )

        # Відправляємо повідомлення при кожному евенті
        channel_layer = get_channel_layer()
        room_group_name = f"sales_room_{room.id}"

        payload = {
            "msg_type": "call",
            "direction": "incoming" if direction_code == 4 else "outgoing",
            "event": event_type,
            "phone": client_phone,
            "uuid": uuid,
            "created_at": interaction.created_at.strftime("%H:%M"),
            "duration": call_msg.duration,
            "dial_at": call_msg.dial_at.strftime("%H:%M:%S") if call_msg.dial_at else "",
            "bridge_at": call_msg.bridge_at.strftime("%H:%M:%S") if call_msg.bridge_at else "",
            "hangup_at": call_msg.hangup_at.strftime("%H:%M:%S") if call_msg.hangup_at else "",
        }

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "chat_message",
                "payload": payload,
                "username": "Phonet",
            }
        )

        user_group_name = f"user_{user.id}"
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                "type": "room_list_update",
            }
        )



from celery import shared_task
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from .models import User, Contact
import logging
import time

logger = logging.getLogger(__name__)

@shared_task
def import_telegram_contact_task(user_id, contact_phone, first_name, last_name):
    result = {'success': False, 'message': None, 'telegram_id': None, 'telegram_username': None, 'imported': False}

    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Задача запущена для user_id={user_id}, phone={contact_phone}")
    except User.DoesNotExist:
        result['message'] = f"User with id={user_id} not found"
        logger.error(result['message'])
        return result

    try:
        profile = user.profile
    except AttributeError:
        result['message'] = f"User {user.username} has no profile"
        logger.error(result['message'])
        return result

    api_id = profile.telegram_api_id
    api_hash = profile.telegram_api_hash
    user_phone = profile.telegram_phone
    session_file = getattr(profile, 'telegram_session_file_out', f"{user.username}_out.session")

    if not all([api_id, api_hash, user_phone]):
        result['message'] = f"Incomplete Telegram credentials for user {user.username}"
        logger.error(result['message'])
        return result

    logger.info(f"Using api_id={api_id}, api_hash={api_hash[:5]}..., session_file={session_file}")
    client = TelegramClient(session_file, api_id, api_hash)
    try:
        # Синхронний запуск клієнта
        logger.info(f"Starting Telegram client for {user_phone}")
        client.start(phone=user_phone)
        logger.info(f"Telegram client started for {user_phone}")

        # Перевіряємо, чи клієнт авторизований
        is_authorized = client.is_user_authorized()
        logger.info(f"Client authorized: {is_authorized}")
        if not is_authorized:
            result['message'] = f"Telegram client not authorized for {user_phone}"
            logger.error(result['message'])
            return result

        telegram_phone = contact_phone  # Номер уже нормалізований
        if not telegram_phone:
            result['message'] = f"Invalid phone number: {contact_phone}"
            logger.warning(result['message'])
            return result

        contact_input = InputPhoneContact(
            client_id=0,
            phone=telegram_phone,
            first_name=first_name or "Contact",
            last_name=last_name or ""
        )

        # Додаємо контакт
        logger.info(f"Importing contact: {telegram_phone}")
        import_result = client(ImportContactsRequest([contact_input]))
        logger.info(f"Full import result: {import_result.to_dict()}")
        if import_result.imported:
            logger.info(f"Contact {telegram_phone} successfully added to Telegram contacts")
            result['imported'] = True
        else:
            logger.warning(f"Contact {telegram_phone} was not added to Telegram contacts: {import_result.to_dict()}")
            result['message'] = f"Failed to add {telegram_phone} to Telegram contacts: {import_result.to_dict()}"
            return result

        # Перевіряємо, чи є користувач у результаті імпорту
        if import_result.users:
            entity = import_result.users[0]
            telegram_id = entity.id
            telegram_username = getattr(entity, 'username', None)
            logger.info(f"Retrieved from import: telegram_id={telegram_id}, username={telegram_username}")
        else:
            # Якщо імпорт не повернув користувача, чекаємо синхронізації з повторними спробами
            logger.info(f"No user in import result, attempting sync with retries...")
            max_attempts = 3
            delay_between_attempts = 5  # 5 секунд між спробами
            for attempt in range(max_attempts):
                time.sleep(delay_between_attempts)
                try:
                    entity = client.get_entity(telegram_phone)
                    telegram_id = entity.id
                    telegram_username = getattr(entity, 'username', None)
                    logger.info(f"Retrieved after sync (attempt {attempt + 1}): telegram_id={telegram_id}, username={telegram_username}")
                    break  # Успіх, виходимо з циклу
                except ValueError as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_attempts - 1:  # Остання спроба
                        result['message'] = f"Could not retrieve entity for {telegram_phone} after {max_attempts} attempts: {str(e)}"
                        logger.error(result['message'])
                        return result

        # Оновлюємо контакт
        contact_obj = Contact.objects.filter(phone=telegram_phone).first()
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
                logger.info(
                    f"Updated Contact {telegram_phone} with telegram_id={telegram_id}, username={telegram_username}")
            else:
                logger.info(f"Contact {telegram_phone} already has up-to-date Telegram data")
            result['success'] = True
            result['telegram_id'] = telegram_id
            result['telegram_username'] = telegram_username
        else:
            result['message'] = f"No Contact found with phone {telegram_phone} in database"
            logger.warning(result['message'])

    except ValueError as e:
        result['message'] = f"Could not retrieve entity for {telegram_phone}: {str(e)}"
        logger.warning(result['message'])
    except Exception as e:
        result['message'] = f"Error importing contact {telegram_phone}: {str(e)}"
        logger.error(result['message'])
    finally:
        client.disconnect()
        logger.info("Telegram client disconnected")

    return result


from django.contrib.auth.models import User
from django.db.models import Exists, OuterRef
from .models import Contact, Task
from main.models import UserProfile, Company
logger = logging.getLogger(__name__)

@shared_task(name="check_company_task_status_for_users")
def check_company_task_status_for_users():
    """
    Періодично перевіряє для всіх активних користувачів,
    чи є у них компанії, де ЖОДЕН з контактів НЕ МАЄ НЕЗАВЕРШЕНИХ завдань.
    """
    logger.info("Starting periodic check for companies needing attention (ignoring completed tasks)...")

    users = User.objects.filter(is_active=True).prefetch_related('profile')

    updated_count = 0
    for user in users:
        try:
            # Знаходимо компанії, за які відповідає користувач,
            # і ВИКЛЮЧАЄМО ті, для яких ІСНУЄ хоча б один контакт,
            # у якого є хоча б одна НЕЗАВЕРШЕНА задача (is_completed=False).
            # Використовуємо 'tasks__' через related_name='tasks' у Task.contact.
            needs_attention = Company.objects.filter(
                responsible=user
            ).exclude(
                Exists(Contact.objects.filter(
                    company=OuterRef('pk'),
                    tasks__is_completed=False # <--- ОСНОВНА ЗМІНА ТУТ
                ))
            ).exists()

            # Подальше оновлення прапорця у профілі користувача залишається таким самим
            profile, created = UserProfile.objects.get_or_create(user=user)

            if profile.has_companies_needing_attention != needs_attention:
                profile.has_companies_needing_attention = needs_attention
                profile.save(update_fields=['has_companies_needing_attention'])
                updated_count += 1
                logger.debug(f"Updated attention flag for user {user.username} to {needs_attention}")
            elif created:
                 profile.has_companies_needing_attention = needs_attention
                 profile.save(update_fields=['has_companies_needing_attention'])
                 logger.debug(f"Initialized attention flag for new profile user {user.username} to {needs_attention}")

        except Exception as e:
            logger.error(f"Error processing user {user.username}: {e}", exc_info=True)

    logger.info(f"Finished periodic check (ignoring completed tasks). Updated flags for {updated_count} users.")
