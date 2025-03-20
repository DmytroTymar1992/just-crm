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


logger = logging.getLogger(__name__)

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

def contact_list(request):
    contacts = Contact.objects.all().select_related('company')
    query = request.GET.get('q', '').strip()

    if query:
        contacts = contacts.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(phone__icontains=query) |
            models.Q(company__name__icontains=query)
        )

    paginator = Paginator(contacts, 36)  # 12 контактів на сторінку
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    companies = Company.objects.all()

    return render(request, 'sales/contact_list.html', {
        'contacts': page_obj,
        'page_obj': page_obj,
        'companies': companies,
    })


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
            })
        else:
            return JsonResponse({'success': False, 'error': form.errors.as_json()}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

def edit_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    if request.method == "POST":
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
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


def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            # Генеруємо slug (можна ще й зробити унікальність при потребі)
            company.slug = slugify(company.name)
            company.save()
            return redirect('company_list')  # або ваша потрібна URL-назва
    else:
        form = CompanyForm()

    return render(request, 'sales/company_create.html', {'form': form})


@csrf_exempt
@require_POST
def create_task(request):
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        task_type = data.get('task_type')
        task_date = data.get('task_date')
        subject = data.get('subject')
        description = data.get('description')

        # Отримуємо кімнату
        room = Room.objects.get(id=room_id)

        # Створюємо задачу
        task = Task.objects.create(
            task_date=task_date,
            contact=room.contact,
            user=request.user,
            task_type=task_type,
            subject=subject,
            description=description,
        )

        return JsonResponse({'success': True, 'task_id': task.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def kanban_board(request):
    # Отримуємо всі задачі для поточного користувача
    tasks = Task.objects.filter(user=request.user).order_by('task_date')

    # Поточна дата і час
    now = timezone.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    # Визначаємо початок і кінець тижня
    start_of_week = today - timedelta(days=today.weekday())  # Понеділок
    end_of_week = start_of_week + timedelta(days=6)  # Неділя

    # Розділяємо задачі за критеріями
    overdue_tasks = tasks.filter(
        is_completed=False,
        task_date__lt=now
    )

    today_tasks = tasks.filter(
        task_date__date=today,
        is_completed=False
    )

    tomorrow_tasks = tasks.filter(
        task_date__date=tomorrow,
        is_completed=False
    )

    this_week_tasks = tasks.filter(
        task_date__date__gt=tomorrow,
        task_date__date__lte=end_of_week,
        is_completed=False
    )

    context = {
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'tomorrow_tasks': tomorrow_tasks,
        'this_week_tasks': this_week_tasks,
    }
    return render(request, 'sales/kanban.html', context)

@csrf_exempt
@require_POST
def update_task_status(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_status = data.get('status')

        task = Task.objects.get(id=task_id, user=request.user)

        if new_status == 'new':
            task.is_completed = False
            task.completed_at = None
        elif new_status == 'in_progress':
            task.is_completed = False
            task.completed_at = timezone.now()
        elif new_status == 'completed':
            task.is_completed = True
            task.completed_at = timezone.now()

        task.save()
        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Задача не знайдена'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)