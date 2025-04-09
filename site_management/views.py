from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
# from django.db.models.functions import TruncHour # Більше не потрібен
# from django.db.models.functions import TruncDate # Більше не потрібен
# import plotly.express as px # Більше не потрібен
import pandas as pd
# from datetime import datetime, date, timedelta # datetime, date, timedelta - потрібні для дат
from datetime import datetime, date, timedelta
# import json # Більше не потрібен тут
# import os # Більше не потрібен тут
# from django.conf import settings # Більше не потрібен тут
import logging

logger = logging.getLogger(__name__)

def visitor_map_dashboard(request):
    # Отримуємо параметри дат з запиту
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

    # --- Дані для списку регіонів (залишаємо, бо потрібні для правої колонки) ---
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
        .values('region')
        .annotate(count=Count('id'))
        # .order_by('region') # Необов'язково, бо сортуємо далі за count
    )
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        data = pd.DataFrame({'region': [], 'count': []})
        logger.warning("No visitors found for Ukraine between %s and %s", start_date, end_date)

    # --- Загальна кількість відвідувачів ---
    total_visitors = Visitor.objects.filter(
        country='Україна', is_bot=False, created_at__date__range=[start_date, end_date]
    ).count()

    # --- Дані для лінійного графіка ЗАКОМЕНТОВАНО ---
    # if start_date == end_date:
    #     # ... запит по годинах ...
    #     # time_data = pd.DataFrame(visitors_by_time)
    #     # if not time_data.empty:
    #     #     time_data['hour'] = time_data['hour'].apply(lambda x: x.strftime('%Y-%m-%d %H:00'))
    #     x_label = 'hour'
    #     x_title = 'Година'
    # else:
    #     # ... запит по днях ...
    #     # time_data = pd.DataFrame(visitors_by_time)
    #     # if not time_data.empty:
    #     #    time_data['date'] = time_data['date'].astype(str)
    #     x_label = 'date'
    #     x_title = 'Дата'
    # logger.info("Visitors by region (for top list): %s", list(visitors_by_region))
    # # logger.info("Visitors by time: %s", list(visitors_by_time)) # Закоментовано, бо visitors_by_time немає

    # --- БЛОК КАРТИ ЗАКОМЕНТОВАНО ---
    # # ... код карти ...
    map_html = "" # Порожній рядок замість HTML карти

    # --- Сортуємо для топ-10 і додаємо відсотки (використовуємо 'data' як є) ---
    max_count = data['count'].max() if not data.empty else 1
    top_10_data = data.sort_values(by='count', ascending=False).head(10)
    if max_count > 0:
        top_10_data['percentage'] = (top_10_data['count'] / max_count * 100).round(2)
    else:
         top_10_data['percentage'] = 0

    # --- Доповнюємо дані для лінійного графіка ЗАКОМЕНТОВАНО ---
    # if time_data.empty:
    #     # ... обробка порожнього time_data ...
    # else:
    #     # ... обробка не порожнього time_data (merge, fillna) ...
    #     pass # Залишаємо pass або повністю коментуємо блок else

    # --- Створюємо статичний лінійний графік ЗАКОМЕНТОВАНО ---
    # fig_line = px.line(...)
    # fig_line.update_layout(...)
    # fig_line.update_traces(...)
    # line_chart_html = fig_line.to_html(full_html=False, config={'staticPlot': True})
    line_chart_html = "" # Порожній рядок замість HTML графіка

    # --- Контекст для шаблону ---
    context = {
        'map_html': map_html, # Передаємо порожній рядок
        'line_chart_html': line_chart_html, # Передаємо порожній рядок
        'top_regions': top_10_data.to_dict('records'),
        'max_count': int(max_count),
        'total_visitors': total_visitors,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    logger.info("Dashboard context prepared (charts excluded)")
    return render(request, 'site_management/dashboard.html', context)