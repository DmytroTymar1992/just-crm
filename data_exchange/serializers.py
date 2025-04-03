from rest_framework import serializers
from .models import Visitor

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ['visitor_id', 'ip_address', 'first_url', 'created_at']
        read_only_fields = ['created_at']  # created_at встановлюється автоматично