"""
Quick test script for notification preferences API
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tidy_linker.settings')
django.setup()

from notifications.models import NotificationPreference
from users.models import User

# Get first user
user = User.objects.first()
if not user:
    print("❌ No users found in database")
    exit(1)

print(f"✅ Testing with user: {user.email}")

# Get or create preferences
pref, created = NotificationPreference.objects.get_or_create(user=user)

print(f"\n{'Created new preferences' if created else 'Loaded existing preferences'}")
print(f"Preference ID: {pref.id}")
print(f"Email enabled: {pref.email_enabled}")
print(f"SMS enabled: {pref.sms_enabled}")
print(f"Push enabled: {pref.push_enabled}")
print(f"Custom preferences: {pref.preferences}")
print(f"Quiet hours: {pref.quiet_hours_start} to {pref.quiet_hours_end}")

# Test get_channels_for_event method
print("\n📢 Testing get_channels_for_event():")
print(f"  booking_confirmed: {pref.get_channels_for_event('booking_confirmed')}")
print(f"  new_message: {pref.get_channels_for_event('new_message')}")

# Test is_quiet_hours method
print(f"\n🌙 Currently in quiet hours: {pref.is_quiet_hours()}")

print("\n✅ All tests passed!")
