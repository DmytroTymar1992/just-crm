from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor
from .serializers import VisitorSerializer, ContactSerializer, SeekerSerializer
from sales.models import Contact, ContactLink
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

class VisitorCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            visitor = serializer.save()  # Зберігаємо відвідувача

            # Отримуємо first_url із запиту
            first_url = request.data.get('first_url', '')



            # Шукаємо збіги в ContactLink
            matching_link = ContactLink.objects.filter(url=first_url).first()
            if matching_link:
                # Оновлюємо відповідний контакт
                contact = matching_link.contact
                contact.has_visited_site = True
                contact.save()

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