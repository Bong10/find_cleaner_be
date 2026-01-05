import logging
import time
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from .rate_limit import check_password_reset_rate_limit, record_password_reset_attempt
from .password_serializers import PasswordResetConfirmSerializer

logger = logging.getLogger(__name__)


class CustomUserViewSet(DjoserUserViewSet):
    """
    Custom UserViewSet that extends Djoser's UserViewSet to add rate limiting
    to password reset requests and password history validation.
    """

    def get_serializer_class(self):
        """Override to use custom serializer for password reset confirmation."""
        if self.action == 'reset_password_confirm':
            return PasswordResetConfirmSerializer
        return super().get_serializer_class()

    @action(["post"], detail=False)
    def reset_password(self, request, *args, **kwargs):
        """
        Override reset_password to add rate limiting and retry logic.
        
        Rate limits:
        - 2 minutes cooldown per email
        - 5 requests per 15 minutes per IP address
        """
        # Get email from request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        
        # Check rate limit
        allowed, wait_seconds, message = check_password_reset_rate_limit(email, request)
        
        if not allowed:
            return Response(
                {
                    "detail": message,
                    "wait_seconds": wait_seconds,
                    "error_code": "rate_limit_exceeded"
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Attempt to send the email with retry logic
        max_retries = 3
        retry_delay = 1  # seconds
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = super().reset_password(request, *args, **kwargs)
                
                # Only record attempt if email sent successfully (status 2xx)
                if response.status_code >= 200 and response.status_code < 300:
                    record_password_reset_attempt(email, request)
                    
                    # Log successful send after retries
                    if attempt > 0:
                        logger.info(f"Password reset email sent for {email} after {attempt + 1} attempts")
                
                return response
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Check if it's a connection error that might benefit from retry
                if "Connection unexpectedly closed" in error_msg or "Connection refused" in error_msg or "10051" in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"Password reset email attempt {attempt + 1} failed for {email}: {error_msg}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue  # Retry
                    else:
                        logger.error(f"Password reset email failed for {email} after {max_retries} attempts: {error_msg}")
                else:
                    # Not a connection error, don't retry
                    logger.error(f"Password reset email failed for {email}: {error_msg}")
                    break
        
        # All retries failed or non-retryable error
        return Response(
            {
                "detail": "Unable to send password reset email due to a temporary connection issue. Please try again in a few moments.",
                "error_code": "email_send_failed",
                "technical_info": str(last_error) if last_error else "Unknown error"
            },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
