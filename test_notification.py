"""
Quick test script to verify notification system.
Run this with: python test_notification.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tidy_linker.settings')
django.setup()

from notifications.tasks import send_notification
from notifications import events
from django.contrib.auth import get_user_model

User = get_user_model()

# Get the first user (or create one for testing)
user = User.objects.first()

if not user:
    print("❌ No users found. Create a user first.")
    exit()

print(f"✅ Testing notification system for user: {user.email}")

# Send a test notification
result = send_notification.delay(
    user_id=user.id,
    event_type=events.BOOKING_CONFIRMED,
    context={
        'name': user.name or 'Test User',
        'service_name': 'Deep Clean',
        'booking_date': 'December 15, 2025',
        'booking_time': '10:00 AM',
        'cleaner_name': 'Sarah Johnson',
        'location': 'Cambridge, UK',
        'booking_url': 'https://find-cleaner.com/bookings/123',
    },
    channels=['email']  # Only email for now
)

print(f"📧 Notification queued! Task ID: {result.id}")
print("Check the Celery worker terminal to see it being processed.")
print("\nSince no API keys are configured, you'll see [MOCK EMAIL] logs.")
