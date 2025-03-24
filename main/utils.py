# sales/utils.py
import re

def normalize_phone_number(phone):
    """
    Приводить номер телефону до стандартного формату: +380XXXXXXXXX.
    Args:
        phone (str): Номер телефону в будь-якому форматі (наприклад, '+380688078320', '0688078320', '068-807-83-20').
    Returns:
        str: Нормалізований номер (наприклад, '+380688078320') або None, якщо номер некоректний.
    """
    if not phone:
        return None

    # Видаляємо всі нечислові символи
    phone = re.sub(r'[^0-9]', '', str(phone))

    # Перевіряємо довжину та формат
    if len(phone) < 9:  # Менше 9 цифр — некоректний номер
        return None

    # Обробка номера
    if phone.startswith('0'):
        # Якщо починається з 0, додаємо 38
        phone = '38' + phone
    elif phone.startswith('+'):
        # Якщо є +, видаляємо його (вже видалено re.sub, але для ясності)
        phone = phone.lstrip('+')
        if not phone.startswith('38'):
            phone = '38' + phone  # Додаємо 38, якщо його немає
    elif phone.startswith('380'):
        # Якщо вже є 380, залишаємо як є
        pass
    else:
        # Якщо номер не відповідає жодному формату, додаємо 38
        phone = '38' + phone

    # Перевіряємо, чи вийшов 12-значний номер
    if len(phone) == 12 and phone.startswith('380'):
        return f"+{phone}"  # Повертаємо номер із префіксом '+'
    return None

# Тестування
if __name__ == "__main__":
    test_numbers = [
        '+380688078320',  # з плюсом
        '0688078320',     # з 0
        '068-807-83-20',  # з дефісами
        '380688078320',   # без плюса
        '+0688078320',    # плюс і 0
        '068 807 83 20',  # з пробілами
        'abc123',         # некоректний
        '',               # порожній
    ]
    for num in test_numbers:
        result = normalize_phone_number(num)
        print(f"Input: {num} -> Output: {result}")