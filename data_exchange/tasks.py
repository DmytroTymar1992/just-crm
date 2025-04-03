import requests
from celery import shared_task
from .models import Visitor


@shared_task
def fetch_visitors_data():
    site_url = "http://your-job-site.com/api/visitors/"

    try:
        response = requests.get(site_url, timeout=10)
        response.raise_for_status()
        visitors_data = response.json()

        for visitor in visitors_data:
            if not visitor.get('is_bot'):  # Фільтруємо ботів
                Visitor.objects.update_or_create(
                    visitor_id=visitor['visitor_id'],
                    defaults={
                        'ip_address': visitor['ip_address'],
                        'first_url': visitor['first_url'],
                    }
                )
    except requests.RequestException as e:
        print(f"Error fetching visitors: {e}")