"""
SMS provider implementation using Twilio.
"""
from django.conf import settings
from . import BaseNotificationProvider
import logging

logger = logging.getLogger(__name__)


class TwilioSMSProvider(BaseNotificationProvider):
    """
    Sends SMS via Twilio API.
    """
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio credentials not configured. SMS sending will be mocked.")
    
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send SMS via Twilio.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +237XXXXXXXXX)
            subject: Not used for SMS (kept for interface consistency)
            body: SMS text content (max 160 chars recommended)
        """
        if not all([self.account_sid, self.auth_token, self.from_number]):
            # Mock mode
            logger.info(f"[MOCK SMS] To: {to}, Body: {body[:50]}...")
            return {'success': True, 'message_id': 'mock-sms-id', 'mocked': True}
        
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            message = client.messages.create(
                to=to,
                from_=self.from_number,
                body=body
            )
            
            return {
                'success': True,
                'message_id': message.sid,
                'status': message.status
            }
            
        except Exception as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def get_sms_provider():
    """
    Returns the configured SMS provider.
    """
    return TwilioSMSProvider()
