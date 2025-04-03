from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor
from .serializers import VisitorSerializer, ContactSerializer, SeekerSerializer
from sales.models import Contact, ContactLink
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class VisitorCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            visitor = serializer.save()  # Зберігаємо відвідувача

            # Отримуємо first_url із запиту
            first_url = request.data.get('first_url', '')

            # Додаємо префікс для порівняння
            full_url = f"https://www.just-look.com.ua{first_url}"

            # Шукаємо збіги в ContactLink
            matching_link = ContactLink.objects.filter(url=full_url).first()
            if matching_link:
                # Оновлюємо відповідний контакт
                contact = matching_link.contact
                contact.has_visited_site = True
                contact.save()

            return Response({"message": "Visitor created successfully", "data": serializer.data},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class UserCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        role = request.data.get('role')
        if role == 'employer':
            # Перевіряємо, чи є контакт із таким email
            email = request.data.get('email')
            existing_contact = Contact.objects.filter(email=email).first()

            if existing_contact:
                # Оновлюємо існуючий контакт
                existing_contact.user_id = request.data.get('user_id')
                existing_contact.is_from_site = False  # Залишаємо False, бо контакт уже був у CRM
                existing_contact.is_registered = True  # Встановлюємо True
                existing_contact.is_processed = True  # Залишаємо True (за замовчуванням)
                existing_contact.has_visited_site = True  # Оновлюємо, бо прийшов із сайту
                existing_contact.save()
                serializer = ContactSerializer(existing_contact)
                return Response({"message": "Employer updated successfully", "data": serializer.data},
                                status=status.HTTP_200_OK)
            else:
                # Створюємо новий контакт
                data = {
                    'first_name': request.data.get('first_name'),
                    'last_name': request.data.get('last_name'),
                    'phone': request.data.get('phone'),
                    'email': email,
                    'user_id': request.data.get('user_id'),
                    'company_id': None,  # Додайте, якщо передаватимете компанію
                    'is_from_site': True,  # Новий контакт із сайту
                    'is_processed': False,  # Новий контакт не оброблений
                    'is_registered': True,  # Новий контакт із сайту зареєстрований
                    'has_visited_site': True  # Прийшов із сайту
                }
                serializer = ContactSerializer(data=data)

        elif role == 'seeker':
            # Для пошуковців створюємо Seeker
            data = {
                'user_id': request.data.get('user_id'),
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'phone': request.data.get('phone'),
                'email': request.data.get('email')
            }
            serializer = SeekerSerializer(data=data)
        else:
            return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"{role.capitalize()} created successfully", "data": serializer.data},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)