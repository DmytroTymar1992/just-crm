import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from main.models import Company
from sales.models import Vacancy

class Command(BaseCommand):
    help = "Парсить всі вакансії з Work.ua (до max_pages сторінок)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--max_pages',
            type=int,
            default=4000,
            help='Максимальна кількість сторінок для парсингу (за замовчуванням 4000)'
        )

    def handle(self, *args, **options):
        max_pages = options['max_pages']
        total_parsed = 0

        for page in range(1, max_pages + 1):
            url = f"https://www.work.ua/jobs/?page={page}"
            self.stdout.write(f"Парсинг сторінки {page}: {url}")
            response = requests.get(url)
            time.sleep(1)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Не вдалося завантажити сторінку {page}"))
                break

            soup = BeautifulSoup(response.content, "html.parser")
            vacancy_links = soup.find_all("a", href=re.compile(r"^/jobs/\d+/"))
            if not vacancy_links:
                self.stdout.write(f"Сторінка {page} не містить вакансій. Завершуємо парсинг.")
                break

            parsed_in_page = 0
            for a_tag in vacancy_links:
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                match = re.search(r"/jobs/(\d+)/", href)
                if not match:
                    continue
                work_job_id = int(match.group(1))

                try:
                    vacancy = Vacancy.objects.get(work_id=work_job_id, placement="work")
                    time_tag = a_tag.find_next("time")
                    if time_tag and time_tag.has_attr("datetime"):
                        try:
                            parsed_date = datetime.datetime.strptime(time_tag["datetime"], "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            parsed_date = None
                    else:
                        parsed_date = None
                    if parsed_date and vacancy.created_at.date() != parsed_date.date():
                        vacancy.updated_at = parsed_date
                        vacancy.save()
                        self.stdout.write(f"Оновлено вакансію {work_job_id} (updated_at = {parsed_date})")
                        parsed_in_page += 1
                    else:
                        self.stdout.write(f"Вакансія {work_job_id} вже існує; пропускаємо")
                    continue
                except Vacancy.DoesNotExist:
                    pass

                # Визначаємо місто (правильний селектор)
                city = ""
                city_div = a_tag.find_next("div", class_=re.compile(r"mt-xs"))
                if city_div:
                    # Шукаємо span без класу "strong-600", який містить місто
                    city_span = city_div.find("span", class_=lambda x: x != "strong-600")
                    if city_span:
                        city = city_span.get_text(strip=True).strip(",").strip()
                    else:
                        # Якщо span не знайдено, беремо текст напряму після компанії
                        city_text = city_div.get_text(strip=True)
                        company_name = city_div.find("span", class_="strong-600").get_text(strip=True)
                        city = city_text.replace(company_name, "").strip(",").strip()

                # Перевірка на «гарячу» вакансію
                is_hot = False
                hot_el = a_tag.find_next(string=re.compile(r"Гаряча"))
                if hot_el:
                    is_hot = True

                # Отримуємо work_company_id з логотипу
                work_company_id = None
                vacancy_block = a_tag.find_parent("div", class_=re.compile(r"card"))
                if vacancy_block:
                    logo_img = vacancy_block.find("img", src=re.compile(r"_company_logo_"))
                    if logo_img and logo_img.has_attr("src"):
                        match_logo = re.search(r"/(\d+)_company_logo_", logo_img["src"])
                        if match_logo:
                            work_company_id = int(match_logo.group(1))

                if work_company_id is None:
                    self.stdout.write(f"Пропущено вакансію {work_job_id}: логотип відсутній")
                    continue

                now = datetime.datetime.now()
                if is_hot:
                    created_date = now
                    updated_date = now
                else:
                    time_tag = a_tag.find_next("time")
                    if time_tag and time_tag.has_attr("datetime"):
                        try:
                            created_date = datetime.datetime.strptime(time_tag["datetime"], "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            created_date = now
                    else:
                        created_date = now
                    updated_date = created_date

                vacancy = Vacancy.objects.create(
                    title=title,
                    created_at=created_date,
                    updated_at=updated_date,
                    company=None,
                    placement="work",
                    work_id=work_job_id,
                    work_company_id=work_company_id,
                    is_hot=is_hot,
                    city=city
                )
                self.stdout.write(f"Створено вакансію {work_job_id}: {title} (місто: {city})")
                parsed_in_page += 1

            self.stdout.write(self.style.SUCCESS(f"Сторінка {page}: Оброблено {parsed_in_page} вакансій"))
            total_parsed += parsed_in_page

        self.stdout.write(self.style.SUCCESS(f"Загалом оброблено {total_parsed} вакансій"))