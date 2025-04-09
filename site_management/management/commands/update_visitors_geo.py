from django.core.management.base import BaseCommand
from data_exchange.models import Visitor
from twoip import TwoIP
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update country, region, and is_bot fields for all existing visitors based on their IP addresses.'

    def get_geolocation(self, ip_address):
        try:
            twoip = TwoIP(key=None)  # Додайте key='ВАШ_КЛЮЧ', якщо є
            geo_data = twoip.geo(ip=ip_address)

            country = geo_data.get('country_ua', geo_data.get('country', '')).strip()
            region = geo_data.get('region_ua', geo_data.get('region', '')).strip() if country == 'Україна' else None
            is_bot = country != 'Україна'

            return country, region, is_bot
        except Exception as e:
            logger.error(f"Failed to get geolocation for IP {ip_address}: {e}")
            return None, None, True  # Якщо геодані не вдалося отримати, вважаємо ботом

    def handle(self, *args, **kwargs):
        # Отримуємо всіх відвідувачів, у яких не заповнені геодані або is_bot
        visitors = Visitor.objects.filter(country__isnull=True) | \
                   Visitor.objects.filter(region__isnull=True) | \
                   Visitor.objects.filter(is_bot__isnull=True)

        total = visitors.count()
        self.stdout.write(f"Found {total} visitors to update.")

        updated_count = 0
        for visitor in visitors:
            country, region, is_bot = self.get_geolocation(visitor.ip_address)

            # Оновлюємо тільки якщо отримали нові дані або потрібно змінити is_bot
            if country != visitor.country or region != visitor.region or is_bot != visitor.is_bot:
                visitor.country = country
                visitor.region = region
                visitor.is_bot = is_bot
                visitor.save()
                updated_count += 1
                self.stdout.write(
                    f"Updated visitor {visitor.visitor_id}: country={country}, region={region}, is_bot={is_bot}")
            else:
                self.stdout.write(f"No changes for visitor {visitor.visitor_id}")

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} out of {total} visitors."))