from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
from django.db.models.functions import TruncHour
import plotly.express as px
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os
from django.conf import settings
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

    # Фільтруємо відвідувачів за періодом для карти (не боти)
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
        .values('region')
        .annotate(count=Count('id'))
        .order_by('region')
    )

    # Загальна кількість відвідувачів (не ботів) за період
    total_visitors = Visitor.objects.filter(
        country='Україна', is_bot=False, created_at__date__range=[start_date, end_date]
    ).count()

    # Дані для графіка: по днях або по годинах, якщо один день
    if start_date == end_date:
        visitors_by_time = (
            Visitor.objects
            .filter(country='Україна', is_bot=False, created_at__date=start_date)
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        time_data = pd.DataFrame(visitors_by_time)
        time_data['hour'] = time_data['hour'].apply(lambda x: x.strftime('%Y-%m-%d %H:00'))
        x_label = 'hour'
        x_title = 'Година'
    else:
        visitors_by_time = (
            Visitor.objects
            .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
            .extra({'date': "date(created_at)"})
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        time_data = pd.DataFrame(visitors_by_time)
        time_data['date'] = time_data['date'].astype(str)
        x_label = 'date'
        x_title = 'Дата'

    logger.info("Visitors by region: %s", list(visitors_by_region))
    logger.info("Visitors by time: %s", list(visitors_by_time))

    # Перетворюємо в DataFrame для карти
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        logger.warning("No visitors found for Ukraine between %s and %s", start_date, end_date)
        data = pd.DataFrame({'region': [], 'count': []})

    # Завантажуємо GeoJSON із локального файлу
    geojson_path = os.path.join(settings.BASE_DIR, 'static', 'geojson', 'ukraine_regions.geojson')
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"GeoJSON file not found at {geojson_path}")
        geojson_data = {'features': []}  # Порожній GeoJSON у разі помилки

    # Отримуємо всі регіони з GeoJSON
    all_regions = [feature['properties']['name:uk'] for feature in geojson_data['features']]

    # Доповнюємо дані регіонами з 0 відвідувачів
    existing_regions = set(data['region'])
    missing_regions = [r for r in all_regions if r not in existing_regions]
    missing_data = pd.DataFrame({'region': missing_regions, 'count': [0] * len(missing_regions)})
    data = pd.concat([data, missing_data], ignore_index=True)

    # Сортуємо для топ-10 і додаємо відсотки
    max_count = data['count'].max() if not data.empty else 1
    top_10_data = data.sort_values(by='count', ascending=False).head(10)
    top_10_data['percentage'] = (top_10_data['count'] / max_count * 100).round(2)

    # Створюємо статичну карту
    fig_map = px.choropleth(
        data,
        geojson=geojson_data,
        locations='region',
        featureidkey="properties.name:uk",
        color='count',
        color_continuous_scale=['white', 'green'],
        range_color=[0, max_count],
    )
    fig_map.update_geos(
        fitbounds="locations",
        visible=False,
    )
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
        dragmode=False,
        title=None,
        modebar_remove=['zoom', 'pan', 'select', 'lasso', 'zoomin', 'zoomout', 'reset'],
        hovermode=False,
    )
    fig_map.update_traces(
        marker_line_width=1,
        marker_line_color='gray',
    )
    map_html = fig_map.to_html(full_html=False, config={'staticPlot': True})

    # Доповнюємо дані для графіка
    if time_data.empty:
        time_data = pd.DataFrame({x_label: [start_date.strftime('%Y-%m-%d')], 'count': [0]})
    else:
        if x_label == 'date':
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
            all_times = pd.DataFrame({x_label: [d.strftime('%Y-%m-%d') for d in date_range]})
        else:
            hour_range = [datetime.combine(start_date, datetime.min.time()) + timedelta(hours=x) for x in range(24)]
            all_times = pd.DataFrame({x_label: [h.strftime('%Y-%m-%d %H:00') for h in hour_range]})
        time_data = all_times.merge(time_data, on=x_label, how='left').fillna({'count': 0})

    # Створюємо статичний графік
    fig_line = px.line(
        time_data,
        x=x_label,
        y='count',
        title='Відвідувачі за період',
        labels={x_label: x_title, 'count': 'Кількість відвідувачів'},
    )
    fig_line.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        title_font_size=16,
        title_x=0.5,
        showlegend=False,
        modebar_remove=['zoom', 'pan', 'select', 'lasso', 'zoomin', 'zoomout', 'reset'],
        hovermode=False,
    )
    fig_line.update_traces(line_color='#00ff00')
    line_chart_html = fig_line.to_html(full_html=False, config={'staticPlot': True})

    # Контекст для шаблону
    context = {
        'map_html': map_html,
        'line_chart_html': line_chart_html,
        'top_regions': top_10_data.to_dict('records'),
        'max_count': max_count,
        'total_visitors': total_visitors,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    return render(request, 'site_management/dashboard.html', context)