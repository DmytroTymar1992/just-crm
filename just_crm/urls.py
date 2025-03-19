
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    #path('marketing/', include('marketing.urls')),
    #path('facebook_app/', include('facebook_app.urls')),
    path('sales/', include('sales.urls')),
    #path('chat/', include('chat.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
