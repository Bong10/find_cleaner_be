"""
Rate limiting utilities for password reset and other sensitive operations.
"""
from django.utils import timezone
from datetime import timedelta
from .models import PasswordResetAttempt, LoginAttempt


def get_client_ip(request):
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_password_reset_rate_limit(email, request, cooldown_minutes=2):
    """
    Check if password reset request should be allowed.
    
    Args:
        email: User's email address
        request: Django request object (to extract IP)
        cooldown_minutes: Minutes to wait between requests (default: 2)
    
    Returns:
        tuple: (allowed: bool, wait_seconds: int, message: str)
    """
    now = timezone.now()
    cooldown_delta = timedelta(minutes=cooldown_minutes)
    cutoff_time = now - cooldown_delta
    
    # Check recent attempts for this email
    recent_email_attempts = PasswordResetAttempt.objects.filter(
        email=email.lower(),
        attempted_at__gte=cutoff_time
    ).order_by('-attempted_at')
    
    if recent_email_attempts.exists():
        last_attempt = recent_email_attempts.first()
        time_since_last = (now - last_attempt.attempted_at).total_seconds()
        wait_seconds = int((cooldown_minutes * 60) - time_since_last)
        
        if wait_seconds > 0:
            minutes = wait_seconds // 60
            seconds = wait_seconds % 60
            
            if minutes > 0:
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"
                if seconds > 0:
                    time_str += f" and {seconds} second{'s' if seconds > 1 else ''}"
            else:
                time_str = f"{seconds} second{'s' if seconds > 1 else ''}"
            
            return (
                False,
                wait_seconds,
                f"Please wait for 2 minutes before requesting another password reset."
            )
    
    # Check IP-based rate limiting (more lenient: 5 requests per 15 minutes)
    ip_address = get_client_ip(request)
    if ip_address:
        ip_cutoff = now - timedelta(minutes=15)
        ip_attempts = PasswordResetAttempt.objects.filter(
            ip_address=ip_address,
            attempted_at__gte=ip_cutoff
        ).count()
        
        if ip_attempts >= 5:
            return (
                False,
                0,
                "Too many password reset requests from your location. Please try again later."
            )
    
    # All checks passed
    return (True, 0, "")


def record_password_reset_attempt(email, request):
    """Record a password reset attempt for rate limiting."""
    ip_address = get_client_ip(request)
    PasswordResetAttempt.objects.create(
        email=email.lower(),
        ip_address=ip_address
    )


def cleanup_old_attempts(days=7):
    """
    Clean up old password reset attempts (housekeeping).
    Call this periodically via cron or celery task.
    """
    cutoff = timezone.now() - timedelta(days=days)
    deleted_count = PasswordResetAttempt.objects.filter(
        attempted_at__lt=cutoff
    ).delete()[0]
    return deleted_count


def check_login_rate_limit(email, request, max_failed_attempts=5, lockout_minutes=15):
    """
    Check if login attempt should be allowed based on failed attempts.
    
    CRITICAL SECURITY: Prevents brute force password attacks.
    
    Args:
        email: User's email address (case-insensitive)
        request: Django request object (to extract IP)
        max_failed_attempts: Maximum failed attempts before lockout (default: 5)
        lockout_minutes: Minutes to lock out after max failures (default: 15)
    
    Returns:
        tuple: (allowed: bool, wait_seconds: int, message: str, remaining_attempts: int)
    """
    now = timezone.now()
    email = email.lower()
    lockout_cutoff = now - timedelta(minutes=lockout_minutes)
    
    # Count failed login attempts for this email in the lockout window
    failed_attempts = LoginAttempt.objects.filter(
        email=email,
        success=False,
        attempted_at__gte=lockout_cutoff
    ).count()
    
    # Check if account is locked out
    if failed_attempts >= max_failed_attempts:
        # Find the oldest failed attempt in the lockout window
        oldest_attempt = LoginAttempt.objects.filter(
            email=email,
            success=False,
            attempted_at__gte=lockout_cutoff
        ).order_by('attempted_at').first()
        
        if oldest_attempt:
            time_until_unlock = lockout_cutoff + timedelta(minutes=lockout_minutes) - now
            wait_seconds = max(0, int(time_until_unlock.total_seconds()))
            
            if wait_seconds > 0:
                minutes = wait_seconds // 60
                seconds = wait_seconds % 60
                
                if minutes > 0:
                    time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"
                else:
                    time_str = f"{seconds} second{'s' if seconds > 1 else ''}"
                
                return (
                    False,
                    wait_seconds,
                    f"Too many failed login attempts. Account locked for {lockout_minutes} minutes. Try again in {time_str}.",
                    0
                )
    
    # Check IP-based rate limiting (more aggressive: 10 attempts per 15 minutes per IP)
    ip_address = get_client_ip(request)
    if ip_address:
        ip_attempts_list = LoginAttempt.objects.filter(
            ip_address=ip_address,
            success=False,
            attempted_at__gte=lockout_cutoff
        ).order_by('attempted_at')
        
        if ip_attempts_list.count() >= 10:
            # Calculate time until the oldest attempt expires
            oldest_ip_attempt = ip_attempts_list.first()
            time_until_unlock = oldest_ip_attempt.attempted_at + timedelta(minutes=lockout_minutes) - now
            wait_seconds = max(0, int(time_until_unlock.total_seconds()))
            
            if wait_seconds > 0:
                minutes = wait_seconds // 60
                seconds = wait_seconds % 60
                
                if minutes > 0:
                    time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"
                else:
                    time_str = f"{seconds} second{'s' if seconds > 1 else ''}"
                
                return (
                    False,
                    wait_seconds,
                    f"Too many failed login attempts from your location. Please try again in {time_str}.",
                    0
                )
            
            return (
                False,
                0,
                "Too many failed login attempts from your location. Please try again later.",
                0
            )
    
    # Calculate remaining attempts
    remaining = max_failed_attempts - failed_attempts
    
    # All checks passed
    return (True, 0, "", remaining)


def record_login_attempt(email, request, success=False):
    """
    Record a login attempt for rate limiting and security auditing.
    
    Args:
        email: User's email address
        request: Django request object (to extract IP)
        success: Whether the login was successful
    """
    ip_address = get_client_ip(request)
    LoginAttempt.objects.create(
        email=email.lower(),
        ip_address=ip_address,
        success=success
    )
    
    # If login was successful, clear old failed attempts for this email
    # (give user a fresh start after successful login)
    if success:
        cutoff = timezone.now() - timedelta(minutes=15)
        LoginAttempt.objects.filter(
            email=email.lower(),
            success=False,
            attempted_at__lt=cutoff
        ).delete()


def cleanup_old_login_attempts(days=30):
    """
    Clean up old login attempts (housekeeping).
    Keep longer than password reset attempts for security auditing.
    Call this periodically via cron or celery task.
    """
    cutoff = timezone.now() - timedelta(days=days)
    deleted_count = LoginAttempt.objects.filter(
        attempted_at__lt=cutoff
    ).delete()[0]
    return deleted_count
