from django.core.management.base import BaseCommand
from data_exchange.models import Visitor
from twoip import TwoIP
import logging
import time  # Додаємо для затримки між запитами

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update country, region, and is_bot fields for all visitors based on their IP addresses.'

    def get_geolocation(self, ip_address):
        try:
            twoip = TwoIP(key='16c5fd1380a1db89')  # Ваш ключ
            geo_data = twoip.geo(ip=ip_address)
            logger.info(f"Geo data for IP {ip_address}: {geo_data}")  # Логуємо сирі дані від API

            country = geo_data.get('country_ua', geo_data.get('country', '')).strip()
            region = geo_data.get('region_ua', geo_data.get('region', '')).strip() if country == 'Україна' else None
            is_bot = country != 'Україна'

            return country, region, is_bot
        except Exception as e:
            logger.error(f"Failed to get geolocation for IP {ip_address}: {e}")
            return None, None, True  # Якщо геодані не вдалося отримати, вважаємо ботом

    def handle(self, *args, **kwargs):
        # Отримуємо всіх відвідувачів без фільтра
        visitors = Visitor.objects.all()

        total = visitors.count()
        self.stdout.write(f"Found {total} visitors to update.")

        updated_count = 0
        for visitor in visitors:
            country, region, is_bot = self.get_geolocation(visitor.ip_address)

            # Оновлюємо завжди, щоб перезаписати попередні значення
            visitor.country = country
            visitor.region = region
            visitor.is_bot = is_bot
            visitor.save()
            updated_count += 1
            self.stdout.write(
                f"Updated visitor {visitor.visitor_id}: country={country}, region={region}, is_bot={is_bot}"
            )
            time.sleep(1)  # Затримка 1 секунда між запитами, щоб уникнути блокування API

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} out of {total} visitors."))