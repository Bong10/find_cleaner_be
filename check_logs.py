"""
Check notification logs to see what actually happened.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tidy_linker.settings')
django.setup()

from notifications.models import NotificationLog
from django.db.models import Count

print("\n" + "="*60)
print("NOTIFICATION LOG DIAGNOSIS")
print("="*60)

# Count total logs
total = NotificationLog.objects.count()
print(f"\n📊 Total notification logs: {total}")

if total == 0:
    print("❌ No notification logs found!")
    print("   This means the email tasks never created log entries.")
    print("   Check if there are errors in Celery worker.")
else:
    # Count by status
    print("\n📈 Status breakdown:")
    status_counts = NotificationLog.objects.values('status').annotate(count=Count('id'))
    for item in status_counts:
        print(f"   {item['status']}: {item['count']}")
    
    # Show recent logs
    print("\n📧 Recent notification logs:")
    logs = NotificationLog.objects.all().order_by('-created_at')[:10]
    for log in logs:
        status_icon = "✅" if log.status == 'sent' else "❌"
        print(f"{status_icon} {log.event_type} -> {log.user.email}")
        print(f"   Status: {log.status}, Channel: {log.channel}")
        if log.status == 'failed':
            print(f"   Error: {log.error_message}")
        if log.provider_response:
            print(f"   Provider: {log.provider_response}")
        print()

print("="*60 + "\n")
