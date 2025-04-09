from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor
from .serializers import VisitorSerializer, ContactSerializer, SeekerSerializer
from sales.models import Contact, ContactLink, Room, Interaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from twoip import TwoIP


class VisitorCreateAPIView(APIView):
    def get_geolocation(self, ip_address):
        try:
            # Ініціалізація TwoIP (додайте key='ВАШ_КЛЮЧ', якщо є)
            twoip = TwoIP(key='16c5fd1380a1db89')
            geo_data = twoip.geo(ip=ip_address)

            # Отримуємо країну та регіон
            country = geo_data.get('country_ua', geo_data.get('country', '')).strip()
            region = geo_data.get('region_ua', geo_data.get('region', '')).strip() if country == 'Україна' else None

            # Визначаємо, чи бот: якщо не з України, то True
            is_bot = country != 'Україна'

            return country, region, is_bot
        except Exception as e:
            logger.error(f"Failed to get geolocation for IP {ip_address}: {e}")
            # Якщо геодані не вдалося отримати, повертаємо порожні країну та регіон, а is_bot = True
            return None, None, True

    def post(self, request, *args, **kwargs):
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            # Зберігаємо відвідувача спочатку без геолокації
            visitor = serializer.save()

            # Отримуємо геолокаційні дані за IP
            country, region, is_bot = self.get_geolocation(visitor.ip_address)

            # Оновлюємо модель відвідувача з отриманими даними
            visitor.country = country
            visitor.region = region
            visitor.is_bot = is_bot
            visitor.save()

            # Отримуємо first_url із запиту
            first_url = request.data.get('first_url', '')

            # Перетворюємо відносний URL на повний, якщо потрібно
            if first_url and not first_url.startswith(('http://', 'https://')):
                first_url = f"https://www.just-look.com.ua{first_url}"

            # Шукаємо збіги в ContactLink
            matching_link = ContactLink.objects.filter(url=first_url).first()
            if matching_link:
                # Оновлюємо відповідний контакт
                contact = matching_link.contact
                contact.has_visited_site = True
                contact.save()
                logger.info(f"Updated contact {contact.id}: has_visited_site=True")

                # Знаходимо всі чати (Room), де є цей контакт
                rooms = Room.objects.filter(contact=contact)
                for room in rooms:
                    # Створюємо системне повідомлення в кожному чаті
                    interaction = Interaction.objects.create(
                        room=room,
                        interaction_type='chat',
                        sender='system',
                        is_read=False
                    )
                    interaction.content = "Користувач відвідав сайт"
                    interaction.is_system = True
                    interaction.save()
                    logger.info(f"Sent system message to Room #{room.pk} for contact {contact.id}")

            # Повертаємо оновлені дані відвідувача
            serializer = VisitorSerializer(visitor)
            return Response({"message": "Visitor created successfully", "data": serializer.data},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


import logging
logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import ContactSerializer

@method_decorator([csrf_exempt, require_http_methods(["POST"])], name='dispatch')
class UserCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        logger.info(f"Received request: method={request.method}, data={request.data}")
        role = request.data.get('role')
        if role == 'employer':
            email = request.data.get('email')
            existing_contact = Contact.objects.filter(email=email).first()
            if existing_contact:
                existing_contact.user_id = request.data.get('user_id')
                existing_contact.is_from_site = False
                existing_contact.is_registered = True
                existing_contact.is_processed = True
                existing_contact.has_visited_site = True
                existing_contact.save()
                serializer = ContactSerializer(existing_contact)
                logger.info(f"Updated employer: {serializer.data}")
                return Response({"message": "Employer updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            else:
                data = {
                    'first_name': request.data.get('first_name'),
                    'last_name': request.data.get('last_name'),
                    'phone': request.data.get('phone'),
                    'email': email,
                    'user_id': request.data.get('user_id'),
                    'company_id': None,
                    'is_from_site': True,
                    'is_processed': False,
                    'is_registered': True,
                    'has_visited_site': True
                }
                serializer = ContactSerializer(data=data)
                if serializer.is_valid():
                    serializer.save()
                    logger.info(f"Created employer: {serializer.data}")
                    return Response({"message": "Employer created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
                logger.error(f"Validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        logger.warning(f"Invalid role: {role}")
        return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)