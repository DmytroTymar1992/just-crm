from django.urls import path
from .views import visitor_map_dashboard

urlpatterns = [
    # ... ваші інші URL
    path('dashboard/', visitor_map_dashboard, name='site_dashboard'),
]