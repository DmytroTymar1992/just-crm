# chat/urls.py
from django.urls import path
from .views import *
from sales_analytics.views import analytics_dashboard
from django.views.generic import TemplateView

urlpatterns = [
    path('<int:room_id>/', chat_room, name='chat_room'),
    path('companies/', company_list, name='company_list'),
    path('contacts/', contact_list, name='contact_list'),
    path('contacts/create/', create_contact, name='create_contact'),
    path('contacts/edit/<int:contact_id>/', edit_contact, name='edit_contact'),
    path('company/create/', company_create, name='company_create'),
    path('company/edit/<int:company_id>/', edit_company, name='edit_company'),

    path('<int:room_id>/load_more_interactions/', load_more_interactions, name='load_more_interactions'),
    path('create_task/', create_task, name='create_task'),
    path('kanban/', kanban_board, name='kanban_board'),  # Новий маршрут
    path('complete_task/', complete_task, name='complete_task'),
    path('get_task/<int:task_id>/', get_task, name='get_task'),
    path('edit_task/', edit_task, name='edit_task'),
    path('chats/', chats_view, name='chats'),
    path('contacts/search/', search_contacts, name='contact_search'),
    path('contacts/create_chat/<int:contact_id>/', create_chat_room, name='create_chat_room'),
    path('<int:room_id>/vacancies/', get_company_vacancies, name='get_company_vacancies'),

    path('dashboard/', analytics_dashboard, name='analytics_dashboard'),
    path('company/<int:company_id>/', company_detail, name='company_detail'),

    path("contacts/<int:contact_id>/", contact_detail_view, name="contact_detail"),
    path("contacts/merge_confirm/<int:contact1_id>/<int:contact2_id>/", merge_contacts_confirm_view,
         name="merge_contacts_confirm"),
    path('api/phonet/call-events/', PhonetCallEventView.as_view(), name='phonet-call-events'),






]
