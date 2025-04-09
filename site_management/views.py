from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
import plotly.express as px
import pandas as pd
import requests
import logging

logger = logging.getLogger(__name__)

def visitor_map_dashboard(request):
    # Отримуємо дані про відвідувачів із України
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна')
        .values('region')
        .annotate(count=Count('id'))
        .order_by('region')
    )

    logger.info("Visitors by region: %s", list(visitors_by_region))

    # Перетворюємо в DataFrame
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        logger.warning("No visitors found for Ukraine.")
        data = pd.DataFrame({'region': [], 'count': []})

    # Завантажуємо GeoJSON
    geojson_url = "https://raw.githubusercontent.com/EugeneBorshch/ukraine_geojson/master/UA_FULL_Ukraine.geojson"
    geojson_data = requests.get(geojson_url).json()

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
    top_10_data['percentage'] = (top_10_data['count'] / max_count * 100).round(2)  # Обчислюємо відсотки

    # Створюємо статичну карту
    fig = px.choropleth(
        data,
        geojson=geojson_data,
        locations='region',
        featureidkey="properties.name:uk",
        color='count',
        color_continuous_scale=['white', 'green'],
        range_color=[0, max_count],
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
        dragmode=False,
        title=None,
    )

    fig.update_traces(
        marker_line_width=1,
        marker_line_color='gray',
    )
    fig.update_layout(
        modebar_remove=['zoom', 'pan', 'select', 'lasso', 'zoomin', 'zoomout', 'reset'],
        hovermode=False,
    )

    map_html = fig.to_html(full_html=False, config={'staticPlot': True})

    # Передаємо дані в шаблон
    context = {
        'map_html': map_html,
        'top_regions': top_10_data.to_dict('records'),  # Топ-10 регіонів із відсотками
        'max_count': max_count,
    }
    return render(request, 'site_management/dashboard.html', context)