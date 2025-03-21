from django.shortcuts import render, get_object_or_404, redirect
from .models import Room, Interaction, Contact, Vacancy, ContactLink, Task
from django.db.models import Max, Count, Q, F, Subquery, OuterRef, IntegerField
from main.models import Company
from django.core.paginator import Paginator
from django.db import models
from .forms import ContactForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CompanyForm
from django.core.management import call_command
import logging
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from django.utils import timezone
from datetime import timedelta, date
import datetime
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import login_required
from sales_analytics.models import ManagerActivity

logger = logging.getLogger(__name__)

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    interactions_qs = room.interactions.order_by('created_at')
    paginator = Paginator(interactions_qs, 20)

    # Якщо взагалі немає повідомлень => num_pages = 0
    if paginator.num_pages == 0:
        page_obj = None
    else:
        # Якщо є хоча б одна сторінка, беремо ОСТАННЮ (найновіші повідомлення знизу)
        last_page_number = paginator.num_pages
        page_obj = paginator.get_page(last_page_number)

    # Помітити всі непрочитані
    room.interactions.filter(is_read=False, sender='contact').update(is_read=True)

    # Список кімнат для користувача
    rooms_for_user = (
        request.user.rooms
        .annotate(
            latest_interaction=Max('interactions__created_at'),
            unread_count=Count(
                'interactions',
                filter=Q(interactions__is_read=False, interactions__sender='contact')
            )
        )
        .order_by('-latest_interaction')
    )

    return render(request, 'sales/chat_room.html', {
        'room_id': room_id,
        'room': room,
        'page_obj': page_obj,
        'rooms_for_user': rooms_for_user,
    })

@login_required
def chats_view(request):
    # Список кімнат для користувача
    rooms_for_user = (
        request.user.rooms
        .annotate(
            latest_interaction=Max('interactions__created_at'),
            unread_count=Count(
                'interactions',
                filter=Q(interactions__is_read=False, interactions__sender='contact')
            )
        )
        .order_by('-latest_interaction')
    )

    return render(request, 'sales/chat_room.html', {
        'rooms_for_user': rooms_for_user,
    })

@login_required
def load_more_interactions(request, room_id):
    """
    Повертає старіші повідомлення (HTML), щоб додати їх зверху у чаті.
    Наприклад, якщо поточна сторінка була 10,
    то при натисканні "Завантажити ще" можна піти на сторінку 9, 8 і т.д.
    """
    room = get_object_or_404(Room, pk=room_id)

    # Поточна сторінка, яку запитуємо, передається GET-параметром `page`.
    page_number = request.GET.get('page', 1)
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    interactions_qs = room.interactions.order_by('created_at')
    paginator = Paginator(interactions_qs, 20)
    page_obj = paginator.get_page(page_number)

    # Рендеримо шматок HTML із повідомленнями (з partial-шаблону)
    rendered_messages = render_to_string(
        'sales/partials/chat_messages.html',
        {'interactions': page_obj.object_list}
    )

    # Для зручності повертаємо, чи є попередня сторінка
    # (тому що ми рухаємось "назад" до старіших повідомлень).
    has_previous = page_obj.has_previous()
    prev_page_number = page_obj.previous_page_number() if has_previous else None

    data = {
        'messages_html': rendered_messages,
        'has_previous': has_previous,
        'prev_page_number': prev_page_number,
    }
    return JsonResponse(data)

@login_required
def company_list(request):
    # Підзапит для вакансій Work.ua
    work_vacancies_qs = Vacancy.objects.filter(
        work_company_id=OuterRef('work_id')
    ).values('work_company_id').annotate(cnt=Count('*')).values('cnt')

    # Підзапит для вакансій Robota.ua
    robota_vacancies_qs = Vacancy.objects.filter(
        robota_company_id=OuterRef('robota_id')
    ).values('robota_company_id').annotate(cnt=Count('*')).values('cnt')

    # Підзапит для вакансій Just
    just_vacancies_qs = Vacancy.objects.filter(
        just_id=OuterRef('just_id__id')
    ).values('just_id').annotate(cnt=Count('*')).values('cnt')

    companies = Company.objects.all().annotate(
        work_vacancies=Subquery(work_vacancies_qs, output_field=IntegerField()),
        robota_vacancies=Subquery(robota_vacancies_qs, output_field=IntegerField()),
        just_vacancies=Subquery(just_vacancies_qs, output_field=IntegerField()),
    )

    paginator = Paginator(companies, 12)  # 12 компаній на сторінку
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sales/company_list.html', {
        'companies': page_obj,
        'page_obj': page_obj,
    })


@login_required
def contact_list(request):
    contacts = Contact.objects.all().select_related('company')
    query = request.GET.get('q', '').strip()

    if query:
        contacts = contacts.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__name__icontains=query)
        )

    paginator = Paginator(contacts, 36)  # 36 контактів на сторінку
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Отримуємо поточного користувача
    current_user = request.user

    # Додаємо інформацію про наявність чату для кожного контакту
    contacts_with_chat_info = []
    for contact in page_obj:
        # Перевіряємо, чи існує Room для цього контакту і користувача
        room = Room.objects.filter(user=current_user, contact=contact).first()
        contact_data = {
            'id': contact.id,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'position': contact.position,
            'company': contact.company,
            'phone': contact.phone,
            'email': contact.email,
            'telegram_username': contact.telegram_username,
            'telegram_id': contact.telegram_id,
            'created_at': contact.created_at.strftime('%d.%m.%Y %H:%M'),  # Форматуємо дату
            'has_chat': bool(room),  # Чи є чат
            'room_id': room.id if room else None  # ID чату, якщо є
        }
        contacts_with_chat_info.append(contact_data)

    companies = Company.objects.all()

    return render(request, 'sales/contact_list.html', {
        'contacts': contacts_with_chat_info,  # Передаємо список із додатковою інформацією
        'page_obj': page_obj,
        'companies': companies,
    })

@login_required
def company_detail(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    contacts = Contact.objects.filter(company=company).order_by('created_at')
    current_user = request.user

    # Додаємо інформацію про чат для кожного контакту
    contacts_with_chat_info = []
    for contact in contacts:
        room = Room.objects.filter(user=current_user, contact=contact).first()
        contact_data = {
            'id': contact.id,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'position': contact.position,
            'phone': contact.phone,
            'email': contact.email,
            'telegram_username': contact.telegram_username,
            'telegram_id': contact.telegram_id,
            'created_at': contact.created_at,
            'has_chat': bool(room),
            'room_id': room.id if room else None
        }
        contacts_with_chat_info.append(contact_data)

    context = {
        'company': company,
        'contacts': contacts_with_chat_info,
    }
    return render(request, 'sales/company_detail.html', context)

@login_required
def create_chat_room(request, contact_id):
    contact = Contact.objects.get(id=contact_id)
    user = request.user

    # Перевіряємо, чи чат уже існує
    room = Room.objects.filter(user=user, contact=contact).first()
    if room:
        return redirect('chat_room', room_id=room.id)

    # Створюємо новий чат
    room = Room.objects.create(user=user, contact=contact)
    return redirect('chat_room', room_id=room.id)

@login_required
def get_company_vacancies(request, room_id):
    room = Room.objects.get(id=room_id)
    contact = room.contact
    company = contact.company

    if not company or not company.work_id:
        return JsonResponse({'success': True, 'vacancies': []})

    # Фільтруємо вакансії лише за work_company_id
    vacancies = Vacancy.objects.filter(
        work_company_id=company.work_id
    )[:10]  # Обмежуємо до 10 вакансій

    vacancies_data = [
        {
            'title': vacancy.title,
            'city': vacancy.city,
            'work_id': vacancy.work_id,
            'is_hot': vacancy.is_hot,
            'created_at': vacancy.created_at.strftime('%d.%m.%Y') if vacancy.created_at else None
        }
        for vacancy in vacancies
    ]

    return JsonResponse({'success': True, 'vacancies': vacancies_data})

def contact_search(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)

    # Фільтруємо контакти
    contacts = Contact.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query) |
        Q(company__name__icontains=query)
    ).select_related('company').prefetch_related('rooms').order_by('id')

    # Пагінація
    paginator = Paginator(contacts, 10)  # 10 контактів на сторінку
    page_obj = paginator.get_page(page)

    # Формуємо дані для JSON
    contacts_data = [
        {
            'id': contact.id,
            'first_name': contact.first_name,
            'last_name': contact.last_name or '',
            'position': contact.position or '',
            'phone': contact.phone or '',
            'email': contact.email or '',
            'telegram_username': contact.telegram_username or '',
            'telegram_id': contact.telegram_id or '',
            'company_name': contact.company.name if contact.company else '',
            'created_at': contact.created_at.strftime('%d.%m.%Y %H:%M'),
            'rooms': [{'id': room.id} for room in contact.rooms.all()]  # Додаємо пов’язані rooms
        }
        for contact in page_obj
    ]

    pagination_data = {
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'current_page': page_obj.number,
        'page_range': list(paginator.page_range),
        'has_other_pages': page_obj.has_other_pages()
    }

    return JsonResponse({
        'success': True,
        'contacts': contacts_data,
        'pagination': pagination_data
    })

@login_required
def create_contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            new_contact = form.save()

            # 1. Залежно від наявності компанії та її slug:
            if new_contact.company and new_contact.company.slug:
                company_part = new_contact.company.slug
            else:
                company_part = 'null'  # якщо компанії немає або її slug відсутній

            # 2. Формуємо URL:
            link_url = f"https://www.just-look.com.ua/?utm_company={company_part}_{new_contact.id}"

            # 3. Створюємо запис Link, прив’язаний до контакту
            ContactLink.objects.create(contact=new_contact, url=link_url)

            # 4. Створюємо чат (Room) із контактом
            room = Room.objects.create(
                user=request.user,  # Поточний авторизований користувач
                contact=new_contact,  # Новий контакт
            )

            ManagerActivity.objects.create(
                manager=request.user,
                activity_type='create_contact',
                contact=new_contact,  # Додаємо контакт

            )

            # Оновлюємо відповідь JSON із даними чату
            return JsonResponse({
                'success': True,
                'id': new_contact.id,
                'first_name': new_contact.first_name,
                'last_name': new_contact.last_name or '',
                'position': new_contact.position or '',
                'company_name': new_contact.company.name if new_contact.company else '',
                'phone': new_contact.phone or '',
                'email': new_contact.email or '',
                'telegram_username': new_contact.telegram_username or '',
                'telegram_id': new_contact.telegram_id or '',
                'room_id': room.id,  # ID створеного чату
                'room_url': f"/sales/{room.id}/"  # URL для переходу в чат (залежить від твоєї маршрутизації)
            })
        else:
            return JsonResponse({'success': False, 'error': form.errors.as_json()}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def edit_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    if request.method == "POST":
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()

            ManagerActivity.objects.create(
                manager=request.user,
                activity_type='edit_contact',
                contact=contact,  # Додаємо контакт

            )
            return JsonResponse({
                'success': True,
                'id': contact.id,
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'position': form.cleaned_data['position'],
                'company_name': form.cleaned_data['company'].name if form.cleaned_data['company'] else '',
                'phone': form.cleaned_data['phone'],
                'email': form.cleaned_data['email'],
                'telegram_username': form.cleaned_data['telegram_username'],
                'telegram_id': form.cleaned_data['telegram_id'],
            })
        else:
            return JsonResponse({'success': False, 'error': form.errors.as_json()}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            # Генеруємо slug (можна ще й зробити унікальність при потребі)
            company.slug = slugify(company.name)
            company.save()

            ManagerActivity.objects.create(
                manager=request.user,
                activity_type='create_company',
                company=company  # Додаємо компанію
            )
            return redirect('company_list')  # або ваша потрібна URL-назва
    else:
        form = CompanyForm()

    return render(request, 'sales/company_create.html', {'form': form})

@login_required
def edit_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            company = form.save(commit=False)
            company.slug = slugify(company.name)  # Оновлюємо slug при редагуванні
            company.save()

            ManagerActivity.objects.create(
                manager=request.user,
                activity_type='edit_company',
                company=company  # Додаємо компанію
            )
            return redirect('company_list')  # Перенаправляємо на список компаній
    else:
        form = CompanyForm(instance=company)

    return render(request, 'sales/company_edit.html', {'form': form, 'company': company})

@login_required
@csrf_exempt
@require_POST
def create_task(request):
    try:
        # Перевіряємо, чи є тіло запиту
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Тіло запиту порожнє'}, status=400)

        # Парсимо JSON-дані
        data = json.loads(request.body)

        # Отримуємо дані з запиту
        room_id = data.get('room_id')
        task_type = data.get('task_type')
        task_date_str = data.get('task_date')  # Отримуємо task_date як рядок
        target = data.get('target')
        description = data.get('description')

        # Перевірка обов’язкових полів
        if not all([room_id, task_type, task_date_str, target]):
            return JsonResponse({'success': False, 'error': 'Не всі обов’язкові поля заповнені'}, status=400)

        # Перевірка коректності task_type
        valid_task_types = [choice[0] for choice in Task.TASK_TYPE_CHOICES]
        if task_type not in valid_task_types:
            return JsonResponse({'success': False, 'error': 'Невірний тип задачі'}, status=400)

        # Отримуємо кімнату
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Кімната не знайдена'}, status=404)

        # Перевірка, чи користувач авторизований
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Користувач не авторизований'}, status=403)

        # Конвертуємо task_date із рядка в datetime
        task_date = parse_datetime(task_date_str)
        if task_date is None:
            return JsonResponse({'success': False, 'error': 'Невірний формат дати'}, status=400)

        # Створюємо задачу
        task = Task.objects.create(
            task_date=task_date,  # Передаємо об’єкт datetime
            contact=room.contact,
            user=request.user,
            task_type=task_type,
            target=target,
            description=description or '',
        )

        # Записуємо діяльність менеджера
        ManagerActivity.objects.create(
            manager=request.user,
            activity_type='create_task',
            contact=room.contact,
            task=task,
            company=room.contact.company if room.contact.company else None  # Додаємо компанію, якщо є
        )

        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'task_type': task.task_type,
            'target': task.target,
            'task_date': task.task_date.isoformat(),  # Тепер це точно datetime
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Невірний формат JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def kanban_board(request):
    # Отримуємо всі задачі для поточного користувача
    tasks = Task.objects.filter(user=request.user).order_by('task_date')

    # Поточна дата і час
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)  # Вчора
    tomorrow = today + timedelta(days=1)

    # Визначаємо початок і кінець тижня
    start_of_week = today - timedelta(days=today.weekday())  # Понеділок
    end_of_week = start_of_week + timedelta(days=6)  # Неділя

    # Розділяємо задачі за критеріями
    # Протерміновані: задачі, дата виконання яких була вчора або раніше
    overdue_tasks = tasks.filter(
        is_completed=False,
        task_date__date__lte=yesterday  # Задачі, які прострочені (до вчора включно)
    )

    # Сьогодні: задачі, які мають дату виконання сьогодні
    today_tasks = tasks.filter(
        is_completed=False,
        task_date__date=today
    )

    # Завтра: задачі, які мають дату виконання завтра
    tomorrow_tasks = tasks.filter(
        is_completed=False,
        task_date__date=tomorrow
    )

    # На цьому тижні: задачі, які мають дату виконання до кінця тижня, але не сьогодні і не завтра
    this_week_tasks = tasks.filter(
        is_completed=False,
        task_date__date__gt=tomorrow,
        task_date__date__lte=end_of_week
    )

    context = {
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'tomorrow_tasks': tomorrow_tasks,
        'this_week_tasks': this_week_tasks,
    }
    return render(request, 'sales/kanban.html', context)
@login_required
@csrf_exempt
@require_POST
def complete_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')

        task = Task.objects.get(id=task_id, user=request.user)
        task.is_completed = True
        task.completed_at = timezone.now()
        task.save()

        # Записуємо діяльність менеджера
        ManagerActivity.objects.create(
            manager=request.user,
            activity_type='complete_task',
            contact=task.contact,
            task=task,
            company=task.contact.company if task.contact.company else None  # Додаємо компанію, якщо є
        )

        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def get_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id, user=request.user)
        return JsonResponse({
            'success': True,
            'task_type': task.task_type,
            'task_date': task.task_date.isoformat(),
            'target': task.target,
            'description': task.description or '',
        })
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@csrf_exempt
@require_POST
def edit_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        task_type = data.get('task_type')
        task_date_str = data.get('task_date')
        target = data.get('target')
        description = data.get('description')

        if not all([task_type, task_date_str, target]):
            return JsonResponse({'success': False, 'error': 'Не всі обов’язкові поля заповнені'}, status=400)

        valid_task_types = [choice[0] for choice in Task.TASK_TYPE_CHOICES]
        if task_type not in valid_task_types:
            return JsonResponse({'success': False, 'error': 'Невірний тип задачі'}, status=400)

        task_date = parse_datetime(task_date_str)
        if task_date is None:
            return JsonResponse({'success': False, 'error': 'Невірний формат дати'}, status=400)

        task = Task.objects.get(id=task_id, user=request.user)
        task.task_type = task_type
        task.task_date = task_date
        task.target = target
        task.description = description or ''
        task.save()

        ManagerActivity.objects.create(
            manager=request.user,
            activity_type='edit_task',
            contact=task.contact,
            task=task,
            company=task.contact.company if task.contact.company else None  # Додаємо компанію, якщо є
        )

        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)