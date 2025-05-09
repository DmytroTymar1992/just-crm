# Generated by Django 5.1.6 on 2025-03-04 09:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0005_vacancy_is_hot_vacancy_robota_company_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=1000, verbose_name='Посилання')),
                ('contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sales.contact', verbose_name='Контакт')),
            ],
        ),
    ]
