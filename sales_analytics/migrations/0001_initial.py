# Generated by Django 5.1.6 on 2025-03-25 04:08

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('main', '0005_company_slug'),
        ('sales', '0008_contact_avatar_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagerActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Дата')),
                ('activity_type', models.CharField(choices=[('create_contact', 'Створення контакту'), ('create_company', 'Створення компанії'), ('edit_contact', 'Редагування контакту'), ('edit_company', 'Редагування компанії'), ('create_task', 'Створення задачі'), ('move_task', 'Перенос задачі'), ('edit_task', 'Редагування задачі'), ('complete_task', 'Закриття задачі'), ('telegram_in', 'Телеграм повідомлення вхідне'), ('telegram_out', 'Телеграм повідомлення вихідне'), ('call_in', 'Дзвінок вхідний'), ('call_out', 'Дзвінок вихідний'), ('email_in', 'Емейл вхідний'), ('email_out', 'Емейл вихідний')], max_length=20, verbose_name='Тип діяльності')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='main.company', verbose_name='Компанія')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='sales.contact', verbose_name='Контакт')),
                ('interaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='sales.interaction', verbose_name='Взаємодія')),
                ('manager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL, verbose_name='Менеджер')),
                ('task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='sales.task', verbose_name='Задача')),
            ],
            options={
                'verbose_name': 'Діяльність менеджера',
                'verbose_name_plural': 'Діяльність менеджерів',
            },
        ),
    ]
