from django.contrib import admin
from .models import Task, Contact, Company  # Додаємо Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_type', 'target', 'contact', 'user', 'task_date', 'is_completed', 'completed_at')
    list_filter = ('task_type', 'is_completed', 'task_date')
    search_fields = ('target', 'description', 'contact__first_name', 'contact__last_name')
    date_hierarchy = 'task_date'
    ordering = ('-task_date',)

# Якщо у вас уже є інші моделі в admin.py, просто додайте цей код