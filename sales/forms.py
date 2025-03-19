# sales/forms.py
from django import forms
from .models import Contact, Company
from django.core.exceptions import ValidationError

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'position', 'company', 'phone', 'email', 'telegram_username', 'telegram_id']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telegram_username': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_id': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            existing_contact = Contact.objects.exclude(id=self.instance.id).filter(phone=phone).first()
            if existing_contact:
                raise ValidationError(f"Цей номер телефону вже використовується контактом: {existing_contact.first_name} {existing_contact.last_name or ''}")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            existing_contact = Contact.objects.exclude(id=self.instance.id).filter(email=email).first()
            if existing_contact:
                raise ValidationError(f"Цей email вже використовується контактом: {existing_contact.first_name} {existing_contact.last_name or ''}")
        return email

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get('telegram_username')
        if telegram_username:
            existing_contact = Contact.objects.exclude(id=self.instance.id).filter(telegram_username=telegram_username).first()
            if existing_contact:
                raise ValidationError(f"Цей Telegram username вже використовується контактом: {existing_contact.first_name} {existing_contact.last_name or ''}")
        return telegram_username

    def clean_telegram_id(self):
        telegram_id = self.cleaned_data.get('telegram_id')
        if telegram_id:
            existing_contact = Contact.objects.exclude(id=self.instance.id).filter(telegram_id=telegram_id).first()
            if existing_contact:
                raise ValidationError(f"Цей Telegram ID вже використовується контактом: {existing_contact.first_name} {existing_contact.last_name or ''}")
        return telegram_id


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'work_id', 'robota_id', 'responsible', 'just_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'work_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'robota_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'responsible': forms.Select(attrs={'class': 'form-control'}),
            'just_id': forms.Select(attrs={'class': 'form-control'}),
        }