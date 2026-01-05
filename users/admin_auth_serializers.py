"""
Admin-only login endpoint.
Only users with is_staff=True can authenticate here.
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .rate_limit import check_login_rate_limit, record_login_attempt

User = get_user_model()


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Admin-only login serializer.
    Rejects non-admin users even if credentials are correct.
    """
    
    username_field = 'email'

    def validate(self, attrs):
        email = (attrs.get('email') or attrs.get('username') or '').strip()
        password = (attrs.get('password') or '').strip()

        if not email or not password:
            raise AuthenticationFailed(
                'Email and password are required.',
                code='missing_credentials'
            )

        # CRITICAL SECURITY: Check rate limiting BEFORE password validation
        request = self.context.get('request')
        allowed, wait_seconds, message, remaining = check_login_rate_limit(email, request)
        
        if not allowed:
            raise AuthenticationFailed(message, code='rate_limit_exceeded')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Record failed attempt
            record_login_attempt(email, request, success=False)
            raise AuthenticationFailed(
                'No account found with this email.',
                code='user_not_found'
            )

        if not user.is_active:
            record_login_attempt(email, request, success=False)
            raise AuthenticationFailed(
                'Your account is not active. Please check your email to activate.',
                code='inactive'
            )

        if not user.check_password(password):
            # Record failed password attempt
            record_login_attempt(email, request, success=False)
            
            # Warn user about remaining attempts
            if remaining <= 3 and remaining > 0:
                raise AuthenticationFailed(
                    f'Incorrect password. {remaining} attempt{"s" if remaining != 1 else ""} remaining before account lockout.',
                    code='bad_password'
                )
            else:
                raise AuthenticationFailed('Incorrect password.', code='bad_password')

        # ✅ ADMIN CHECK: Reject non-admin users (don't reveal this is admin endpoint)
        if not user.is_staff:
            # Don't record as failed attempt - credentials were correct
            raise AuthenticationFailed(
                'Invalid login credentials.',
                code='invalid_credentials'
            )

        # Record successful admin login
        record_login_attempt(email, request, success=True)

        # Issue tokens
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'name': getattr(user, 'name', None),
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'role': user.role.name if user.role else None,
            },
        }
        return data
