import os
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import EmailMultiAlternatives
from email.mime.base import MIMEBase
from email import encoders
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

from .serializers import (
    CleanerRegistrationSerializer,
    EmployerRegistrationSerializer,
    AdminRegistrationSerializer,
    RoleSerializer,
    UserSerializer,
)
from .models import Role

# Reuse cookie helper from your login flow
try:
    from .views_jwt import set_refresh_cookie  # sets HttpOnly refresh cookie
    HAVE_COOKIE_HELPER = True
except Exception:
    HAVE_COOKIE_HELPER = False

from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def _build_activation_url(request, user):
    """Secure, time-limited token; supports frontend or backend activation URL."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    use_frontend = getattr(settings, "ACTIVATE_VIA_FRONTEND", False)
    if use_frontend:
        origin = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:3000")
        path = getattr(settings, "FRONTEND_ACTIVATE_PATH", "/confirmation-account")
        return f"{origin.rstrip('/')}{path}/{uid}/{token}"
    else:
        path = reverse("activate-user", args=[uid, token])
        return request.build_absolute_uri(path)


def _send_activation_email(user, token_url):
    """
    Send HTML email with inline logo; uses {{ display_name }} & {{ token_url }}.
    Uses user.name field for greeting.
    """
    # Use user's name field directly
    display_name = user.name if user.name else "there"
    
    template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'jwt_email_template.html')
    html_content = render_to_string(template_path, {
        'name': display_name,  # Use smart display name
        'token_url': token_url
    })
    text_content = f'Hello {display_name}, please activate your account: {token_url}'

    email = EmailMultiAlternatives(
        subject='Activate your account',
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")

    # inline logo (cid:logo)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEBase('image', 'png')
            logo.set_payload(f.read())
            encoders.encode_base64(logo)
            logo.add_header('Content-ID', '<logo>')
            logo.add_header('Content-Disposition', 'inline', filename='logo.png')
            email.attach(logo)

    email.send()


class CleanerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CleanerRegistrationSerializer

    def post(self, request):
        serializer = CleanerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            cleaner = serializer.save()  # user.is_active = False set in serializer
            # TEMPORARILY DISABLED: Email sending causing timeout
            try:
                token_url = _build_activation_url(request, cleaner.user)
                _send_activation_email(cleaner.user, token_url)
            except Exception as e:
                return Response({"message": f"Error sending activation email: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"message": "Cleaner created successfully. Email verification disabled temporarily."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmployerRegistrationSerializer

    def post(self, request):
        serializer = EmployerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            employer = serializer.save()
            try:
                token_url = _build_activation_url(request, employer.user)
                _send_activation_email(employer.user, token_url)
            except Exception as e:
                return Response({"message": f"Error sending activation email: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"message": "Employer created. Check your email to activate the account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRegistrationView(APIView):
    permission_classes = [permissions.IsAdminUser]  # ✅ Only admins can create admin accounts
    serializer_class = AdminRegistrationSerializer

    def post(self, request):
        serializer = AdminRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            admin = serializer.save()
            try:
                token_url = _build_activation_url(request, admin.user)
                _send_activation_email(admin.user, token_url)
            except Exception as e:
                return Response({"message": f"Error sending activation email: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"message": "Admin created. Check your email to activate the account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class RoleManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]


    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return None

    def get(self, request, pk):
        role = self.get_object(pk)
        if not role:
            return Response({"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RoleSerializer(role).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        role = self.get_object(pk)
        if not role:
            return Response({"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        role = self.get_object(pk)
        if not role:
            return Response({"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND)
        role.delete()
        return Response({"message": "Role deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class ActivateUserView(APIView):
    """
    GET /api/users/activate/<uidb64>/<token>/
    - Secure, time-limited activation (fixes #1, #3)
    - Auto-login on success: sets HttpOnly refresh cookie and returns access (fixes #8)
    - Keeps custom flow (fixes #9)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token):
        # Decode user id
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({
                'detail': 'This activation link is invalid. Please contact support or register again.',
                'error_code': 'invalid_activation_link'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate token
        if not default_token_generator.check_token(user, token):
            return Response({
                'detail': 'This activation link has expired or is invalid. Please contact support to resend the activation email.',
                'error_code': 'expired_activation_token'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Activate if not already
        if not user.is_active:
            user.is_active = True
            user.save()

        # Auto-login: issue refresh/access and set cookie (HttpOnly)
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        resp = Response({
            'message': 'Account activated. You are now signed in.',
            'access': str(access),
        }, status=status.HTTP_200_OK)

        if HAVE_COOKIE_HELPER:
            set_refresh_cookie(resp, str(refresh))
        else:
            # Fallback: set cookie from settings
            resp.set_cookie(
                key=getattr(settings, "REFRESH_COOKIE_NAME", "refresh_token"),
                value=str(refresh),
                httponly=getattr(settings, "REFRESH_COOKIE_HTTPONLY", True),
                secure=getattr(settings, "REFRESH_COOKIE_SECURE", False),
                samesite=getattr(settings, "REFRESH_COOKIE_SAMESITE", "Lax"),
                path=getattr(settings, "REFRESH_COOKIE_PATH", "/auth/jwt"),
                max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            )
        return resp
