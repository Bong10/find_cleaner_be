"""
Admin-only API endpoints for dashboard, statistics, and management.
"""
from django.urls import path
from .views_admin_stats import (
    admin_dashboard_stats,
    admin_user_reports,
    admin_jobs_reports,
    admin_security_reports,
)

urlpatterns = [
    # Dashboard stats
    path('stats/', admin_dashboard_stats, name='admin-dashboard-stats'),
    
    # Reports
    path('reports/users/', admin_user_reports, name='admin-user-reports'),
    path('reports/jobs/', admin_jobs_reports, name='admin-jobs-reports'),
    path('reports/security/', admin_security_reports, name='admin-security-reports'),
]
