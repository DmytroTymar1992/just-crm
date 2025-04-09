from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
from django.db.models.functions import TruncHour, TruncDate
# import plotly.express as px # Не використовуємо Plotly
import pandas as pd
from datetime import datetime, date, timedelta
# import json
# import os
# from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def visitor_map_dashboard(request):
    # --- Отримання дат (без змін) ---
    start_date_str = request.GET.get('start_date', date.today().isoformat())
    end_date_str = request.GET.get('end_date', date.today().isoformat())
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = end_date = date.today()
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    logger.info("Processing dashboard for dates: %s to %s", start_date, end_date)

    # --- Дані для Топ-10 регіонів (без змін) ---
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
        .values('region')
        .annotate(count=Count('id'))
    )
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        data = pd.DataFrame({'region': [], 'count': []})
        logger.warning("No visitors found for Ukraine (regions) between %s and %s", start_date, end_date)
    max_count_region = data['count'].max() if not data.empty else 1
    top_10_data = data.sort_values(by='count', ascending=False).head(10)
    if max_count_region > 0:
        top_10_data['percentage'] = (top_10_data['count'] / max_count_region * 100).round(2)
    else:
        top_10_data['percentage'] = 0

    # --- Загальна кількість відвідувачів (без змін) ---
    total_visitors = Visitor.objects.filter(
        country='Україна', is_bot=False, created_at__date__range=[start_date, end_date]
    ).count()

    # --- Дані для Стовпчиків за часом (Розкоментовано і допрацьовано) ---
    if start_date == end_date:
        # Запит по годинах
        visitors_by_time = (
            Visitor.objects
            .filter(country='Україна', is_bot=False, created_at__date=start_date)
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        time_data = pd.DataFrame(visitors_by_time)
        # Створюємо мітку (label) і готуємо до заповнення пропусків
        if not time_data.empty:
            time_data['label'] = time_data['hour'].apply(lambda x: x.strftime('%H:00')) # Тільки година для мітки
            time_data['time_key'] = time_data['hour'].apply(lambda x: x.strftime('%Y-%m-%d %H:00')) # Повний ключ для merge
            time_data = time_data[['time_key', 'label', 'count']] # Вибираємо потрібні колонки
        else:
             time_data = pd.DataFrame({'time_key': [], 'label': [], 'count': []})

        # Створюємо повний діапазон годин для заповнення пропусків
        hour_range = [datetime.combine(start_date, datetime.min.time()) + timedelta(hours=x) for x in range(24)]
        all_times = pd.DataFrame({
            'time_key': [h.strftime('%Y-%m-%d %H:00') for h in hour_range],
            'label': [h.strftime('%H:00') for h in hour_range]
            })
        time_axis_label = "Година"

    else:
        # Запит по днях
        visitors_by_time = (
            Visitor.objects
            .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        time_data = pd.DataFrame(visitors_by_time)
        # Створюємо мітку (label) і готуємо до заповнення пропусків
        if not time_data.empty:
            time_data['label'] = time_data['date'].astype(str) # Дата як мітка
            time_data['time_key'] = time_data['date'].astype(str) # Ключ для merge - теж дата
            time_data = time_data[['time_key', 'label', 'count']] # Вибираємо потрібні колонки
        else:
            time_data = pd.DataFrame({'time_key': [], 'label': [], 'count': []})

        # Створюємо повний діапазон дат для заповнення пропусків
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        all_times = pd.DataFrame({
            'time_key': [d.strftime('%Y-%m-%d') for d in date_range],
            'label': [d.strftime('%Y-%m-%d') for d in date_range]
            })
        time_axis_label = "Дата"


    # Об'єднуємо з повним діапазоном і заповнюємо нулями пропущені значення
    processed_time_data = all_times.merge(time_data, on='time_key', how='left').fillna({'count': 0})
    # Видаляємо label_y, якщо він з'явився після merge, залишаємо label_x як основний
    if 'label_y' in processed_time_data.columns:
        processed_time_data = processed_time_data.rename(columns={'label_x': 'label'}).drop('label_y', axis=1)
    elif 'label_x' in processed_time_data.columns: # Якщо був тільки label_x
         processed_time_data = processed_time_data.rename(columns={'label_x': 'label'})

    processed_time_data['count'] = processed_time_data['count'].astype(int)

    # Розраховуємо висоту стовпчиків
    max_time_count = processed_time_data['count'].max() if not processed_time_data.empty else 1
    if max_time_count > 0:
        processed_time_data['height_percentage'] = (processed_time_data['count'] / max_time_count * 100).round(1)
    else:
        processed_time_data['height_percentage'] = 0

    # Готуємо фінальний список для шаблону
    timeline_bars_data = processed_time_data[['label', 'count', 'height_percentage']].to_dict('records')

    # --- Карта і Лінійний графік Plotly залишаються закоментованими ---
    map_html = ""
    line_chart_html = ""

    # --- Контекст для шаблону ---
    context = {
        'map_html': map_html,
        'line_chart_html': line_chart_html, # Залишаємо порожнім
        'top_regions': top_10_data.to_dict('records'),
        'max_count': int(max_count_region),
        'total_visitors': total_visitors,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'timeline_bars_data': timeline_bars_data, # Додаємо дані для стовпчиків
        'time_axis_label': time_axis_label, # Додаємо підпис осі часу
    }
    logger.info("Dashboard context prepared (HTML bars for timeline)")
    return render(request, 'site_management/dashboard.html', context)