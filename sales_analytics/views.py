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