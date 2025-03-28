#import os
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'just_crm.settings')
#import django
#django.setup()

#from channels.auth import AuthMiddlewareStack
#from channels.routing import ProtocolTypeRouter, URLRouter
#from django.core.asgi import get_asgi_application
#import sales.routing

#application = ProtocolTypeRouter({
#    "http": get_asgi_application(),
#    "websocket": AuthMiddlewareStack(
#         URLRouter(
#             sales.routing.websocket_urlpatterns
#         )
#    ),
#})


# just_crm/asgi.py
import os
import django # Імпортуємо сам django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'just_crm.settings')

# Необов'язково, але може допомогти: явний виклик django.setup()
# Спробуйте спочатку без цього рядка. Якщо помилка залишиться, розкоментуйте його.
# django.setup()

# Спочатку отримуємо стандартний ASGI додаток Django для HTTP
django_asgi_app = get_asgi_application()

# !!! ВАЖЛИВО: Імпортуємо роутінг та інші залежності Channels ПІСЛЯ get_asgi_application !!!
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import sales.routing
import transcription.routing # Імпортуємо маршрути нового додатка

application = ProtocolTypeRouter({
    # Тепер використовуємо змінну django_asgi_app
    "http": django_asgi_app,

    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                # Об'єднуємо списки маршрутів, як і раніше
                sales.routing.websocket_urlpatterns +
                transcription.routing.websocket_urlpatterns
            )
        )
    ),
})
