from django.db import models
from django.contrib.auth.models import User
from slugify import slugify


class CompanyJust(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва CompanyJust")
    # Додаткові поля за потреби

    def __str__(self):
        return self.name


class Company(models.Model):

    name = models.CharField(max_length=255, verbose_name="Назва")
    work_id = models.IntegerField(blank=True, null=True, verbose_name="Work.ua ID")
    robota_id = models.IntegerField(blank=True, null=True, verbose_name="Robota.ua ID")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата створення")
    responsible = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Відповідальний"
    )
    just_id = models.ForeignKey(
        CompanyJust,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="CompanyJust"
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Slug"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            # "Компанія" -> "kompaniia"
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_api_id = models.BigIntegerField(null=True, blank=True)
    telegram_api_hash = models.CharField(max_length=64, null=True, blank=True)
    telegram_phone = models.CharField(max_length=32, null=True, blank=True)
    telegram_session_file = models.CharField(max_length=128, null=True, blank=True)
    telegram_session_file_out = models.CharField(max_length=128, null=True, blank=True)  # для out-сесії
    telegram_enabled = models.BooleanField(default=False)

    email_enabled = models.BooleanField(default=False)
    email_imap_host = models.CharField(max_length=255, null=True, blank=True)
    email_imap_port = models.PositiveIntegerField(null=True, blank=True, default=993)
    email_imap_user = models.CharField(max_length=255, null=True, blank=True)
    email_imap_password = models.CharField(max_length=255, null=True, blank=True)
    email_imap_ssl = models.BooleanField(default=True)

    smtp_host = models.CharField(max_length=255, null=True, blank=True)
    smtp_port = models.PositiveIntegerField(null=True, blank=True, default=587)
    smtp_user = models.CharField(max_length=255, null=True, blank=True)
    smtp_password = models.CharField(max_length=255, null=True, blank=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_use_tls = models.BooleanField(default=True)

    # Нові поля для Phonet:
    phonet_ext = models.CharField(max_length=32, null=True, blank=True, help_text="Внутрішній номер (ext) співробітника в Phonet")
    phonet_enabled = models.BooleanField(default=False, help_text="Активувати прослуховування викликів для цього користувача?")

    has_companies_needing_attention = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

