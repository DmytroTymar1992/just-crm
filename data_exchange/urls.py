from django.urls import path
from .views import VisitorCreateAPIView

urlpatterns = [
    path('api/visitors/', VisitorCreateAPIView.as_view(), name='visitor-create'),
]