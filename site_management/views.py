from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
# from django.db.models.functions import TruncHour # Замінив .extra()
from django.db.models.functions import TruncHour, TruncDate # Додав TruncDate
import plotly.express as px
import pandas as pd
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

    # --- Дані для списку регіонів (залишаємо, бо потрібні для правої колонки) ---
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
        .values('region')
        .annotate(count=Count('id'))
        .order_by('region')
    )
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        # Якщо регіонів немає, створимо порожній DataFrame з потрібними колонками
        data = pd.DataFrame({'region': [], 'count': []})
        logger.warning("No visitors found for Ukraine between %s and %s", start_date, end_date)

    # --- Загальна кількість відвідувачів ---
    total_visitors = Visitor.objects.filter(
        country='Україна', is_bot=False, created_at__date__range=[start_date, end_date]
    ).count()

    # --- Дані для лінійного графіка ---
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
        if not time_data.empty: # Застосовувати .apply тільки якщо дані є
            time_data['hour'] = time_data['hour'].apply(lambda x: x.strftime('%Y-%m-%d %H:00'))
        x_label = 'hour'
        x_title = 'Година'
    else:
        # Використовуємо TruncDate замість .extra()
        visitors_by_time = (
            Visitor.objects
            .filter(country='Україна', is_bot=False, created_at__date__range=[start_date, end_date])
            .annotate(date=TruncDate('created_at')) # <-- Змінено
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        time_data = pd.DataFrame(visitors_by_time)
        if not time_data.empty: # Застосовувати .astype тільки якщо дані є
           time_data['date'] = time_data['date'].astype(str)
        x_label = 'date'
        x_title = 'Дата'

    logger.info("Visitors by region (for top list): %s", list(visitors_by_region))
    logger.info("Visitors by time: %s", list(visitors_by_time))

    # --- БЛОК КАРТИ ЗАКОМЕНТОВАНО ---
    # # Перетворюємо в DataFrame для карти - вже зроблено вище для top_regions
    # # data = pd.DataFrame(visitors_by_region)
    # # if data.empty:
    # #     logger.warning("No visitors found for Ukraine between %s and %s", start_date, end_date)
    # #     data = pd.DataFrame({'region': [], 'count': []})

    # # Завантажуємо GeoJSON із локального файлу
    # # if settings.DEBUG:
    # #     geojson_path = os.path.join(settings.BASE_DIR, 'site_management', 'static', 'site_management', 'ukraine_regions.geojson')
    # # else:
    # #     geojson_path = os.path.join(settings.STATIC_ROOT, 'site_management', 'ukraine_regions.geojson')

    # # try:
    # #     with open(geojson_path, 'r', encoding='utf-8') as f:
    # #         geojson_data = json.load(f)
    # # except FileNotFoundError:
    # #     logger.error(f"GeoJSON file not found at {geojson_path}")
    # #     geojson_data = {'features': []}
    # # except Exception as e: # Ловимо інші можливі помилки читання/парсингу
    # #      logger.error(f"Error loading or parsing GeoJSON file at {geojson_path}: {e}")
    # #      geojson_data = {'features': []}


    # # Отримуємо всі регіони з GeoJSON - Потрібно для доповнення нулями списку топ-регіонів
    # # all_regions = [feature['properties']['name:uk'] for feature in geojson_data.get('features', [])] # Використовуємо .get для безпеки

    # # --- Потрібно отримати список всіх регіонів для коректного Top-10, якщо немає GeoJSON ---
    # # # Якщо ми не можемо завантажити GeoJSON, нам потрібен альтернативний спосіб отримати
    # # # повний список регіонів, щоб доповнити дані нулями для коректного розрахунку max_count.
    # # # НАЙПРОСТІШЕ ЗАРАЗ: розрахуємо max_count тільки на основі наявних даних.
    # # # existing_regions = set(data['region'])
    # # # missing_regions = [r for r in all_regions if r not in existing_regions]
    # # # missing_data = pd.DataFrame({'region': missing_regions, 'count': [0] * len(missing_regions)})
    # # # data = pd.concat([data, missing_data], ignore_index=True)
    # # Залишаємо data як є (тільки з регіонами, де були візити) для розрахунку топ-10

    # --- Сортуємо для топ-10 і додаємо відсотки (використовуємо 'data' як є) ---
    max_count = data['count'].max() if not data.empty else 1
    top_10_data = data.sort_values(by='count', ascending=False).head(10)
    # Перевіряємо чи max_count не 0 перед діленням
    if max_count > 0:
        top_10_data['percentage'] = (top_10_data['count'] / max_count * 100).round(2)
    else:
         top_10_data['percentage'] = 0

    # --- Створення статичної карти ЗАКОМЕНТОВАНО ---
    # fig_map = px.choropleth(
    #     data,
    #     geojson=geojson_data,
    #     locations='region',
    #     featureidkey="properties.name:uk",
    #     color='count',
    #     color_continuous_scale=['white', 'green'],
    #     range_color=[0, max_count],
    # )
    # fig_map.update_geos(
    #     fitbounds="locations",
    #     visible=False,
    # )
    # fig_map.update_layout(
    #     margin={"r": 0, "t": 0, "l": 0, "b": 0},
    #     showlegend=False,
    #     dragmode=False,
    #     title=None,
    #     modebar_remove=['zoom', 'pan', 'select', 'lasso', 'zoomin', 'zoomout', 'reset'],
    #     hovermode=False,
    # )
    # fig_map.update_traces(
    #     marker_line_width=1,
    #     marker_line_color='gray',
    # )
    # map_html = fig_map.to_html(full_html=False, config={'staticPlot': True})
    map_html = "" # Порожній рядок замість HTML карти

    # --- Доповнюємо дані для лінійного графіка ---
    if time_data.empty:
        # Якщо даних взагалі немає, створимо одну точку на старті
        if x_label == 'date':
             placeholder_x = start_date.strftime('%Y-%m-%d')
        else: # 'hour'
             placeholder_x = datetime.combine(start_date, datetime.min.time()).strftime('%Y-%m-%d %H:00')
        time_data = pd.DataFrame({x_label: [placeholder_x], 'count': [0]})
    else:
        # Створюємо повний діапазон дат/годин для заповнення пропусків
        if x_label == 'date':
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
            all_times = pd.DataFrame({x_label: [d.strftime('%Y-%m-%d') for d in date_range]})
        else: # 'hour'
            hour_range = [datetime.combine(start_date, datetime.min.time()) + timedelta(hours=x) for x in range(24)]
            all_times = pd.DataFrame({x_label: [h.strftime('%Y-%m-%d %H:00') for h in hour_range]})
        # Об'єднуємо і заповнюємо нулями пропущені значення
        time_data = all_times.merge(time_data, on=x_label, how='left').fillna({'count': 0})
        # Перетворюємо count на цілі числа після fillna
        time_data['count'] = time_data['count'].astype(int)


    # --- Створюємо статичний лінійний графік ---
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

    # --- Контекст для шаблону ---
    context = {
        'map_html': map_html, # Передаємо порожній рядок
        'line_chart_html': line_chart_html,
        'top_regions': top_10_data.to_dict('records'),
        'max_count': int(max_count), # Переконуємося, що max_count - ціле число для шаблону
        'total_visitors': total_visitors,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    return render(request, 'site_management/dashboard.html', context)