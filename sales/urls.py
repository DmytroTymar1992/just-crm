# chat/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('<int:room_id>/', chat_room, name='chat_room'),
    path('companies/', company_list, name='company_list'),
    path('contacts/', contact_list, name='contact_list'),
    path('contacts/create/', create_contact, name='create_contact'),
    path('contacts/edit/<int:contact_id>/', edit_contact, name='edit_contact'),
    path('company/create/', company_create, name='company_create'),

    path('<int:room_id>/load_more_interactions/', load_more_interactions, name='load_more_interactions'),
    path('create_task/', create_task, name='create_task'),
    path('kanban/', kanban_board, name='kanban_board'),  # Новий маршрут
    path('update_task_status/', complete_task, name='complete_task'),

]
