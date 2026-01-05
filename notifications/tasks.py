"""
Celery tasks for sending notifications.
These run in the background, so your main app stays fast.
"""
from celery import shared_task
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
import logging

from .models import NotificationLog, NotificationPreference
from .providers.email import get_email_provider
from .providers.sms import get_sms_provider
from .providers.push import get_push_provider
from . import events

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, retry_backoff=True)
def send_email_notification(self, user_id, event_type, context, subject=None):
    """
    Send an email notification.
    
    Args:
        user_id: User to send to
        event_type: Event constant (e.g., events.BOOKING_CONFIRMED)
        context: Data for template rendering (dict)
        subject: Optional subject override
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check user preferences
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        if 'email' not in prefs.get_channels_for_event(event_type):
            logger.info(f"User {user.email} has disabled email for {event_type}")
            return {'skipped': True, 'reason': 'user_preference'}
        
        # Check quiet hours
        if prefs.is_quiet_hours():
            logger.info(f"Skipping notification during quiet hours for {user.email}")
            return {'skipped': True, 'reason': 'quiet_hours'}
        
        # Get subject from metadata or override
        if not subject:
            metadata = events.EVENT_METADATA.get(event_type, {})
            subject = metadata.get('subject', 'Notification from find-cleaner.com')
        
        # Render email template
        template_name = f'notifications/email/{event_type}.html'
        try:
            body = render_to_string(template_name, context)
        except Exception as e:
            logger.warning(f"Template {template_name} not found, using default")
            body = f"<p>{context.get('message', 'You have a new notification.')}</p>"
        
        # Create log entry
        log = NotificationLog.objects.create(
            user=user,
            event_type=event_type,
            channel='email',
            subject=subject,
            body=body,
            status='pending'
        )
        
        # Send via provider
        provider = get_email_provider()
        result = provider.send(
            to=user.email,
            subject=subject,
            body=body
        )
        
        # Update log
        if result.get('success'):
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.provider_response = result
        else:
            log.status = 'failed'
            log.failed_at = timezone.now()
            log.error_message = result.get('error', 'Unknown error')
        
        log.save()
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Email notification error: {str(e)}")
        raise  # Celery will retry


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, retry_backoff=True)
def send_sms_notification(self, user_id, event_type, message):
    """
    Send an SMS notification.
    
    Args:
        user_id: User to send to
        event_type: Event constant
        message: SMS text (keep under 160 chars)
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check if user has phone number
        if not user.phone_number:
            logger.warning(f"User {user.email} has no phone number")
            return {'skipped': True, 'reason': 'no_phone_number'}
        
        # Check user preferences
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        if 'sms' not in prefs.get_channels_for_event(event_type):
            return {'skipped': True, 'reason': 'user_preference'}
        
        # Create log entry
        log = NotificationLog.objects.create(
            user=user,
            event_type=event_type,
            channel='sms',
            body=message,
            status='pending'
        )
        
        # Send via provider
        provider = get_sms_provider()
        result = provider.send(
            to=str(user.phone_number),  # Convert PhoneNumber to string
            subject='',  # SMS doesn't use subject
            body=message
        )
        
        # Update log
        if result.get('success'):
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.provider_response = result
        else:
            log.status = 'failed'
            log.failed_at = timezone.now()
            log.error_message = result.get('error', 'Unknown error')
        
        log.save()
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"SMS notification error: {str(e)}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, retry_backoff=True)
def send_push_notification(self, user_id, event_type, title, body, data=None):
    """
    Send a push notification.
    
    Args:
        user_id: User to send to
        event_type: Event constant
        title: Notification title
        body: Notification body
        data: Optional custom data payload (dict)
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check user preferences
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        if 'push' not in prefs.get_channels_for_event(event_type):
            return {'skipped': True, 'reason': 'user_preference'}
        
        # TODO: You need to store device tokens somewhere
        # For now, we'll log this limitation
        # device_token = get_user_device_token(user)
        device_token = None
        
        if not device_token:
            logger.warning(f"User {user.email} has no device token registered")
            return {'skipped': True, 'reason': 'no_device_token'}
        
        # Create log entry
        log = NotificationLog.objects.create(
            user=user,
            event_type=event_type,
            channel='push',
            subject=title,
            body=body,
            status='pending'
        )
        
        # Send via provider
        provider = get_push_provider()
        result = provider.send(
            to=device_token,
            subject=title,
            body=body,
            data=data or {}
        )
        
        # Update log
        if result.get('success'):
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.provider_response = result
        else:
            log.status = 'failed'
            log.failed_at = timezone.now()
            log.error_message = result.get('error', 'Unknown error')
        
        log.save()
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Push notification error: {str(e)}")
        raise


@shared_task
def send_notification(user_id, event_type, context=None, channels=None):
    """
    Master task that sends a notification via multiple channels.
    
    Args:
        user_id: User to notify
        event_type: Event constant
        context: Data for rendering (dict)
        channels: List of channels ['email', 'sms', 'push'] or None for defaults
    """
    context = context or {}
    
    # Get user preferences if channels not specified
    if not channels:
        try:
            user = User.objects.get(id=user_id)
            prefs, _ = NotificationPreference.objects.get_or_create(user=user)
            channels = prefs.get_channels_for_event(event_type)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found")
            return
    
    # Dispatch to specific channel tasks
    results = {}
    
    if 'email' in channels:
        send_email_notification.delay(user_id, event_type, context)
        results['email'] = 'queued'
    
    if 'sms' in channels:
        message = context.get('sms_message', context.get('message', ''))
        if message:
            send_sms_notification.delay(user_id, event_type, message)
            results['sms'] = 'queued'
    
    if 'push' in channels:
        title = context.get('push_title', context.get('title', 'find-cleaner.com'))
        body = context.get('push_body', context.get('message', ''))
        if body:
            send_push_notification.delay(user_id, event_type, title, body, context.get('data'))
            results['push'] = 'queued'
    
    return results
