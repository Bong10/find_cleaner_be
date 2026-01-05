"""
Management command to clean up old password history entries.
Keeps only the configured number of most recent passwords per user.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import PasswordHistory, User


class Command(BaseCommand):
    help = 'Clean up old password history entries beyond the configured limit'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            type=int,
            default=None,
            help=f'Number of passwords to keep per user (default: {getattr(settings, "PASSWORD_HISTORY_COUNT", 5)})',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        keep_count = options['keep'] or getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)
        dry_run = options['dry_run']
        
        total_deleted = 0
        users_processed = 0
        
        # Get all users who have password history
        users_with_history = User.objects.filter(
            password_history__isnull=False
        ).distinct()
        
        self.stdout.write(f"Processing {users_with_history.count()} users with password history...")
        self.stdout.write(f"Keeping {keep_count} most recent passwords per user")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No deletions will be performed"))
        
        for user in users_with_history:
            # Get all password history for this user, ordered by newest first
            all_history = PasswordHistory.objects.filter(user=user).order_by('-created_at')
            
            # Count how many we have
            total_count = all_history.count()
            
            if total_count > keep_count:
                # Get IDs of entries to delete (everything beyond keep_count)
                to_delete = all_history[keep_count:]
                delete_count = to_delete.count()
                
                if dry_run:
                    self.stdout.write(
                        f"  Would delete {delete_count} old passwords for {user.email}"
                    )
                else:
                    # Delete the old entries
                    deleted_ids = list(to_delete.values_list('id', flat=True))
                    PasswordHistory.objects.filter(id__in=deleted_ids).delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Deleted {delete_count} old passwords for {user.email}"
                        )
                    )
                
                total_deleted += delete_count
                users_processed += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN: Would delete {total_deleted} password history entries for {users_processed} users"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {total_deleted} old password history entries for {users_processed} users"
                )
            )
        
        self.stdout.write(
            f"\nTotal password history entries remaining: {PasswordHistory.objects.count()}"
        )
