from django.db import models
from main.models import Company
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class Contact(models.Model):
    company = models.ForeignKey(Company,
                                on_delete=models.CASCADE,
                                related_name="contacts",
                                verbose_name="Компанія",
                                null=True,
                                blank=True)
    first_name = models.CharField("Ім'я", max_length=100)
    last_name = models.CharField("Прізвище", max_length=100, null=True, blank=True)
    position = models.CharField("Посада", max_length=100, blank=True, null=True)
    created_at = models.DateTimeField("Створено", auto_now_add=True)



    telegram_id = models.BigIntegerField(null=True,blank=True, unique=True, verbose_name="Telegram ID")
    telegram_username = models.CharField(max_length=100, null=True, blank=True, verbose_name="Telegram Username")
    phone = models.CharField(max_length=32, null=True, blank=True, verbose_name="Телефон")
    email = models.EmailField("Email", max_length=254, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Room(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms', verbose_name="Користувач")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='rooms', verbose_name="Контакт")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room #{self.pk} (User: {self.user.username} - Contact: {self.contact})"

    #class Meta:
    #    unique_together = ('user', 'contact')


class Interaction(models.Model):
    # Типи взаємодій:
    TELEGRAM = 'telegram'
    EMAIL = 'email'
    TASK = 'task'
    CALL = 'call'
    CHAT = 'chat'
    INTERACTION_TYPES = [
        (TELEGRAM, 'Telegram'),
        (EMAIL, 'Email'),
        (TASK, 'Task'),
        (CALL, 'Call'),
        (CHAT, 'Chat'),
    ]

    # Хто відправник?
    SENDER_CHOICES = [
        ('user', 'User'),
        ('contact', 'Contact'),
    ]

    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='interactions')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    is_read = models.BooleanField("Прочитано", default=False)

    def __str__(self):
        return f"[{self.interaction_type}] in Room {self.room_id} by {self.sender}"


class EmailMessage(models.Model):
    # Кожен email-прив’язаний до одного Interaction
    interaction = models.OneToOneField(
        Interaction,
        on_delete=models.CASCADE,
        related_name='email_message'
    )
    subject = models.CharField(max_length=255, verbose_name="Тема листа")
    body = models.TextField(verbose_name="Текст листа", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Можна використовувати Interaction.created_at, але іноді зручно мати свій timestamp

    # Інші поля, якщо потрібно:
    # from_email = models.EmailField(...)
    # to_email = models.EmailField(...)
    # attachments = ...
    # і т.д.

    def __str__(self):
        return f"Email #{self.pk} (Interaction {self.interaction_id})"


class TelegramMessage(models.Model):
    """
    Зберігає конкретне Telegram-повідомлення,
    прив'язане до Interaction із типом 'telegram'.
    """
    interaction = models.OneToOneField(Interaction, on_delete=models.CASCADE, related_name='telegram_message')

    # Унікальний id повідомлення в Telegram
    # (для вхідних і вихідних, щоб уникати дублювань)
    message_id = models.BigIntegerField("Message ID у Telegram", null=True, blank=True)

    # Можна зберігати також chat_id, якщо потрібно
    chat_id = models.BigIntegerField("ID чату/діалогу", null=True, blank=True)

    # Текст
    text = models.TextField("Текст повідомлення", blank=True, null=True)

    # Додаткові поля за бажанням:
    # date = models.DateTimeField("Час відправлення TG", null=True, blank=True)
    # media_type = ...
    # file_id = ... (якщо пересилають фото/документи)
    # від кого: user_id (якщо треба зберегти)
    # ...

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TG msg ID={self.message_id} (Interaction {self.interaction_id})"


class CallMessage(models.Model):
    """
    Модель для зберігання деталей дзвінка від Phonet (або іншої телефонії).
    OneToOneField -> зв'язана з Interaction (type='call').
    """
    interaction = models.OneToOneField(Interaction, on_delete=models.CASCADE, related_name='call_message', verbose_name="Взаємодія (дзвінок)")
    phonet_uuid = models.CharField(max_length=100, blank=True, null=True, verbose_name="Унікальний UUID від Phonet")
    parent_uuid = models.CharField(max_length=100, blank=True, null=True, verbose_name="UUID батьківського виклику, якщо є")
    direction = models.PositiveSmallIntegerField(verbose_name="Напрямок дзвінка", help_text="1=internal, 2=outgoing, 4=incoming, etc.")
    leg_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Leg ID (Phonet)")
    leg_ext = models.CharField(max_length=50, blank=True, null=True, verbose_name="Внутр. номер (ext) користувача")
    leg_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ім'я/назва користувача (Phonet)")
    client_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Телефон клієнта")
    dial_at = models.DateTimeField(blank=True, null=True, verbose_name="Час початку дзвінка (call.dial)")
    bridge_at = models.DateTimeField(blank=True, null=True, verbose_name="Час підняття слухавки (call.bridge)")
    hangup_at = models.DateTimeField(blank=True, null=True, verbose_name="Час завершення дзвінка (call.hangup)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення запису")

    def __str__(self):
        return f"CallMessage #{self.pk} (UUID={self.phonet_uuid})"

    @property
    def duration(self):
        """
        Можна обчислити тривалість розмови, якщо є bridge_at і hangup_at
        """
        if self.bridge_at and self.hangup_at:
            return (self.hangup_at - self.bridge_at).total_seconds()
        return 0


class Vacancy(models.Model):
    WORK_CHOICES = (
        ('work', 'Work'),
        ('robota', 'Robota'),
        ('just', 'Just'),
    )

    title = models.CharField(max_length=255, verbose_name="Тайтл")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата створення")
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оновлення")
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        related_name="vacancies",
        verbose_name="Компанія",
        null=True,
        blank=True
    )
    placement = models.CharField(
        max_length=20,
        choices=WORK_CHOICES,
        verbose_name="Розміщення"
    )
    work_id = models.IntegerField(null=True, blank=True, verbose_name="Work.ua ID")
    robota_id = models.IntegerField(null=True, blank=True, verbose_name="Robota.ua ID")
    just_id = models.IntegerField(null=True, blank=True, verbose_name="Just ID")
    city = models.CharField(max_length=255, null=True, blank=True, verbose_name="Місто")
    work_company_id = models.IntegerField(null=True, blank=True, verbose_name="Work компані ID")
    robota_company_id = models.IntegerField(null=True, blank=True, verbose_name="Robota компані ID")
    is_hot = models.BooleanField(default=False, verbose_name="Гаряча вакансія")

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['work_company_id']),  # Індекс для швидкого пошуку за work_company_id
        ]

class ContactLink(models.Model):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        verbose_name="Контакт"
    )
    url = models.URLField(
        max_length=1000,
        verbose_name="Посилання"
    )

    def __str__(self):
        return self.url


class Task(models.Model):
    # Типи завдань
    TASK_TYPE_CHOICES = [
        ('call', 'Дзвінок'),
        ('email', 'Лист'),
        ('message', 'Повідомлення'),
    ]

    # Атрибути моделі
    created_at = models.DateTimeField("Дата створення", auto_now_add=True)
    task_date = models.DateTimeField("Дата задачі")
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Контакт"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Користувач"
    )
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        verbose_name="Тип задачі"
    )
    target = models.CharField(max_length=255, verbose_name="Ціль")  # Змінено на CharField, якщо потрібна інша модель, уточніть
    description = models.TextField("Опис", blank=True, null=True)
    is_completed = models.BooleanField("Статус", default=False)
    completed_at = models.DateTimeField("Дата виконання", blank=True, null=True)

    def __str__(self):
        return f"Task {self.task_type} for {self.contact} by {self.user} - {self.subject}"

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачі"