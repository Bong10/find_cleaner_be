"""
Notification event type constants.
Define all notification events here for consistency across the app.
"""

# Booking Events
BOOKING_CREATED = 'booking_created'
BOOKING_CONFIRMED = 'booking_confirmed'
BOOKING_CANCELLED = 'booking_cancelled'
BOOKING_COMPLETED = 'booking_completed'
BOOKING_REMINDER = 'booking_reminder'

# Application Events
APPLICATION_RECEIVED = 'application_received'
APPLICATION_ACCEPTED = 'application_accepted'
APPLICATION_REJECTED = 'application_rejected'

# Payment Events
PAYMENT_RECEIVED = 'payment_received'
PAYMENT_FAILED = 'payment_failed'
PAYOUT_PROCESSED = 'payout_processed'

# Message Events
NEW_MESSAGE = 'new_message'
MESSAGE_FLAGGED = 'message_flagged'

# Review Events
NEW_REVIEW = 'new_review'
REVIEW_RESPONSE = 'review_response'

# Account Events
ACCOUNT_VERIFIED = 'account_verified'
ACCOUNT_SUSPENDED = 'account_suspended'
PASSWORD_CHANGED = 'password_changed'
PROFILE_INCOMPLETE = 'profile_incomplete'

# Shortlist Events
SHORTLIST_ADDED = 'shortlist_added'

# System Events
SYSTEM_MAINTENANCE = 'system_maintenance'
FEATURE_ANNOUNCEMENT = 'feature_announcement'


# Event metadata (for templates and defaults)
EVENT_METADATA = {
    BOOKING_CONFIRMED: {
        'default_channels': ['email', 'push', 'in_app'],
        'subject': 'Booking Confirmed - find-cleaner.com',
        'priority': 'high',
    },
    NEW_MESSAGE: {
        'default_channels': ['push', 'in_app'],
        'subject': 'New Message',
        'priority': 'medium',
    },
    PAYMENT_RECEIVED: {
        'default_channels': ['email', 'in_app'],
        'subject': 'Payment Received - find-cleaner.com',
        'priority': 'high',
    },
    BOOKING_CREATED: {
        'default_channels': ['email', 'push', 'in_app'],
        'subject': 'New Booking Request - find-cleaner.com',
        'priority': 'high',
    },
    APPLICATION_ACCEPTED: {
        'default_channels': ['email', 'push', 'in_app'],
        'subject': 'Application Accepted - find-cleaner.com',
        'priority': 'high',
    },
    APPLICATION_REJECTED: {
        'default_channels': ['email', 'in_app'],
        'subject': 'Application Update - find-cleaner.com',
        'priority': 'medium',
    },
    SHORTLIST_ADDED: {
        'default_channels': ['push', 'in_app'],
        'subject': 'You\'ve been shortlisted!',
        'priority': 'medium',
    },
    BOOKING_COMPLETED: {
        'default_channels': ['email', 'in_app'],
        'subject': 'Job Completed - find-cleaner.com',
        'priority': 'medium',
    },
    NEW_REVIEW: {
        'default_channels': ['email', 'push', 'in_app'],
        'subject': 'New Review Received - find-cleaner.com',
        'priority': 'medium',
    },
}
