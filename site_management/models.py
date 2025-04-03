from django.db import models

class Seeker(models.Model):
    user_id = models.CharField(max_length=50, unique=True, verbose_name="ID користувача")
    first_name = models.CharField("Ім'я", max_length=100, verbose_name="Ім'я")
    last_name = models.CharField("Прізвище", max_length=100, null=True, blank=True, verbose_name="Прізвище")
    phone = models.CharField(max_length=32, null=True, blank=True, verbose_name="Телефон")
    email = models.EmailField("Email", max_length=254, null=True, blank=True, verbose_name="Email")
    created_at = models.DateTimeField("Створено", auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone or self.email or "Безіменний пошуковець"
