from django.contrib import admin
from .models import UserProfile, Company


@admin.register(UserProfile)
class StatusAdmin(admin.ModelAdmin):
    search_fields = ('user',)


@admin.register(Company)
class StatusAdmin(admin.ModelAdmin):
    search_fields = ('name',)
