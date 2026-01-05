# users/views_jwt.py
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .auth_serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

import logging
logger = logging.getLogger(__name__)


def set_refresh_cookie(response, refresh_token: str):
    params = {
        "key": getattr(settings, "REFRESH_COOKIE_NAME", "refresh_token"),
        "value": refresh_token,
        "httponly": getattr(settings, "REFRESH_COOKIE_HTTPONLY", True),
        "secure": getattr(settings, "REFRESH_COOKIE_SECURE", False),  # dev: False (HTTP)
        "samesite": getattr(settings, "REFRESH_COOKIE_SAMESITE", "Lax"),
        "path": getattr(settings, "REFRESH_COOKIE_PATH", "/auth/jwt"),
    }
    # Align cookie lifetime with refresh lifetime
    refresh_lifetime = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")
    if refresh_lifetime:
        params["max_age"] = int(refresh_lifetime.total_seconds())
    response.set_cookie(**params)


def clear_refresh_cookie(response):
    response.delete_cookie(
        key=getattr(settings, "REFRESH_COOKIE_NAME", "refresh_token"),
        path=getattr(settings, "REFRESH_COOKIE_PATH", "/auth/jwt"),
        samesite=getattr(settings, "REFRESH_COOKIE_SAMESITE", "Lax"),
    )


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    POST /auth/jwt/create/
    Returns: { access } and sets HttpOnly refresh_token cookie.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer

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


class CookieTokenRefreshView(TokenRefreshView):
    """
    POST /auth/jwt/refresh/
    Reads refresh token from HttpOnly cookie and injects into serializer.
    Body can be {}.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        cookie_name = getattr(settings, "REFRESH_COOKIE_NAME", "refresh_token")
        cookie_refresh = request.COOKIES.get(cookie_name)

        logger.warning(
            "JWT refresh hit; Origin=%s; Cookie=%s",
            request.META.get("HTTP_ORIGIN"),
            request.META.get("HTTP_COOKIE"),
        )

        if cookie_refresh:
            # Inject cookie value into request.data for the parent view
            try:
                if hasattr(request.data, "mutable"):
                    request.data.mutable = True
                request.data["refresh"] = cookie_refresh
            except Exception:
                pass
        return super().post(request, *args, **kwargs)


class CookieLogoutView(APIView):
    """
    POST /auth/jwt/logout/
    Blacklists the refresh token if possible and clears the cookie.
    Does NOT require Authorization so you can always log out.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        cookie_name = getattr(settings, "REFRESH_COOKIE_NAME", "refresh_token")
        raw = request.COOKIES.get(cookie_name)

        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                # Token may be invalid/expired/untracked — ignore
                pass

        resp = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
        clear_refresh_cookie(resp)
        return resp
