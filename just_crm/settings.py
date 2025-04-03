"""
Django settings for just_crm project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-_k4&)d9@5l4y*w16b$s57o0)5fvlqv39hjnxq0(1p6gj3ks!6h'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['185.65.247.186', '127.0.0.1', 'localhost', '*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'main',
    'sales.apps.SalesConfig',
    'celery',
    'django_celery_beat',
    'sales_analytics',
    'transcription',
    'data_exchange',
    'site_management',
    'rest_framework',

    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'just_crm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'sales.context_processors.attention_notification_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'just_crm.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.mysql',
#        'NAME': 'crm',         # назва бази даних, яку вам надав провайдер
#        'USER': 'crm',            # ім'я користувача для підключення до бази
#        'PASSWORD': 'RHErhe1013',            # пароль для підключення
#        'HOST': 'prdsv558.mysql.network',         # IP-адреса або домен бази даних (зазвичай щось на кшталт db.provider.com)
#        'PORT': '10544',                     # порт, за замовчуванням MySQL використовує 3306
#        # Опціонально, додаткові параметри:
#        'OPTIONS': {
#            'charset': 'utf8mb4',
#            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#        },
#    }
#}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'just_crm_by',         # назва бази даних, яку вам надав провайдер
        'USER': 'just_crm_by',            # ім'я користувача для підключення до бази
        'PASSWORD': 'zT3HVh6d75',            # пароль для підключення
        'HOST': 'prdsv558.mysql.network',         # IP-адреса або домен бази даних (зазвичай щось на кшталт db.provider.com)
        'PORT': '10544',                     # порт, за замовчуванням MySQL використовує 3306
        # Опціонально, додаткові параметри:
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# Шлях до статичних файлів у вашому проєкті (де лежать ваші файли, наприклад, static/main/images)

# Куди Django збереже зібрані статичні файли після виконання collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# URL, за яким статичні файли будуть доступні в браузері
STATIC_URL = "/main/static/"

# (Опціонально) Якщо у вас є додаткові джерела статичних файлів (наприклад, від бібліотек)
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Розклад задач
CELERY_BEAT_SCHEDULE = {
    'check-company-status-every-15-minutes': {
        'task': 'sales.tasks.check_company_task_status_for_users',
        'schedule': 900.0,
    },
    'fetch-visitors-every-15-minutes': {
        'task': 'data_exchange.tasks.fetch_visitors_data',
        'schedule': 900.0,
    },
}

ASGI_APPLICATION = 'just_crm.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = ''


CSRF_TRUSTED_ORIGINS = [
    'https://www.just-look.com.ua',  # Домен сайту
    'https://just-look.com.ua',      # Додай без www, якщо є варіанти
]