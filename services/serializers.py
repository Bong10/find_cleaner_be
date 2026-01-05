from rest_framework import serializers
from django.conf import settings
import requests
from .models import Service, Category, ServiceZone, EligibilityApplication


class ServiceZoneSerializer(serializers.ModelSerializer):
    """Serializer for service zones with geographic data and hierarchy."""
    cleaners_count = serializers.SerializerMethodField(read_only=True)
    total_cleaners_count = serializers.SerializerMethodField(read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children_names = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ServiceZone
        fields = [
            'id', 'name', 'description',
            'center_latitude', 'center_longitude', 'radius_km',
            'boundary_data',
            'parent', 'parent_name', 'children_names',
            'is_active', 'cleaners_count', 'total_cleaners_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'cleaners_count', 'total_cleaners_count']
    
    def get_cleaners_count(self, obj):
        """Return number of verified cleaners directly in this zone."""
        return obj.cleaners.filter(is_verified_by_admin=True).count()
    
    def get_total_cleaners_count(self, obj):
        """Return total verified cleaners including child zones."""
        return obj.get_all_cleaners().filter(is_verified_by_admin=True).count()
    
    def get_children_names(self, obj):
        """Return list of child zone names."""
        return [child.name for child in obj.children.filter(is_active=True)]


class CategorySerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "description", "active", "created_at", "updated_at", "services_count"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_services_count(self, obj):
        return obj.services.count()


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "name", "description", "category", "category_name",
            "min_hourly_rate", "min_hours_required",
            "active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EligibilityApplicationSerializer(serializers.ModelSerializer):
    recaptcha_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = EligibilityApplication
        fields = [
            'id', 'full_name', 'email', 'phone', 'postcode',
            'contact_method', 'eligibility_criteria', 'status',
            'created_at', 'recaptcha_token'
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def validate_eligibility_criteria(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Criteria must be a list.")
        if len(value) > 20:  # Prevent massive lists
            raise serializers.ValidationError("Too many criteria selected.")
        for item in value:
            if not isinstance(item, str) or len(item) > 200:
                raise serializers.ValidationError("Invalid criteria format.")
        return value

    def validate(self, data):
        # 1. Verify reCAPTCHA (DISABLED FOR LOCAL DEVELOPMENT)
        token = data.pop('recaptcha_token', None)
        # if not token:
        #     # You can make this required=True if you want to enforce it strictly
        #     # raise serializers.ValidationError("reCAPTCHA token is missing.")
        #     pass 
        # else:
        #     try:
        #         response = requests.post(
        #             'https://www.google.com/recaptcha/api/siteverify',
        #             data={
        #                 'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        #                 'response': token
        #             }
        #         )
        #         result = response.json()
        #         if not result.get('success'):
        #             raise serializers.ValidationError("reCAPTCHA verification failed.")
        #     except Exception:
        #         raise serializers.ValidationError("Error verifying reCAPTCHA.")

        # 2. Check that either email or phone is provided.
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("You must provide either an email address or a phone number.")
        return data

