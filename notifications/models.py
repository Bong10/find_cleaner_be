from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class AlertType(models.TextChoices):
    INFO = "info", "info"
    SUCCESS = "success", "success"
    WARNING = "warning", "warning"
    ERROR = "error", "error"


class Category(models.TextChoices):
    MESSAGE = "message", "message"
    BOOKING = "booking", "booking"
    APPLICATION = "application", "application"
    SHORTLIST = "shortlist", "shortlist"
    PAYMENT = "payment", "payment"
    REVIEW = "review", "review"
    SYSTEM = "system", "system"


# In-App Notification (existing - for bell icon)
class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    verb = models.CharField(max_length=255)
    # New concise title + longer description
    title = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, null=True)

    # Alert meta
    alert_type = models.CharField(max_length=20, choices=AlertType.choices, default=AlertType.INFO)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SYSTEM)

    # Generic relation to the object that is the target of the action
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    target_object_id = models.PositiveIntegerField(blank=True, null=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    unread = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        if self.target:
            return f"{self.actor} {self.verb} {self.target}"
        return f"{self.actor} {self.verb}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'unread']),
        ]


# Multi-Channel Notification Log (new - for email/SMS/push tracking)
class NotificationLog(models.Model):
    """
    Tracks every notification sent via email, SMS, or push.
    This is separate from the in-app Notification model.
    """
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('delivered', 'Delivered'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_logs'
    )
    event_type = models.CharField(max_length=50, db_index=True)  # e.g., 'booking_confirmed'
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # Content
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Tracking (for emails)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Provider response (for debugging)
    provider_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.channel} - {self.event_type} to {self.user.email} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['status', 'created_at']),
        ]


# User Notification Preferences (new)
class NotificationPreference(models.Model):
    """
    Controls what types of notifications a user wants to receive and via which channels.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Global channel toggles
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    # Event-specific preferences (stored as JSON)
    # Example: {"booking_confirmed": ["email", "push"], "new_message": ["push", "in_app"]}
    preferences = models.JSONField(default=dict, blank=True)
    
    # Quiet hours (optional feature)
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="e.g., 22:00")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="e.g., 08:00")
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"

    def get_channels_for_event(self, event_type):
        """
        Returns list of channels user wants to receive for this event.
        Falls back to global defaults if event not configured.
        """
        # Check event-specific preferences
        if event_type in self.preferences:
            return self.preferences[event_type]
        
        # Default: send via enabled channels
        channels = []
        if self.email_enabled:
            channels.append('email')
        if self.push_enabled:
            channels.append('push')
        if self.sms_enabled:
            channels.append('sms')
        
        return channels

    def is_quiet_hours(self):
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        
        if start < end:
            return start <= now <= end
        else:  # Quiet hours span midnight
            return now >= start or now <= end

