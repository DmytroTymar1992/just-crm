from django.shortcuts import render, get_object_or_404, redirect
from .models import Room, Interaction, Contact, Vacancy, ContactLink, Task, TaskTransfer
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
from django.contrib import messages
from django.http import HttpResponse


logger = logging.getLogger(__name__)

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    interactions_qs = room.interactions.order_by('created_at')
    paginator = Paginator(interactions_qs, 20)
    contact = room.contact

    today = timezone.now().date()
    relevant_task = Task.objects.filter(
        user=request.user,  # Поточний користувач
        contact=contact,  # Контакт з поточної кімнати
        is_completed=False  # Тільки незавершені задачі
    ).order_by('task_date').first()  # Беремо найближчу за датою виконання

    task_info = {
        'task': None,
        'status_class': '',  # CSS клас для стилізації в шаблоні
    }

    if relevant_task:
        task_info['task'] = relevant_task
        # Перетворюємо дату/час задачі на просто дату для порівняння
        # Якщо task_date - це DateTimeField з підтримкою часових поясів (aware), краще конвертувати так:
        # task_date_only = relevant_task.task_date.astimezone(timezone.get_current_timezone()).date()
        # Якщо task_date - це DateTimeField без підтримки часових поясів (naive), то:
        task_date_only = relevant_task.task_date.date()

        if task_date_only < today:
            # Протермінована задача
            task_info['status_class'] = 'task-overdue'
        elif task_date_only == today:
            # Задача на сьогодні
            task_info['status_class'] = 'task-today'
        else:
            # Задача на майбутнє
            task_info['status_class'] = 'task-future'

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
        .order_by('-latest_interaction')[:25]
    )

    return render(request, 'sales/chat_room.html', {
        'room_id': room_id,
        'room': room,
        'page_obj': page_obj,
        'rooms_for_user': rooms_for_user,
        'task_info': task_info,
        'contact_links': room.contact.contactlink_set.all(),
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
        .order_by('-latest_interaction')[:25]
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
    unprocessed = request.GET.get('unprocessed') == 'on'

    if query:
        contacts = contacts.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__name__icontains=query)
        )

    if unprocessed:
        contacts = contacts.filter(is_processed=False)

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
        'unprocessed': unprocessed,
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

def search_contacts(request):
    query = request.GET.get("q", "").strip()
    if query:
        contacts = Contact.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(position__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(telegram_username__icontains=query) |
            Q(telegram_id__icontains=query) |
            Q(company__name__icontains=query)
        ).distinct()
    else:
        contacts = Contact.objects.all()

    # Рендеримо карточки через шаблон
    html = render_to_string('sales/partials/contacts_list_partial.html', {'contacts': contacts})
    return HttpResponse(html)

@login_required
def search_companies(request):
    query = request.GET.get("q", "").strip()
    if query:
        companies = Company.objects.filter(
            Q(name__icontains=query) |
            Q(work_id__icontains=query) |
            Q(robota_id__icontains=query)
        ).distinct()
    else:
        companies = Company.objects.all()

    paginator = Paginator(companies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    html = render_to_string('sales/partials/companies_list_partial.html', {
        'companies': page_obj,
        'page_obj': page_obj,
        'request': request  # Передаємо request для збереження параметрів у пагінації
    })
    return HttpResponse(html)

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
            print("Error: Тіло запиту порожнє")
            return JsonResponse({'success': False, 'error': 'Тіло запиту порожнє'}, status=400)

        # Парсимо JSON-дані
        data = json.loads(request.body)

        # Отримуємо дані з запиту
        contact_id = data.get('contact_id')
        task_type = data.get('task_type')
        task_date_str = data.get('task_date')  # Отримуємо task_date як рядок
        target = data.get('target')
        description = data.get('description')

        # Перевірка обов’язкових полів та збір відсутніх
        missing_fields = []
        if not contact_id:
            missing_fields.append("contact_id")
        if not task_type:
            missing_fields.append("task_type")
        if not task_date_str:
            missing_fields.append("task_date")
        if not target:
            missing_fields.append("target")
        if missing_fields:
            print("Missing fields in create_task:", missing_fields)
            return JsonResponse({'success': False, 'error': f'Не всі обов’язкові поля заповнені: {", ".join(missing_fields)}'}, status=400)

        # Перевірка коректності task_type
        valid_task_types = [choice[0] for choice in Task.TASK_TYPE_CHOICES]
        if task_type not in valid_task_types:
            print("Error: Невірний тип задачі", task_type)
            return JsonResponse({'success': False, 'error': 'Невірний тип задачі'}, status=400)

        # Отримуємо контакт
        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            print("Error: Контакт не знайдено, contact_id =", contact_id)
            return JsonResponse({'success': False, 'error': 'Контакт не знайдено'}, status=404)

        # Перевірка, чи користувач авторизований
        if not request.user.is_authenticated:
            print("Error: Користувач не авторизований")
            return JsonResponse({'success': False, 'error': 'Користувач не авторизований'}, status=403)

        # Конвертуємо task_date із рядка в datetime
        task_date = parse_datetime(task_date_str)
        if task_date is None:
            print("Error: Невірний формат дати", task_date_str)
            return JsonResponse({'success': False, 'error': 'Невірний формат дати'}, status=400)

        # Створюємо задачу
        task = Task.objects.create(
            task_date=task_date,  # Передаємо об’єкт datetime
            contact=contact,
            user=request.user,
            task_type=task_type,
            target=target,
            description=description or '',
        )

        # Записуємо діяльність менеджера
        ManagerActivity.objects.create(
            manager=request.user,
            activity_type='create_task',
            contact=contact,
            task=task,
            company=contact.company if contact.company else None
        )

        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'task_type': task.task_type,
            'target': task.target,
            'task_date': task.task_date.isoformat(),
        })
    except json.JSONDecodeError:
        print("Error: Невірний формат JSON")
        return JsonResponse({'success': False, 'error': 'Невірний формат JSON'}, status=400)
    except Exception as e:
        print("Exception in create_task:", str(e))
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


@csrf_exempt
@require_POST
def transfer_task(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_task_date = data.get('new_task_date')
        reason = data.get('reason')

        if not all([task_id, new_task_date, reason]):
            return JsonResponse({'success': False, 'error': 'Не всі обов’язкові поля заповнені'}, status=400)

        task = Task.objects.get(id=task_id, user=request.user)
        old_task_date = task.task_date

        # Логуємо вхідну дату для діагностики
        logger.info(f"Received new_task_date: {new_task_date}")

        # Спробуємо розпарсити дату
        try:
            new_task_date_parsed = parse_datetime(new_task_date)
        except ValueError as e:
            logger.error(f"Failed to parse date {new_task_date}: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Невірний формат дати'}, status=400)

        if new_task_date_parsed is None:
            return JsonResponse({'success': False, 'error': 'Невірний формат дати'}, status=400)

        task.task_date = new_task_date_parsed
        task.save()

        TaskTransfer.objects.create(
            task=task,
            reason=reason,
            from_date=old_task_date,
            to_date=new_task_date_parsed
        )

        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        logger.error(f"Error in transfer_task: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from main.models import Company

def merge_contacts_confirm_view(request, contact1_id, contact2_id):
    contact1 = get_object_or_404(Contact, id=contact1_id)
    contact2 = get_object_or_404(Contact, id=contact2_id)

    if request.method == "POST":
        print("POST data:", request.POST)
        keep_contact_id = request.POST.get("keep_contact")
        keep_self = str(contact1.id) == keep_contact_id

        primary = contact1 if keep_self else contact2
        secondary = contact2 if keep_self else contact1

        # Зберігаємо нові значення для всіх полів
        new_values = {
            'first_name': request.POST.get(f"contact{'1' if keep_self else '2'}_first_name", primary.first_name),
            'last_name': request.POST.get(f"contact{'1' if keep_self else '2'}_last_name", primary.last_name),
            'position': request.POST.get(f"contact{'1' if keep_self else '2'}_position", primary.position),
            'company': None,
            'phone': request.POST.get(f"contact{'1' if keep_self else '2'}_phone", primary.phone or secondary.phone),
            'email': request.POST.get(f"contact{'1' if keep_self else '2'}_email", primary.email or secondary.email),
            'telegram_username': request.POST.get(f"contact{'1' if keep_self else '2'}_telegram_username", primary.telegram_username or secondary.telegram_username),
            'telegram_id': None,
        }

        # Обробка company
        company_id = request.POST.get(f"contact{'1' if keep_self else '2'}_company")
        try:
            new_values['company'] = Company.objects.get(id=company_id) if company_id else primary.company
        except Company.DoesNotExist:
            print(f"Помилка: Компанії з ID {company_id} не існує")
            new_values['company'] = None

        # Обробка telegram_id
        telegram_id = request.POST.get(f"contact{'1' if keep_self else '2'}_telegram_id")
        try:
            new_values['telegram_id'] = int(telegram_id) if telegram_id and telegram_id.strip() else None
        except ValueError:
            print(f"Помилка: Некоректний Telegram ID: {telegram_id}")
            new_values['telegram_id'] = None

        # Визначаємо, які унікальні поля потрібно відкласти до видалення secondary
        unique_fields_to_update_later = {}
        for field in ['telegram_id', 'email', 'phone', 'telegram_username']:
            new_value = new_values[field]
            current_primary_value = getattr(primary, field)
            current_secondary_value = getattr(secondary, field)
            # Якщо нове значення є і відрізняється від primary, але збігається з secondary (для унікальних полів)
            if field == 'telegram_id' and new_value and new_value == current_secondary_value and new_value != current_primary_value:
                unique_fields_to_update_later[field] = new_value
                print(f"{field} ({new_value}) належить secondary, оновимо після видалення")
            # Для всіх інших полів (включаючи telegram_username), оновлюємо, якщо нове значення є
            elif new_value and new_value != current_primary_value:
                setattr(primary, field, new_value)
                print(f"Оновлюємо {field} одразу до {new_value}")

        # Оновлюємо неунікальні поля
        primary.first_name = new_values['first_name']
        primary.last_name = new_values['last_name']
        primary.position = new_values['position']
        primary.company = new_values['company']

        try:
            print(f"Зберігаємо primary контакт (тимчасово): {primary}")
            primary.save()

            # Обробка чатів
            all_rooms = Room.objects.filter(contact__in=[primary, secondary])
            print(f"Знайдено чатів: {all_rooms.count()}")
            if all_rooms.exists():
                primary_room = all_rooms.order_by('created_at').first()
                duplicate_rooms = all_rooms.exclude(id=primary_room.id)
                all_rooms.update(contact=primary)
                for dup_room in duplicate_rooms:
                    interactions_updated = Interaction.objects.filter(room=dup_room).update(room=primary_room)
                    print(f"Перенесено {interactions_updated} повідомлень з чату ID {dup_room.id} на чат ID {primary_room.id}")
                    dup_room.delete()
                    print(f"Видалено дубльований чат ID {dup_room.id}")

            print(f"Починаємо об'єднання: primary={primary}, secondary={secondary}")
            primary.merge_with(secondary)

            # Оновлюємо унікальні поля після видалення secondary
            for field, value in unique_fields_to_update_later.items():
                setattr(primary, field, value)
                print(f"Оновлюємо {field} primary до {value}")
            if unique_fields_to_update_later:
                primary.save()

            messages.success(request, f"Контакти успішно об'єднані в {primary}.")
            return redirect("contact_detail", contact_id=primary.id)
        except Exception as e:
            print(f"Помилка при об'єднанні контактів {contact1_id} і {contact2_id}: {str(e)}")
            messages.error(request, f"Помилка при об'єднанні: {str(e)}")
            return redirect("merge_contacts_confirm", contact1_id=contact1_id, contact2_id=contact2_id)

    return render(request, "sales/merge_contacts.html", {
        "contact1": contact1,
        "contact2": contact2,
        "other_contact": contact2 if contact1 else contact1,
    })


@login_required
def contact_detail_view(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    other_contacts = Contact.objects.exclude(id=contact_id)

    # Отримуємо всі чати для контакту
    rooms = Room.objects.filter(contact=contact).select_related('user').annotate(
        latest_interaction=Max('interactions__created_at'),
        unread_count=Count(
            'interactions',
            filter=Q(interactions__is_read=False, interactions__sender='contact')
        )
    ).order_by('-latest_interaction')

    # Отримуємо ID активного чату з GET-параметра або беремо перший чат
    selected_room_id = request.GET.get('room_id')
    selected_room = None
    interactions = []

    if rooms.exists():
        # Якщо room_id вказано і чат існує, вибираємо його
        if selected_room_id and rooms.filter(id=selected_room_id).exists():
            selected_room = rooms.get(id=selected_room_id)
        else:
            # Інакше вибираємо перший чат
            selected_room = rooms.first()

        # Отримуємо взаємодії для вибраного чату
        interactions = Interaction.objects.filter(room=selected_room).select_related(
            'room', 'call_message', 'telegram_message', 'email_message'
        ).order_by('created_at')

    return render(request, "sales/contact_detail.html", {
        "contact": contact,
        "other_contacts": other_contacts,
        "rooms": rooms,
        "selected_room": selected_room,
        "interactions": interactions,
    })



# your_app/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import datetime
from .models import CallMessage, Contact, Room, Interaction
from transcription.consumers import agent_audio_data

User = get_user_model()

class PhonetCallEventView(APIView):
    def post(self, request):
        allowed_ips = [
            "89.184.65.208", "89.184.82.130", "89.184.67.228",
            "89.184.82.191", "89.184.65.137", "95.213.132.131"
        ]
        client_ip = request.META.get("REMOTE_ADDR")
        if client_ip not in allowed_ips:
            agent_audio_data["system"] = {"logs": [{"event": "forbidden", "ip": client_ip, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]}
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        call_data = request.data
        event = call_data.get("event")
        uuid = call_data.get("uuid")

        current_time = datetime.datetime.now(datetime.timezone.utc)
        if "system" not in agent_audio_data:
            agent_audio_data["system"] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
        agent_audio_data["system"]["logs"].append({
            "event": "request_received",
            "data": call_data,
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
        })

        if not uuid:
            agent_audio_data["system"]["logs"].append({"event": "missing_uuid", "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")})
            return Response({"error": "Missing uuid"}, status=status.HTTP_400_BAD_REQUEST)

        if event not in ["call.dial", "call.bridge", "call.hangup"]:
            agent_audio_data["system"]["logs"].append({"event": "invalid_event", "value": event, "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")})
            return Response({"error": "Invalid event"}, status=status.HTTP_400_BAD_REQUEST)

        # Отримуємо користувача
        leg = call_data.get("leg", {})
        ext = leg.get("ext")
        agent_audio_data["system"]["logs"].append({"event": "processing_ext", "ext": ext, "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")})
        if ext:
            try:
                user = User.objects.get(profile__phonet_ext=ext)
                if not user.profile.phonet_enabled:
                    agent_audio_data[user.id] = {"logs": [{"event": "phonet_disabled", "ext": ext, "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")}]}
                    return Response({"error": "Phonet disabled for this user"}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                user = User.objects.get(id=1)
                if 1 not in agent_audio_data:
                    agent_audio_data[1] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
                agent_audio_data[1]["logs"].append({"event": "user_not_found", "ext": ext, "fallback_to": "id=1", "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")})
        else:
            user = User.objects.get(id=1)
            if 1 not in agent_audio_data:
                agent_audio_data[1] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
            agent_audio_data[1]["logs"].append({"event": "no_ext", "fallback_to": "id=1", "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")})

        client_phone = call_data.get("otherLegs", [{}])[0].get("num") or call_data.get("trunkNum")
        if not client_phone:
            agent_audio_data[user.id] = {"logs": [{"event": "no_client_phone", "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")}]}
            return Response({"error": "No client phone"}, status=status.HTTP_400_BAD_REQUEST)

        direction_code = call_data.get("lgDirection")
        sender = "contact" if direction_code == 4 else "user"

        # Логування перед транзакцією
        if user.id not in agent_audio_data:
            agent_audio_data[user.id] = {"logs": [], "audio_length": 0, "data": [], "received_at": ""}
        agent_audio_data[user.id]["logs"].append({
            "event": "processing_call",
            "user_id": user.id,
            "username": user.username,
            "ext": ext,
            "client_phone": client_phone,
            "direction": "incoming" if direction_code == 4 else "outgoing",
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
        })

        with transaction.atomic():
            contact, _ = Contact.objects.get_or_create(
                phone=client_phone,
                defaults={"first_name": client_phone}
            )
            room, _ = Room.objects.get_or_create(user=user, contact=contact)

            try:
                call_msg = CallMessage.objects.get(phonet_uuid=uuid)
                if event == "call.bridge":
                    call_msg.bridge_at = current_time
                elif event == "call.hangup":
                    call_msg.hangup_at = current_time
                call_msg.save()
            except CallMessage.DoesNotExist:
                interaction = Interaction.objects.create(
                    interaction_type="call",
                    room=room,
                    sender=sender,
                    is_read=False,
                )
                call_msg = CallMessage.objects.create(
                    interaction=interaction,
                    phonet_uuid=uuid,
                    parent_uuid=call_data.get("parentUuid-tour"),
                    direction=direction_code,
                    leg_id=leg.get("id"),
                    leg_ext=ext,
                    leg_name=leg.get("displayName"),
                    client_phone=client_phone,
                    dial_at=current_time if event == "call.dial" else None,
                    bridge_at=current_time if event == "call.bridge" else None,
                    hangup_at=current_time if event == "call.hangup" else None,
                )

            payload = {
                "msg_type": "call",
                "direction": "incoming" if direction_code == 4 else "outgoing",
                "event": event,
                "phone": client_phone,
                "uuid": uuid,
                "created_at": interaction.created_at.strftime("%H:%M") if interaction.created_at else current_time.strftime("%H:%M"),
                "dial_at": call_msg.dial_at.strftime("%H:%M:%S") if call_msg.dial_at else "",
                "bridge_at": call_msg.bridge_at.strftime("%H:%M:%S") if call_msg.bridge_at else "",
                "hangup_at": call_msg.hangup_at.strftime("%H:%M:%S") if call_msg.hangup_at else "",
            }

            channel_layer = get_channel_layer()
            room_group_name = f"sales_room_{room.id}"
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "chat_message",
                    "payload": payload,
                    "username": "Phonet",
                }
            )

            # Логування після збереження в базу
            agent_audio_data[user.id]["logs"].append({
                "event": event,
                "user_id": user.id,
                "username": user.username,
                "ext": ext,
                "client_phone": client_phone,
                "direction": "incoming" if direction_code == 4 else "outgoing",
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
            })

            # Відправка команд агенту
            agent_group_name = f"agent_{user.id}"
            if event == "call.bridge":
                command_details = {"uuid": uuid, "phone": client_phone}
                async_to_sync(channel_layer.group_send)(
                    agent_group_name,
                    {
                        "type": "agent_command",
                        "command": "start_streaming",
                        "details": command_details
                    }
                )
                agent_audio_data[user.id]["logs"].append({
                    "command": "start_streaming",
                    "group": agent_group_name,
                    "details": command_details,
                    "status": "sent",
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            elif event == "call.hangup":
                command_details = {"uuid": uuid}
                async_to_sync(channel_layer.group_send)(
                    agent_group_name,
                    {
                        "type": "agent_command",
                        "command": "stop_streaming",
                        "details": command_details
                    }
                )
                agent_audio_data[user.id]["logs"].append({
                    "command": "stop_streaming",
                    "group": agent_group_name,
                    "details": command_details,
                    "status": "sent",
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
                })

        # Логування успішного завершення
        agent_audio_data[user.id]["logs"].append({
            "event": "request_completed",
            "status": "success",
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
        })

        return Response({"status": "success"}, status=status.HTTP_200_OK)

from django.views.decorators.csrf import csrf_protect
@csrf_protect
def update_call_description(request, interaction_id):
    if request.method == 'POST':
        interaction = get_object_or_404(Interaction, id=interaction_id, interaction_type='call')
        data = json.loads(request.body)
        description = data.get('description', '')
        interaction.call_message.description = description
        interaction.call_message.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)