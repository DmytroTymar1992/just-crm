from rest_framework import serializers
from .models import Visitor
from sales.models import Contact, Company
from site_management.models import Seeker

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ['visitor_id', 'ip_address', 'first_url', 'created_at', 'country', 'region', 'is_bot']
        read_only_fields = ['created_at']

class ContactSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source='company',
        write_only=True,
        required=False,  # Дозволяємо null
        allow_null=True  # Дозволяємо null
    )

    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'phone', 'email', 'company_id', 'is_from_site',
                  'is_processed', 'user_id', 'is_registered', 'has_visited_site', 'created_at']
        read_only_fields = ['created_at']

class SeekerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seeker
        fields = ['user_id', 'first_name', 'last_name', 'phone', 'email', 'created_at']
        read_only_fields = ['created_at']