# services/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.throttling import AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.core.mail import send_mail
from django.conf import settings
from .models import Service, Category, ServiceZone, EligibilityApplication
from .serializers import ServiceSerializer, CategorySerializer, ServiceZoneSerializer, EligibilityApplicationSerializer
from rest_framework.permissions import SAFE_METHODS
from .utils import get_available_zones_for_postcode, geocode_postcode


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Public: GET list/retrieve
    Admin:  POST/PATCH/DELETE
    """
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Public: GET list/retrieve
    Admin:  POST/PATCH/DELETE
    """
    queryset = Service.objects.select_related('category').all().order_by("name")
    serializer_class = ServiceSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["active", "category"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "min_hourly_rate", "min_hours_required", "updated_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]


class ServiceZoneViewSet(viewsets.ModelViewSet):
    """
    Public: GET list/retrieve, check availability
    Admin:  POST/PATCH/DELETE
    """
    queryset = ServiceZone.objects.filter(is_active=True).order_by('name')
    serializer_class = ServiceZoneSerializer
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'radius_km', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        if self.action == 'check_availability':
            return [IsAuthenticated()]
        elif self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['post'], url_path='check-availability')
    def check_availability(self, request):
        """
        POST /api/services/zones/check-availability/
        Body: {"postcode": "M1 1AE"}
        
        Returns list of available service zones for the given postcode.
        Only returns leaf zones (most specific) - parent zones are excluded from selection.
        
        Frontend Usage:
        1. Cleaner enters their postcode during onboarding
        2. Call this endpoint to get available zones
        3. Display zones as checkboxes for selection
        4. Send selected zone IDs in cleaner profile update
        """
        postcode = request.data.get('postcode')
        
        if not postcode:
            return Response(
                {'error': 'Postcode is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        zones = get_available_zones_for_postcode(postcode)
        
        if zones is None:
            return Response(
                {'error': 'Invalid postcode or geocoding failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter to only show leaf zones (most specific)
        # If a cleaner is in Cambridge, they should select Cambridge, not Cambridgeshire or England
        leaf_zones = []
        for zone in zones:
            # Check if this zone has any children that are also in the available zones
            has_child_in_list = any(
                child in zones for child in zone.children.filter(is_active=True)
            )
            if not has_child_in_list:
                leaf_zones.append(zone)
        
        serializer = self.get_serializer(leaf_zones, many=True)
        return Response({
            'postcode': postcode,
            'available_zones': serializer.data,
            'count': len(serializer.data),
            'message': 'Select the zones where you can provide services. Only zones covering your location are shown.'
        })
    
    @action(detail=False, methods=['post'], url_path='check-location')
    def check_location(self, request):
        """
        POST /api/services/zones/check-location/
        Body: {"location": "Manchester"} or {"location": "Cambridge"} or {"postcode": "M1 1AE"}
        
        Smart location checker - geocodes ANY location and finds matching zones.
        Works hierarchically: If zone is "England", typing "Manchester" will match.
        
        Frontend Usage:
        1. Cleaner types ANY location (city, town, district, postcode)
        2. Call this endpoint
        3. Backend geocodes it and checks which zones contain it
        4. Returns available zones
        """
        location = request.data.get('location', '').strip()
        postcode = request.data.get('postcode', '').strip()
        
        if not location and not postcode:
            return Response(
                {'error': 'Either location or postcode is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try postcode first (most accurate)
        if postcode:
            coords = geocode_postcode(postcode)
            search_term = postcode
            location_data = None  # Postcodes don't have boundaries
        else:
            # Geocode the location name and get boundary
            location_data = self._geocode_with_boundary(location)
            if not location_data:
                return Response(
                    {
                        'error': f'Could not find location "{location}"',
                        'message': 'Please check spelling or try a different location'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            coords = (location_data['latitude'], location_data['longitude'])
            search_term = location
        
        latitude, longitude = coords
        
        # Find all zones that contain this point (validation only)
        matching_zones = []
        for zone in ServiceZone.objects.filter(is_active=True):
            if zone.contains_point(latitude, longitude):
                matching_zones.append(zone)
        
        if not matching_zones:
            return Response(
                {
                    'error': 'Location not in service area',
                    'message': f'"{search_term}" is outside all service zones. Admin needs to add coverage for this area.',
                    'coordinates': {'latitude': latitude, 'longitude': longitude}
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Filter to only show leaf zones (most specific)
        leaf_zones = []
        for zone in matching_zones:
            has_child_in_list = any(
                child in matching_zones for child in zone.children.filter(is_active=True)
            )
            if not has_child_in_list:
                leaf_zones.append(zone)
        
        # Prepare response
        result = {
            'location_name': search_term,
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'validation_zones': [{'id': z.id, 'name': z.name} for z in leaf_zones],
            'message': f'"{search_term}" is valid. You can offer services here.',
        }
        
        # If we have boundary data (city/town), include it for precise matching
        if location_data:
            result['area_data'] = {
                'name': location_data.get('display_name', search_term),
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'boundary_data': location_data.get('boundary_data'),
                'osm_type': location_data.get('osm_type'),
                'osm_id': location_data.get('osm_id'),
                'type': location_data.get('type', 'city')
            }
            result['instructions'] = {
                'save_this': {
                    'service_areas': [result['area_data']],
                    'service_zone_ids': [z.id for z in leaf_zones]
                },
                'display': f'Services offered in: {search_term}'
            }
        else:
            result['warning'] = 'Postcode entered - no specific area boundary. Consider entering city/town name for better employer matching.'
        
        return Response(result)
    
    def _geocode_with_boundary(self, location):
        """Geocode location and fetch its boundary from OpenStreetMap."""
        try:
            import requests
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'gb',
                'polygon_geojson': 1  # Request boundary data
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        'display_name': result.get('display_name'),
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'boundary_data': result.get('geojson'),
                        'osm_type': result.get('osm_type'),
                        'osm_id': result.get('osm_id'),
                        'type': result.get('type', 'city')
                    }
            return None
        except Exception as e:
            print(f"Geocoding error for '{location}': {e}")
            return None
    
    def _geocode_location_name(self, location):
        """Geocode a location name using OpenStreetMap Nominatim."""
        try:
            import requests
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                'q': location,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'gb'  # Restrict to UK
            }
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return (float(result['lat']), float(result['lon']))
            return None
        except Exception as e:
            print(f"Geocoding error for '{location}': {e}")
            return None
    
    def search_by_location(self, request):
        """
        GET /api/services/zones/search-by-location/?query=cambridge
        
        Search zones by location name for autocomplete.
        Returns only zones that match the search query.
        
        Frontend Usage:
        1. User types in search box (e.g., "camb")
        2. Call this endpoint with query parameter
        3. Display matching zones in dropdown
        4. User selects zone, you get the zone ID
        5. Use zone ID to filter cleaners or check availability
        """
        query = request.query_params.get('query', '').strip()
        
        if len(query) < 2:
            return Response({
                'results': [],
                'message': 'Please enter at least 2 characters'
            })
        
        # Search zones by name or description (case-insensitive)
        zones = ServiceZone.objects.filter(
            is_active=True,
            name__icontains=query
        ).order_by('name')[:10]  # Limit to 10 results
        
        serializer = self.get_serializer(zones, many=True)
        return Response({
            'query': query,
            'results': serializer.data,
            'count': len(serializer.data),
            'message': f'Showing zones matching "{query}". These are admin-defined zones only.'
        })
    
    @action(detail=True, methods=['get'], url_path='cleaners')
    def get_zone_cleaners(self, request, pk=None):
        """
        GET /api/services/zones/{id}/cleaners/
        
        Returns all cleaners in this zone including cleaners from child zones.
        Example: Querying England zone will include all Cambridgeshire cleaners.
        """
        zone = self.get_object()
        cleaners = zone.get_all_cleaners()
        
        # Import here to avoid circular dependency
        from users.serializers import CleanerListSerializer
        serializer = CleanerListSerializer(cleaners, many=True)
        
        return Response({
            'zone': zone.name,
            'direct_cleaners': zone.cleaners.count(),
            'total_cleaners': cleaners.count(),
            'cleaners': serializer.data
        })


class EligibilityApplicationViewSet(viewsets.ModelViewSet):
    """
    Public: POST (create application)
    Admin: GET list/retrieve/update/delete
    """
    queryset = EligibilityApplication.objects.all().order_by('-created_at')
    serializer_class = EligibilityApplicationSerializer
    permission_classes = [AllowAny]  # Allow anyone to submit
    throttle_classes = [AnonRateThrottle]  # Limit rate of requests

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

    def get_authenticators(self):
        """
        Disable authentication for create action to prevent 401 errors
        if invalid tokens are sent by mistake.
        """
        # Check if the request is a POST request (which corresponds to 'create')
        if self.request and self.request.method == 'POST':
            return []
        return super().get_authenticators()

    def create(self, request, *args, **kwargs):
        print("Received Eligibility Data:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        application = serializer.save()
        
        # Send email to admin
        try:
            subject = f"New Eligibility Application: {application.full_name}"
            message = f"""
            New application received from {application.full_name}.
            
            Email: {application.email}
            Phone: {application.phone}
            Postcode: {application.postcode}
            Criteria: {', '.join(application.eligibility_criteria)}
            
            Please review in admin panel.
            """
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to admin email (assuming same as FROM for now)
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send admin notification: {e}")
