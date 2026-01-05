"""
Admin dashboard statistics and analytics endpoints.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from job.models import Job
from services.models import Service

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    """
    GET /api/admin/stats/
    
    Returns overview statistics for admin dashboard:
    - Total cleaners
    - Total employers
    - Total services
    - Active jobs
    """
    from users.models import Cleaner, Employer
    
    stats = {
        'total_cleaners': Cleaner.objects.count(),
        'total_employers': Employer.objects.count(),
        'total_services': Service.objects.count(),
        'active_jobs': Job.objects.filter(status='open').count(),
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_user_reports(request):
    """
    GET /api/admin/reports/users/
    
    Returns user growth and activity statistics.
    """
    from users.models import Cleaner, Employer
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    
    data = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'new_users_last_30_days': User.objects.filter(date_joined__gte=last_30_days).count(),
        'cleaners': {
            'total': Cleaner.objects.count(),
            'verified': Cleaner.objects.filter(profile_completed=True).count(),
            'unverified': Cleaner.objects.filter(profile_completed=False).count(),
        },
        'employers': {
            'total': Employer.objects.count(),
            'active': Employer.objects.filter(user__is_active=True).count(),
        }
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_jobs_reports(request):
    """
    GET /api/admin/reports/jobs/
    
    Returns job statistics and trends.
    """
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    
    data = {
        'total_jobs': Job.objects.count(),
        'jobs_by_status': {
            'open': Job.objects.filter(status='open').count(),
            'in_progress': Job.objects.filter(status='in_progress').count(),
            'completed': Job.objects.filter(status='completed').count(),
            'cancelled': Job.objects.filter(status='cancelled').count(),
        },
        'jobs_created_last_30_days': Job.objects.filter(created_at__gte=last_30_days).count(),
        'most_requested_services': list(
            Job.objects.values('services__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_security_reports(request):
    """
    GET /api/admin/reports/security/
    
    Returns security monitoring data (login attempts, failed logins, etc.)
    """
    from users.models import LoginAttempt
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    
    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)
    last_7_days = now - timedelta(days=7)
    
    # Recent failed login attempts
    failed_attempts_24h = LoginAttempt.objects.filter(
        success=False,
        attempted_at__gte=last_24_hours
    ).count()
    
    # Top suspicious IPs (multiple failed attempts)
    suspicious_ips = list(
        LoginAttempt.objects.filter(
            success=False,
            attempted_at__gte=last_7_days
        ).values('ip_address')
        .annotate(failed_count=Count('id'))
        .filter(failed_count__gte=5)
        .order_by('-failed_count')[:10]
    )
    
    # Accounts with multiple failed login attempts
    targeted_accounts = list(
        LoginAttempt.objects.filter(
            success=False,
            attempted_at__gte=last_7_days
        ).values('email')
        .annotate(failed_count=Count('id'))
        .filter(failed_count__gte=3)
        .order_by('-failed_count')[:10]
    )
    
    data = {
        'failed_logins_last_24h': failed_attempts_24h,
        'total_login_attempts_last_7_days': LoginAttempt.objects.filter(
            attempted_at__gte=last_7_days
        ).count(),
        'successful_logins_last_7_days': LoginAttempt.objects.filter(
            success=True,
            attempted_at__gte=last_7_days
        ).count(),
        'suspicious_ips': suspicious_ips,
        'targeted_accounts': targeted_accounts,
    }
    
    return Response(data)
