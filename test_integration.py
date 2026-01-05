"""
Quick verification script to test notification system integration.
Run this after starting the Celery worker to verify everything is connected properly.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tidy_linker.settings')
django.setup()

from notifications.tasks import send_notification
from notifications import events
from users.models import User

def test_notification_integration():
    """Test that notifications can be queued and processed."""
    
    print("\n" + "="*60)
    print("NOTIFICATION SYSTEM INTEGRATION TEST")
    print("="*60)
    
    # Check if any users exist
    users = User.objects.filter(is_active=True)
    if not users.exists():
        print("❌ No active users found. Cannot test notifications.")
        print("   Create at least one user first.")
        return
    
    # Use specific test email
    test_user = users.first()
    # Override email for testing
    original_email = test_user.email
    test_user.email = 'digitalweb079@gmail.com'
    test_user.save()
    
    user_display = getattr(test_user, 'username', None) or test_user.email or f"User {test_user.id}"
    print(f"\n✅ Found test user: {user_display} (ID: {test_user.id})")
    print(f"📧 Test emails will be sent to: {test_user.email}")
    
    # Test each integrated event
    events_to_test = [
        (events.BOOKING_CREATED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'booking_id': 'BK001',
        }),
        (events.BOOKING_CONFIRMED, {
            'employer_name': 'Jane Smith',
            'cleaner_name': 'John Doe',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'booking_id': 'BK001',
        }),
        (events.PAYMENT_RECEIVED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'booking_id': 'BK001',
            'amount': '150.00',
        }),
        (events.APPLICATION_ACCEPTED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'application_id': 'APP001',
        }),
        (events.APPLICATION_REJECTED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'application_id': 'APP001',
            'rejection_reason': 'Found someone with more experience',
        }),
        (events.SHORTLIST_ADDED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
        }),
        (events.BOOKING_COMPLETED, {
            'cleaner_name': 'John Doe',
            'employer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'booking_id': 'BK001',
        }),
        (events.NEW_REVIEW, {
            'recipient_name': 'John Doe',
            'reviewer_name': 'Jane Smith',
            'job_title': 'Deep Clean - 3 Bedroom House',
            'job_id': 'TEST001',
            'booking_id': 'BK001',
            'rating': 5,
            'comment': 'Excellent work! Very thorough and professional.',
        }),
        (events.NEW_MESSAGE, {
            'sender_name': 'Jane Smith',
            'recipient_name': 'John Doe',
            'message_preview': 'Hello, I have a question about the job requirements...',
            'chat_id': 1,
        }),
    ]
    
    print("\n" + "-"*60)
    print("QUEUEING TEST NOTIFICATIONS")
    print("-"*60)
    
    task_ids = []
    for event_type, context in events_to_test:
        try:
            result = send_notification.delay(
                user_id=test_user.id,
                event_type=event_type,
                context=context
            )
            task_ids.append((event_type, result.id))
            print(f"✅ {event_type:25s} - Task ID: {result.id}")
        except Exception as e:
            print(f"❌ {event_type:25s} - Error: {str(e)}")
    
    print("\n" + "-"*60)
    print("TEST NOTIFICATIONS QUEUED")
    print("-"*60)
    print(f"\n📊 Total tasks queued: {len(task_ids)}")
    print(f"👤 Test recipient: {test_user.email}")
    print("\n📝 Next steps:")
    print("   1. Check Celery worker logs for task processing")
    print("   2. Look for email output in console (mock mode)")
    print("   3. Query NotificationLog to see delivery status:")
    print("      python manage.py shell")
    print("      >>> from notifications.models import NotificationLog")
    print("      >>> NotificationLog.objects.all().order_by('-created_at')[:10]")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    test_notification_integration()
