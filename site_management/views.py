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

    # Нормалізація назв регіонів
    region_mapping = {
        'Київ': 'Kyiv',
        'Київська область': 'Kyivska',
        'Львівська область': 'Lvivska',
        'Черкаська область': 'Cherkaska',
        'Одеська область': 'Odeska',
        # Додайте інші регіони
    }
    data['region'] = data['region'].map(lambda x: region_mapping.get(x, x))

    # Завантажуємо GeoJSON
    geojson_url = "https://raw.githubusercontent.com/EugeneBorshch/ukraine_geojson/master/UA_FULL_Ukraine.geojson"
    geojson_data = requests.get(geojson_url).json()

    # Отримуємо всі регіони з GeoJSON
    all_regions = [feature['properties']['NAME_1'] for feature in geojson_data['features']]

    # Доповнюємо дані регіонами з 0 відвідувачів
    existing_regions = set(data['region'])
    missing_regions = [r for r in all_regions if r not in existing_regions]
    missing_data = pd.DataFrame({'region': missing_regions, 'count': [0] * len(missing_regions)})
    data = pd.concat([data, missing_data], ignore_index=True)

    # Створюємо хороплет-карту
    fig = px.choropleth(
        data,
        geojson=geojson_data,
        locations='region',
        featureidkey="properties.NAME_1",
        color='count',
        color_continuous_scale=['white', 'green'],
        range_color=[0, data['count'].max() if not data.empty else 1],
        title='Відвідувачі сайту за регіонами України',
        labels={'count': 'Кількість відвідувачів'},
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
    )
    fig.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
    )

    map_html = fig.to_html(full_html=False)
    return render(request, 'site_management/dashboard.html', {'map_html': map_html})