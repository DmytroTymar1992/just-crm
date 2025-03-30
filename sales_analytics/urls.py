# crm_app/urls.py
from django.urls import path
from .views import  *


urlpatterns = [
    # ... ваші існуючі URL ...
    path('companies/needs-attention/', companies_needs_attention_list, name='companies_needs_attention_list'),
    # ... інші URL ...
]