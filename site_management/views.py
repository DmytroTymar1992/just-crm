from django.shortcuts import render
from data_exchange.models import Visitor
from django.db.models import Count
import plotly.express as px
import pandas as pd

def visitor_map_dashboard(request):
    # Отримуємо дані про відвідувачів із України
    visitors_by_region = (
        Visitor.objects
        .filter(country='Україна')
        .values('region')
        .annotate(count=Count('id'))
        .order_by('region')
    )

    # Перетворюємо в DataFrame для зручності
    data = pd.DataFrame(visitors_by_region)
    if data.empty:
        data = pd.DataFrame({'region': [], 'count': []})

    # Завантажуємо GeoJSON для карти України з регіонами
    # Ви можете знайти GeoJSON України з регіонами онлайн, наприклад, на GitHub
    # Приклад: https://github.com/vshymanskyy/Ukraine-geojson/blob/master/regions.geojson
    geojson_url = "https://raw.githubusercontent.com/EugeneBorshch/ukraine_geojson/master/UA_FULL_Ukraine.geojson"

    # Створюємо хороплет-карту з Plotly
    fig = px.choropleth(
        data,
        geojson=geojson_url,
        locations='region',  # Назва поля в даних, що відповідає регіонам
        featureidkey="properties.name:uk",  # Поле в GeoJSON, яке відповідає назві регіону українською
        color='count',  # Значення для забарвлення
        color_continuous_scale=['white', 'green'],  # Градієнт від білого до зеленого
        range_color=[0, data['count'].max() if not data.empty else 1],  # Діапазон значень
        title='Відвідувачі сайту за регіонами України',
        labels={'count': 'Кількість відвідувачів'},
    )

    # Налаштування карти
    fig.update_geos(
        fitbounds="locations",  # Автоматичне центрування на Україну
        visible=False,  # Прибираємо базову карту (залишаємо лише регіони)
    )
    fig.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},  # Компактні відступи
    )

    # Конвертуємо графік у HTML
    map_html = fig.to_html(full_html=False)

    # Передаємо HTML у шаблон
    return render(request, 'site_management/dashboard.html', {'map_html': map_html})