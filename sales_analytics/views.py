# sales_analytics/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import ManagerActivity
from main.models import Company
from sales.models import Contact
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

User = get_user_model()

@login_required
def analytics_dashboard(request):
    # Фільтри
    manager_id = request.GET.get('manager', 'all')
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')

    # Встановлюємо період за замовчуванням: сьогодні та -7 днів
    today = timezone.now().date()
    default_date_from = today - timedelta(days=7)
    default_date_to = today

    # Якщо дати не вказані, використовуємо період за замовчуванням
    if not date_from_str:
        date_from = default_date_from
        date_from_str = date_from.strftime('%Y-%m-%d')
    else:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')

    if not date_to_str:
        date_to = default_date_to
        date_to_str = date_to.strftime('%Y-%m-%d')
    else:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')

    # Базовий queryset із фільтром по датах
    activities = ManagerActivity.objects.filter(
        date__gte=date_from,
        date__lt=date_to + timedelta(days=1)  # Включаємо весь день date_to
    )

    # Фільтр по менеджеру
    if manager_id != 'all' and manager_id:
        activities = activities.filter(manager_id=manager_id)
        selected_manager = User.objects.get(id=manager_id)
    else:
        selected_manager = None

    # Отримання всіх менеджерів для фільтра
    managers = User.objects.all()

    # Дані для діаграм
    # Загальна кількість створених компаній за період (усіма менеджерами)
    total_created_companies = ManagerActivity.objects.filter(
        activity_type='create_company',
        date__gte=date_from,
        date__lt=date_to + timedelta(days=1)
    ).count()

    # Загальна кількість створених контактів за період (усіма менеджерами)
    total_created_contacts = ManagerActivity.objects.filter(
        activity_type='create_contact',
        date__gte=date_from,
        date__lt=date_to + timedelta(days=1)
    ).count()

    # Кількість створених компаній і контактів вибраним менеджером за період
    if selected_manager:
        manager_created_companies = activities.filter(activity_type='create_company').count()
        manager_created_contacts = activities.filter(activity_type='create_contact').count()
    else:
        # Якщо вибрано "Всі", показуємо загальну кількість для всіх менеджерів
        manager_created_companies = total_created_companies
        manager_created_contacts = total_created_contacts

    # Дзвінки за період
    incoming_calls = activities.filter(activity_type='call_in').count()
    outgoing_calls = activities.filter(activity_type='call_out').count()

    # Дані для логу
    log_entries = activities.order_by('-date')[:50]

    context = {
        'managers': managers,
        'selected_manager': manager_id,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'total_created_companies': total_created_companies,
        'manager_created_companies': manager_created_companies,
        'total_created_contacts': total_created_contacts,
        'manager_created_contacts': manager_created_contacts,
        'incoming_calls': incoming_calls,
        'outgoing_calls': outgoing_calls,
        'log_entries': log_entries,
    }
    return render(request, 'sales_analytics/analytics_dashboard.html', context)


@login_required # Захищаємо сторінку, доступ тільки для залогінених
def companies_needs_attention_list(request):
    """
    Відображає список компаній, що потребують уваги (немає незавершених завдань у контактів),
    з можливістю фільтрації за відповідальним користувачем.
    """

    # Отримуємо список користувачів для фільтру.
    # Можна взяти всіх активних, або тільки тих, хто є відповідальним хоч за одну компанію
    users_for_filter = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    # Або, для ефективності, якщо багато користувачів:
    # responsible_user_ids = Company.objects.values_list('responsible_user_id', flat=True).distinct()
    # users_for_filter = User.objects.filter(pk__in=responsible_user_ids, is_active=True).order_by('last_name', 'first_name')


    # Базовий запит: знаходимо компанії, де НЕМАЄ контактів з незавершеними завданнями
    # Тобто, виключаємо компанії, де Є хоча б один контакт з is_completed=False
    companies_query = Company.objects.exclude(
        contacts__tasks__is_completed=False  # Замінили 'contact' на 'contacts'
    )

    # Обробка фільтру за користувачем з GET-параметра
    selected_user_id_str = request.GET.get('responsible_user')
    selected_user_id = None
    if selected_user_id_str:
        try:
            selected_user_id = int(selected_user_id_str)
            companies_query = companies_query.filter(responsible_user_id=selected_user_id)
        except (ValueError, TypeError):
            # Якщо передано невалідне значення ID, ігноруємо фільтр
            selected_user_id = None # Скидаємо, щоб у шаблоні не вибралось нічого некоректного

    # Оптимізуємо запит та впорядковуємо
    companies_list = companies_query.select_related('responsible_user').order_by('name')

    context = {
        'companies': companies_list,
        'users_for_filter': users_for_filter,
        'selected_user_id': selected_user_id, # Передаємо ID для виділення у фільтрі
        'page_title': 'Компанії без активних завдань' # Заголовок сторінки
    }

    return render(request, 'sales_analytics/companies_needs_attention_list.html', context)
