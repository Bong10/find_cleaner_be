"""
Admin-only login view.
"""
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import permissions
from .admin_auth_serializers import AdminTokenObtainPairSerializer
from .views_jwt import set_refresh_cookie


class AdminTokenObtainPairView(TokenObtainPairView):
    """
    POST /auth/jwt/admin/create/
    
    Admin-only login endpoint.
    Only users with is_staff=True can authenticate.
    Regular users will be rejected with generic "Invalid login credentials" error.
    
    Returns: { access, user } and sets HttpOnly refresh_token cookie.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = AdminTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        data = response.data
        refresh = data.get("refresh")
        if refresh:
            set_refresh_cookie(response, refresh)
            # Do not expose the refresh token in JSON
            data.pop("refresh", None)
            response.data = data
        return response
