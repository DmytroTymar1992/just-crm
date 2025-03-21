# sales_analytics/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import ManagerActivity
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

    # Базовий queryset
    activities = ManagerActivity.objects.all()

    # Фільтр по менеджеру
    if manager_id != 'all' and manager_id:
        activities = activities.filter(manager_id=manager_id)

    # Фільтр по датах
    if date_from_str:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        activities = activities.filter(date__gte=date_from)
    if date_to_str:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)  # Включаємо весь день
        activities = activities.filter(date__lt=date_to)

    # Отримання всіх менеджерів для фільтра
    managers = User.objects.all()

    # Дані для діаграм
    total_companies = Company.objects.count()
    total_contacts = Contact.objects.count()

    if manager_id != 'all' and manager_id:
        manager = User.objects.get(id=manager_id)
        manager_created_companies = activities.filter(activity_type='create_company').count()
        manager_created_contacts = activities.filter(activity_type='create_contact').count()
    else:
        manager = None
        manager_created_companies = activities.filter(activity_type='create_company').aggregate(total=Count('id'))['total'] or 0
        manager_created_contacts = activities.filter(activity_type='create_contact').aggregate(total=Count('id'))['total'] or 0

    incoming_calls = activities.filter(activity_type='call_in').count()
    outgoing_calls = activities.filter(activity_type='call_out').count()

    # Дані для логу
    log_entries = activities.order_by('-date')[:50]  # Обмежуємо до 50 записів для відображення

    context = {
        'managers': managers,
        'selected_manager': manager_id,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'total_companies': total_companies,
        'manager_created_companies': manager_created_companies,
        'total_contacts': total_contacts,
        'manager_created_contacts': manager_created_contacts,
        'incoming_calls': incoming_calls,
        'outgoing_calls': outgoing_calls,
        'log_entries': log_entries,
    }
    return render(request, 'sales_analytics/analytics_dashboard.html', context)
