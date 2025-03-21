from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from sales.models import Contact, Task, Interaction
from main.models import Company

User = get_user_model()

class ManagerActivity(models.Model):
    ACTIVITY_TYPES = (
        ('create_contact', 'Створення контакту'),
        ('create_company', 'Створення компанії'),
        ('edit_contact', 'Редагування контакту'),
        ('edit_company', 'Редагування компанії'),
        ('create_task', 'Створення задачі'),
        ('move_task', 'Перенос задачі'),
        ('edit_task', 'Редагування задачі'),
        ('complete_task', 'Закриття задачі'),
        ('telegram_in', 'Телеграм повідомлення вхідне'),
        ('telegram_out', 'Телеграм повідомлення вихідне'),
        ('call_in', 'Дзвінок вхідний'),
        ('call_out', 'Дзвінок вихідний'),
        ('email_in', 'Емейл вхідний'),
        ('email_out', 'Емейл вихідний'),
    )

    date = models.DateTimeField("Дата", auto_now_add=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name="Менеджер"
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        verbose_name="Тип діяльності"
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Контакт"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Компанія"
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Задача"
    )
    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Взаємодія"
    )

    def __str__(self):
        return f"{self.manager} - {self.get_activity_type_display()} - {self.date}"

    class Meta:
        verbose_name = "Діяльність менеджера"
        verbose_name_plural = "Діяльність менеджерів"