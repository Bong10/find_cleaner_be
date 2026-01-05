# users/serializers.py  (FULL FILE SHOWN; existing code unchanged)
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Cleaner, Role, User, Admin, Employer, CleanerReference

User = get_user_model()

# 6) Djoser user.create is disabled in settings.
#    Keeping this class as-is to avoid breaking references.
class UserCreateSerializer(serializers.Serializer):
    def validate(self, attrs):
        raise serializers.ValidationError("Registration is disabled by the administrator.")

class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(read_only=True)  # Return role name
    role_id = serializers.PrimaryKeyRelatedField(
        source='role',
        queryset=Role.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone_number',
            'name',
            'gender',
            'profile_picture',
            'address',
            'password',
            'role',       # exposed as role name
            'role_id',    # used for input
            'profile_completed',
        ]
        # CHANGED: only email + password are required; everything else NOT required
        extra_kwargs = {
            'email': {'required': True},
            'password': {'write_only': True, 'required': True},

            'phone_number':    {'required': False, 'allow_null': True},
            'name':            {'required': False, 'allow_blank': True},
            'gender':          {'required': False, 'allow_blank': True},
            'address':         {'required': False, 'allow_blank': True},
            'profile_picture': {'required': False},
        }

    def to_representation(self, instance):
        # Handle AnonymousUser gracefully
        if not instance or not instance.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        return super().to_representation(instance)

    def get_role(self, obj):
        return obj.role.name if obj.role else None

    def create(self, validated_data):
        # create_user handles set_password
        user = User.objects.create_user(**validated_data)
        return user

class CleanerRegistrationSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Cleaner
        fields = [
            'user', 'portfolio', 'years_of_experience', 'dbs_check',
            'insurance_details', 'availability', 'clean_level', 'id'
        ]
        # CHANGED: all cleaner fields optional during registration
        extra_kwargs = {
            'portfolio': {'required': False, 'allow_blank': True, 'allow_null': True},
            'years_of_experience': {'required': False, 'allow_null': True},
            'dbs_check': {'required': False},
            'insurance_details': {'required': False, 'allow_blank': True, 'allow_null': True},
            'availability': {'required': False},
            'clean_level': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        role = Role.objects.filter(name__iexact="cleaner").first()  # guarded
        if not role:
            raise serializers.ValidationError("Role 'cleaner' is not configured.")
        user = User.objects.create_user(**user_data)
        user.role = role
        user.is_active = False  # keep current activation policy
        user.save()
        cleaner = Cleaner.objects.create(user=user, **validated_data)
        return cleaner

class EmployerRegistrationSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Employer
        fields = [
            'user', 'business_name', 'location', 'id',
            # New fields
            'bio', 'address_line1', 'address_line2', 'city', 'county', 'postcode',
            'property_type', 'bedrooms', 'bathrooms', 'toilets', 'kitchens', 'rooms',
            'parking_available', 'elevator_access', 'pets_in_property', 'access_instructions',
            'cleaning_frequency', 'preferred_time', 'cleaning_priorities',
            'special_requirements', 'cleaning_supplies'
        ]
        # CHANGED: employer optional fields
        extra_kwargs = {
            'business_name': {'required': False, 'allow_blank': True, 'allow_null': True},
            'location': {'required': False, 'allow_blank': True, 'allow_null': True},
            # All new fields are optional during registration
            'bio': {'required': False},
            'address_line1': {'required': False},
            'city': {'required': False},
            'postcode': {'required': False},
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        role = Role.objects.filter(name__iexact="employer").first()  # guarded
        if not role:
            raise serializers.ValidationError("Role 'employer' is not configured.")
        user = User.objects.create_user(**user_data)
        user.role = role
        user.is_active = False  # keep current activation policy
        user.save()
        employer = Employer.objects.create(user=user, **validated_data)
        return employer

class AdminRegistrationSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Admin
        fields = ['user', 'id']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        role = Role.objects.filter(name__iexact="admin").first()  # guarded
        if not role:
            raise serializers.ValidationError("Role 'admin' is not configured.")
        user = User.objects.create_user(**user_data)
        user.role = role
        # keep consistent policy: inactive until activation
        user.is_active = False
        user.save()
        admin = Admin.objects.create(user=user)
        return admin


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'user_count']
        extra_kwargs = {'name': {'required': True, 'allow_blank': False}}

    def get_user_count(self, obj):
        return obj.user_set.count() if hasattr(obj, 'user_set') else 0

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'email', 'name', 'address', 'gender', 'profile_picture', 'is_active']


# -------------------------------------------------------------------
# >>> ADDED: Employer serializers for admin CRUD & self-service
# -------------------------------------------------------------------

class EmployerDetailSerializer(serializers.ModelSerializer):
    """
    Read serializer: exposes employer with nested user fields via your existing UserSerializer.
    """
    from .serializers import UserSerializer as _UserSerializer  # avoid circular import on type checking
    user = _UserSerializer(read_only=True)

    class Meta:
        model = Employer
        fields = [
            "id", "business_name", "location", "user",
            # New fields
            'bio', 'address_line1', 'address_line2', 'city', 'county', 'postcode',
            'property_type', 'bedrooms', 'bathrooms', 'toilets', 'kitchens', 'rooms',
            'parking_available', 'elevator_access', 'pets_in_property', 'access_instructions',
            'cleaning_frequency', 'preferred_time', 'cleaning_priorities',
            'special_requirements', 'cleaning_supplies'
        ]


class EmployerUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer: restricts writable fields to employer-specific data only.
    User fields (email, name, etc.) remain managed by Djoser /auth/users/me/.
    """
    class Meta:
        model = Employer
        fields = [
            "business_name", "location",
            # New fields
            'bio', 'address_line1', 'address_line2', 'city', 'county', 'postcode',
            'property_type', 'bedrooms', 'bathrooms', 'toilets', 'kitchens', 'rooms',
            'parking_available', 'elevator_access', 'pets_in_property', 'access_instructions',
            'cleaning_frequency', 'preferred_time', 'cleaning_priorities',
            'special_requirements', 'cleaning_supplies'
        ]  # write-only subset for updates/creates


# -------------------------------------------------------------------
# >>> ADDED: Cleaner serializers for admin CRUD & self-service
# -------------------------------------------------------------------

class CleanerDetailSerializer(serializers.ModelSerializer):
    """
    Read serializer: exposes cleaner with nested user fields via your existing UserSerializer.
    """
    user = UserSerializer(read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.user.name', read_only=True, allow_null=True)
    services = serializers.SerializerMethodField(read_only=True)
    service_zones = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cleaner
        fields = [
            "id",
            "portfolio",
            "years_of_experience",
            "dbs_check",
            "insurance_details",
            "clean_level",
            "user",
            # Address fields
            "date_of_birth",
            "address_line1",
            "address_line2",
            "city",
            "county",
            "postcode",
            "country",
            # Service preferences
            "minimum_hours",
            "availability",
            "service_areas",  # Actual cities/towns with boundaries (for display & matching)
            "service_zones",  # Admin zones (validation only - not shown to users)
            "services",  # List of services offered
            # Verification documents
            "id_document_front",
            "id_document_back",
            "cv",
            "dbs_certificate_number",
            # Document verification status
            "id_verified",
            "dbs_verified",
            "references_verified",
            # Admin verification
            "is_verified_by_admin",
            "verified_at",
            "verified_by",
            "verified_by_name",
            # Reviews
            "average_rating",
            "total_reviews",
        ]
    
    def get_services(self, obj):
        """Return list of service IDs and names offered by this cleaner."""
        from job.models import CleanerService
        from services.serializers import ServiceSerializer
        
        cleaner_services = CleanerService.objects.filter(cleaner=obj).select_related('service')
        return ServiceSerializer([cs.service for cs in cleaner_services], many=True).data
    
    def get_service_zones(self, obj):
        """Return list of geographic zones where this cleaner operates."""
        from services.serializers import ServiceZoneSerializer
        return ServiceZoneSerializer(obj.service_zones.filter(is_active=True), many=True).data


class CleanerUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer: restricts writable fields to cleaner-specific data only.
    User fields (email, name, etc.) remain managed by Djoser /auth/users/me/.
    """
    service_zone_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of validation zone IDs (auto-populated from areas)"
    )
    
    service_areas = serializers.ListField(
        required=False,
        help_text="""List of service areas with boundaries. Each item: {
            'name': 'Manchester',
            'latitude': 53.48,
            'longitude': -2.24,
            'boundary_data': {...GeoJSON...},
            'osm_type': 'relation',
            'osm_id': '123456'
        }"""
    )
    
    class Meta:
        model = Cleaner
        fields = [
            "portfolio",
            "years_of_experience",
            "dbs_check",
            "insurance_details",
            "clean_level",
            # Address fields
            "date_of_birth",
            "address_line1",
            "address_line2",
            "city",
            "county",
            "postcode",
            "country",
            # Service preferences
            "minimum_hours",
            "availability",
            "service_areas",  # Cities/towns with boundaries
            "service_zone_ids",  # Optional validation zone IDs
            # Verification documents
            "id_document_front",
            "id_document_back",
            "cv",
            "dbs_certificate_number",
        ]
    
    def update(self, instance, validated_data):
        """Handle service areas and zone updates."""
        service_zone_ids = validated_data.pop('service_zone_ids', None)
        
        # Pre-process service_areas to ensure they are dicts (handle JSON strings from multipart forms)
        if 'service_areas' in validated_data:
            service_areas = validated_data['service_areas']
            import json
            
            # If service_areas is a string (JSON array), parse it
            if isinstance(service_areas, str):
                try:
                    service_areas = json.loads(service_areas)
                except (json.JSONDecodeError, TypeError):
                    service_areas = []
            
            # If it's a list, check if items are strings
            if isinstance(service_areas, list):
                parsed_areas = []
                for area in service_areas:
                    if isinstance(area, str):
                        try:
                            area = json.loads(area)
                        except (json.JSONDecodeError, TypeError):
                            continue
                    if isinstance(area, dict):
                        parsed_areas.append(area)
                validated_data['service_areas'] = parsed_areas

        service_areas = validated_data.get('service_areas', None)
        
        # Update all other fields (including service_areas with boundary data)
        instance = super().update(instance, validated_data)
        
        # Update validation zones
        if service_zone_ids is not None:
            # Case 1: Frontend explicitly sent zone IDs
            from services.models import ServiceZone
            zones = ServiceZone.objects.filter(id__in=service_zone_ids, is_active=True)
            instance.service_zones.set(zones)
            
        elif service_areas is not None:
            # Case 2: Frontend sent areas but no zone IDs - auto-calculate zones
            # This happens when cleaner adds "Manchester" - we must link them to "England" zone
            from services.models import ServiceZone
            
            # Get all active zones
            all_zones = ServiceZone.objects.filter(is_active=True)
            matched_zones = set()
            
            for area in service_areas:
                # Handle both latitude/longitude and lat/lng keys
                lat = area.get('latitude') or area.get('lat')
                lng = area.get('longitude') or area.get('lng')
                
                if lat is not None and lng is not None:
                    # Find all zones that contain this point
                    for zone in all_zones:
                        # 1. Geometric match (Primary)
                        if zone.contains_point(lat, lng):
                            matched_zones.add(zone)
                            continue
                            
                        # 2. Text-based match (Fallback)
                        # Useful when zone boundaries are imperfect (e.g. "Cambridgeshire" zone having only "Cambridge" city polygon)
                        address = area.get('address', {})
                        if not isinstance(address, dict):
                            continue
                            
                        # Fields to check against zone name
                        address_components = [
                            address.get('city'),
                            address.get('county'),
                            address.get('state'),
                            address.get('state_district'),
                            address.get('region')
                        ]
                        
                        # Check if zone name exactly matches any address component
                        # e.g. Zone "Cambridgeshire" matches address['county'] "Cambridgeshire"
                        if zone.name in [comp for comp in address_components if comp]:
                            matched_zones.add(zone)
            
            # If we found matching zones, update the relationship
            if matched_zones:
                instance.service_zones.set(matched_zones)
        
        return instance


class CleanerReferenceSerializer(serializers.ModelSerializer):
    """Serializer for professional and character references."""
    
    class Meta:
        model = CleanerReference
        fields = [
            "id",
            "reference_type",
            "name",
            "relationship",
            "email",
            "phone",
            "verified",
            "created_at",
        ]
        read_only_fields = ["id", "verified", "created_at"]
