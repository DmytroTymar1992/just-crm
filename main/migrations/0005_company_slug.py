# Generated by Django 5.1.6 on 2025-03-04 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_companyjust_company_created_at_company_responsible_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True, unique=True, verbose_name='Slug'),
        ),
    ]
