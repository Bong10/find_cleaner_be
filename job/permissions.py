# job/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEmployer(BasePermission):
    """
    Allow only users that have a related Employer profile.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "employer"))


class IsJobOwnerOrReadOnly(BasePermission):
    """
    SAFE_METHODS allowed to anyone authenticated; write only to the job owner (employer).
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, "employer"):
            return False
        # obj is a Job instance
        return obj.employer_id == request.user.employer.id
