# users/views_cleaners.py
# >>> UPDATED: Simple public access to list completed cleaner profiles

from rest_framework import viewsets, permissions, decorators, response, status
from django.shortcuts import get_object_or_404

from .models import Cleaner
from .serializers import (
    CleanerDetailSerializer,
    CleanerUpdateSerializer,
)


class CleanerViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD:
      - GET    /api/users/cleaners/           (list)     -> AllowAny (shows completed profiles only for non-admin)
      - POST   /api/users/cleaners/           (create)   -> IsAdminUser
      - GET    /api/users/cleaners/{id}/      (retrieve) -> IsAdminUser
      - PUT    /api/users/cleaners/{id}/      (update)   -> IsAdminUser
      - PATCH  /api/users/cleaners/{id}/      (partial)  -> IsAdminUser
      - DELETE /api/users/cleaners/{id}/      (destroy)  -> IsAdminUser

    Self-service:
      - GET    /api/users/cleaners/me/        (read own cleaner profile)        -> IsAuthenticated
      - PATCH  /api/users/cleaners/me/        (update own cleaner fields only)  -> IsAuthenticated
    """
    queryset = Cleaner.objects.select_related("user").all()
    serializer_class = CleanerDetailSerializer

    # >>> ADDED: Search/Ordering support (reuses your global DRF backends)
    search_fields = ["portfolio", "insurance_details", "user__email", "user__name"]
    ordering_fields = ["id", "years_of_experience", "clean_level", "user__email"]
    ordering = ["id"]

    # >>> UPDATED: Allow public access only for list action and search
    def get_permissions(self):
        if self.action in ["list", "search_by_location"]:
            return [permissions.AllowAny()]
        if self.action in ["me"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    # >>> ADDED: Use write serializer for write actions; read serializer otherwise
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CleanerUpdateSerializer
        if self.action == "me" and self.request.method == "PATCH":
            return CleanerUpdateSerializer
        return CleanerDetailSerializer

    # >>> UPDATED: Override get_queryset to filter based on user permissions
    def get_queryset(self):
        """
        - Admin users: see all cleaners
        - Everyone else: only see verified cleaners with completed profiles
        """
        queryset = super().get_queryset()
        
        # If user is admin, show everything
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        
        # For everyone else (public, non-admin authenticated), only show verified and active cleaners
        return queryset.filter(
            user__profile_completed=True,
            user__is_active=True,
            is_verified_by_admin=True  # Only show admin-verified cleaners
        )

    # >>> ADDED: Self endpoint
    @decorators.action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        # NOTE: Do not use get_queryset() here; it filters out non-completed profiles
        # for non-admin users. The current user should always be able to access
        # their own cleaner record for GET/PATCH regardless of public filters.
        cleaner = get_object_or_404(Cleaner.objects.select_related("user"), user=request.user)

        if request.method.lower() == "get":
            return response.Response(CleanerDetailSerializer(cleaner).data)

        # Auto-reset verification status to "pending" if rejected documents are resubmitted
        verification_updates = {}
        
        # Debug: Log what fields are in the request
        print(f"[DEBUG] PATCH request fields: {list(request.data.keys())}")
        
        # Check if ID documents were resubmitted and were previously rejected
        if ('id_document_front' in request.data or 'id_document_back' in request.data):
            if cleaner.id_verified == 'rejected':
                verification_updates['id_verified'] = 'pending'
                print(f"[DEBUG] Resetting id_verified: rejected -> pending")
        
        # Check if DBS certificate number was updated and was previously rejected
        if 'dbs_certificate_number' in request.data:
            if cleaner.dbs_verified == 'rejected':
                verification_updates['dbs_verified'] = 'pending'
                print(f"[DEBUG] Resetting dbs_verified: rejected -> pending")
        
        # Check if references were resubmitted and were previously rejected
        # Frontend can send references as an array OR as individual fields
        reference_fields = [
            'references',
            'professional_ref_name', 'professional_ref_email', 'professional_ref_phone', 'professional_ref_relationship',
            'character_ref_name', 'character_ref_email', 'character_ref_phone', 'character_ref_relationship'
        ]
        references_submitted = any(field in request.data for field in reference_fields)
        
        if references_submitted:
            print(f"[DEBUG] References found in request data. Current status: {cleaner.references_verified}")
            if cleaner.references_verified == 'rejected':
                verification_updates['references_verified'] = 'pending'
                print(f"[DEBUG] Resetting references_verified: rejected -> pending")
        else:
            print(f"[DEBUG] No reference fields in request data")
        
        # Apply verification status updates
        if verification_updates:
            for field, value in verification_updates.items():
                setattr(cleaner, field, value)
            cleaner.save(update_fields=list(verification_updates.keys()))
            print(f"[DEBUG] Saved verification updates: {verification_updates}")

        # PATCH: update only cleaner-allowed fields (serializer enforces this)
        ser = CleanerUpdateSerializer(cleaner, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        updated_cleaner = ser.save()
        
        # Handle service_types array if provided
        if 'service_types' in request.data:
            from job.models import CleanerService
            from services.models import Service
            import json
            
            service_ids = request.data.get('service_types', [])
            
            # Parse if it's a JSON string (from FormData)
            if isinstance(service_ids, str):
                try:
                    service_ids = json.loads(service_ids)
                except (json.JSONDecodeError, ValueError):
                    service_ids = []
            
            # Ensure it's a list
            if not isinstance(service_ids, list):
                service_ids = []
            
            # Clear existing services
            CleanerService.objects.filter(cleaner=cleaner).delete()
            # Add new services
            for service_id in service_ids:
                try:
                    service = Service.objects.get(id=service_id)
                    CleanerService.objects.create(cleaner=cleaner, service=service)
                except (Service.DoesNotExist, ValueError, TypeError):
                    pass  # Skip invalid service IDs
        
        # Handle references if provided
        if 'references' in request.data:
            from .models import CleanerReference
            from .serializers import CleanerReferenceSerializer
            import json
            
            references_data = request.data.get('references', [])
            
            # Parse if it's a JSON string (from FormData)
            if isinstance(references_data, str):
                try:
                    references_data = json.loads(references_data)
                except (json.JSONDecodeError, ValueError):
                    references_data = []
            
            # Ensure it's a list
            if not isinstance(references_data, list):
                references_data = []
            
            # Clear existing references
            CleanerReference.objects.filter(cleaner=cleaner).delete()
            # Add new references
            for ref_data in references_data:
                ref_data['cleaner'] = cleaner.id
                ref_serializer = CleanerReferenceSerializer(data=ref_data)
                if ref_serializer.is_valid():
                    ref_serializer.save(cleaner=cleaner)
        
        # Handle individual reference fields (alternative format from frontend)
        elif any(field in request.data for field in ['professional_ref_name', 'character_ref_name']):
            from .models import CleanerReference
            
            # Clear existing references
            CleanerReference.objects.filter(cleaner=cleaner).delete()
            
            # Create professional reference if provided
            if 'professional_ref_name' in request.data:
                professional_ref = {
                    'reference_type': 'professional',
                    'name': request.data.get('professional_ref_name', ''),
                    'email': request.data.get('professional_ref_email', ''),
                    'phone': request.data.get('professional_ref_phone', ''),
                    'relationship': request.data.get('professional_ref_relationship', ''),
                }
                if professional_ref['name'] and professional_ref['email']:
                    CleanerReference.objects.create(cleaner=cleaner, **professional_ref)
            
            # Create character reference if provided
            if 'character_ref_name' in request.data:
                character_ref = {
                    'reference_type': 'character',
                    'name': request.data.get('character_ref_name', ''),
                    'email': request.data.get('character_ref_email', ''),
                    'phone': request.data.get('character_ref_phone', ''),
                    'relationship': request.data.get('character_ref_relationship', ''),
                }
                if character_ref['name'] and character_ref['email']:
                    CleanerReference.objects.create(cleaner=cleaner, **character_ref)
        
        # Refresh cleaner from DB to ensure we have latest data
        cleaner.refresh_from_db()
        
        # Debug: Log final verification status being returned
        print(f"[DEBUG] Final response - references_verified: {cleaner.references_verified}")
        
        return response.Response(CleanerDetailSerializer(cleaner).data, status=status.HTTP_200_OK)

    # >>> ADDED: Activate user endpoint
    @decorators.action(detail=True, methods=["post"], url_path="activate", permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        """POST /api/users/cleaners/{id}/activate/ - Activate cleaner's user account"""
        cleaner = self.get_object()
        cleaner.user.is_active = True
        cleaner.user.save()
        return response.Response(
            {"message": "User activated successfully.", "is_active": True},
            status=status.HTTP_200_OK
        )

    # >>> ADDED: Deactivate user endpoint
    @decorators.action(detail=True, methods=["post"], url_path="deactivate", permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        """POST /api/users/cleaners/{id}/deactivate/ - Deactivate cleaner's user account"""
        cleaner = self.get_object()
        cleaner.user.is_active = False
        cleaner.user.save()
        return response.Response(
            {"message": "User deactivated successfully.", "is_active": False},
            status=status.HTTP_200_OK
        )
    
    # >>> ADDED: Search cleaners by location (postcode or city)
    @decorators.action(detail=False, methods=["post"], url_path="search-by-location")
    def search_by_location(self, request):
        """
        POST /api/users/cleaners/search-by-location/
        Body: {"postcode": "M1 1AE"} or {"location": "Manchester"}
        
        Returns verified cleaners who cover the specified location.
        """
        from services.utils import geocode_postcode
        
        postcode = request.data.get('postcode', '').strip()
        location = request.data.get('location', '').strip()
        
        if not postcode and not location:
            return response.Response(
                {'error': 'Either postcode or location is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Geocode the input
        if postcode:
            coords = geocode_postcode(postcode)
            search_term = postcode
        else:
            # Geocode location name
            coords = self._geocode_location(location)
            search_term = location
        
        if not coords:
            return response.Response(
                {
                    'error': f'Could not find location "{search_term}"',
                    'message': 'Please check spelling or try a different location'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        latitude, longitude = coords
        
        # Find all verified cleaners who cover this location
        matching_cleaners = []
        cleaners = Cleaner.objects.filter(
            user__is_active=True,
            user__profile_completed=True,
            is_verified_by_admin=True
        ).select_related('user')
        
        for cleaner in cleaners:
            if cleaner.covers_location(latitude, longitude):
                matching_cleaners.append(cleaner)
        
        if not matching_cleaners:
            return response.Response(
                {
                    'message': f'No cleaners found covering "{search_term}"',
                    'count': 0,
                    'cleaners': []
                },
                status=status.HTTP_200_OK
            )
        
        serializer = CleanerDetailSerializer(matching_cleaners, many=True)
        return response.Response({
            'location': search_term,
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'count': len(matching_cleaners),
            'cleaners': serializer.data
        })
    
    def _geocode_location(self, location):
        """Geocode a location name using OpenStreetMap Nominatim."""
        try:
            import requests
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'gb'
            }
            resp = requests.get(url, params=params, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    result = data[0]
                    return (float(result['lat']), float(result['lon']))
            return None
        except Exception as e:
            print(f"Geocoding error for '{location}': {e}")
            return None