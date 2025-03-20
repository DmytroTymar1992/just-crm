from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    #path('api/received-social-posts/', ReceivedSocialPostCreateAPIView.as_view(), name='received-social-post-create'),
    #path('fetch_social_posts/', fetch_social_posts_view, name='fetch-social-posts'),
    path('login/', login_view, name='login'),  # Новий маршрут для логіна
    ]