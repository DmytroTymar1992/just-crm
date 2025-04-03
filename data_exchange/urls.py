from django.urls import path
from .views import VisitorCreateAPIView, UserCreateAPIView

urlpatterns = [
    path('api/visitors/', VisitorCreateAPIView.as_view(), name='visitor-create'),
    path('api/users/', UserCreateAPIView.as_view(), name='visitor-create'),
]