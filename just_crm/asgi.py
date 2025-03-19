import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'just_crm.settings')
import django
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import sales.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
         URLRouter(
             sales.routing.websocket_urlpatterns
         )
    ),
})
