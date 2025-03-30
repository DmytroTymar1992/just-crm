# context_processors.py

import logging

logger = logging.getLogger(__name__)

def attention_notification_processor(request):
    show_modal = False # Значення за замовчуванням
    if request.user.is_authenticated:
        try:
            # Пробуємо отримати прапорець з профілю
            # request.user.profile може бути вже завантажено через prefetch/select_related
            # або кешовано Django auth middleware, якщо використовується стандартний User
            profile = getattr(request.user, 'profile', None) # Безпечне отримання профілю
            if profile:
                 show_modal = profile.has_companies_needing_attention
            else:
                 # Якщо профілю немає, можливо, варто його створити або просто вважати, що повідомлення не потрібне
                 pass

        except AttributeError:
             # На випадок, якщо модель User не має зв'язку 'profile' або він ще не створений
             pass
        except Exception as e:
             # Логування неочікуваних помилок
             logger.error(f"Error in attention_notification_processor for user {request.user.id}: {e}")

    return {'show_attention_modal': show_modal}

# Не забудьте додати процесор до налаштувань TEMPLATES