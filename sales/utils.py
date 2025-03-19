from django.template.loader import render_to_string

def render_email_template(user):
    context = {
        "manager_name": getattr(user.profile, "manager_name", user.username),
        "manager_email": getattr(user.profile, "manager_email", user.email),
        "manager_phone": getattr(user.profile, "manager_phone", "+380000000000"),
        "company_name": "Назва вашої компанії",
    }
    # Рендеримо HTML шаблон
    html_content = render_to_string("sales/email_template.html", context)
    return html_content
