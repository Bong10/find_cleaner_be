"""
Management command to clean up old password reset attempts.
Usage: python manage.py cleanup_reset_attempts [--days 7]
"""
from django.core.management.base import BaseCommand
from users.rate_limit import cleanup_old_attempts


class Command(BaseCommand):
    help = 'Clean up old password reset attempts from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete attempts older than this many days (default: 7)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL attempts (use for testing/reset)'
        )

    def handle(self, *args, **options):
        if options['all']:
            from users.models import PasswordResetAttempt
            count = PasswordResetAttempt.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'Deleted ALL {count} password reset attempts')
            )
        else:
            days = options['days']
            count = cleanup_old_attempts(days=days)
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {count} password reset attempts older than {days} days')
            )
