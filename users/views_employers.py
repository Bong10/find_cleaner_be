# users/views_employers.py
# >>> ADDED: New ViewSet to expose Employer admin CRUD and self-service "me" endpoints

from rest_framework import viewsets, permissions, decorators, response, status
from django.shortcuts import get_object_or_404

from .models import Employer
from .serializers import (
    # >>> uses serializers added below in users/serializers.py
    EmployerDetailSerializer,
    EmployerUpdateSerializer,
)


class EmployerViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD:
      - GET    /api/users/employers/           (list)     -> IsAdminUser
      - POST   /api/users/employers/           (create)   -> IsAdminUser
      - GET    /api/users/employers/{id}/      (retrieve) -> IsAdminUser
      - PUT    /api/users/employers/{id}/      (update)   -> IsAdminUser
      - PATCH  /api/users/employers/{id}/      (partial)  -> IsAdminUser
      - DELETE /api/users/employers/{id}/      (destroy)  -> IsAdminUser

    Self-service:
      - GET    /api/users/employers/me/        (read own employer profile)        -> IsAuthenticated
      - PATCH  /api/users/employers/me/        (update own business fields only)  -> IsAuthenticated
    """
    queryset = Employer.objects.select_related("user").all()
    # default serializer for safe methods
    serializer_class = EmployerDetailSerializer

    # >>> ADDED: Search/Ordering support (leverages your global DRF backends)
    search_fields = ["business_name", "location", "user__email", "user__name"]
    ordering_fields = ["id", "business_name", "location", "user__email"]
    ordering = ["id"]

    # >>> ADDED: Per-action permissions (admin for CRUD; auth for "me")
    def get_permissions(self):
        if self.action in ["me"]:
            return [permissions.IsAuthenticated()]
        # all standard CRUD endpoints are admin-only
        return [permissions.IsAdminUser()]

    # >>> ADDED: Use write serializer for write actions; read serializer otherwise
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return EmployerUpdateSerializer
        if self.action == "me" and self.request.method == "PATCH":
            return EmployerUpdateSerializer
        return EmployerDetailSerializer

    # >>> ADDED: Self endpoint
    @decorators.action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        employer = get_object_or_404(self.get_queryset(), user=request.user)

        if request.method.lower() == "get":
            return response.Response(EmployerDetailSerializer(employer).data)

        # PATCH: allow only employer's own allowed fields (serializer enforces this)
        serializer = EmployerUpdateSerializer(
            employer, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(EmployerDetailSerializer(employer).data, status=status.HTTP_200_OK)

    # >>> ADDED: Activate user endpoint
    @decorators.action(detail=True, methods=["post"], url_path="activate", permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        """POST /api/users/employers/{id}/activate/ - Activate employer's user account"""
        employer = self.get_object()
        employer.user.is_active = True
        employer.user.save()
        return response.Response(
            {"message": "User activated successfully.", "is_active": True},
            status=status.HTTP_200_OK
        )

    # >>> ADDED: Deactivate user endpoint
    @decorators.action(detail=True, methods=["post"], url_path="deactivate", permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        """POST /api/users/employers/{id}/deactivate/ - Deactivate employer's user account"""
        employer = self.get_object()
        employer.user.is_active = False
        employer.user.save()
        return response.Response(
            {"message": "User deactivated successfully.", "is_active": False},
            status=status.HTTP_200_OK
        )
