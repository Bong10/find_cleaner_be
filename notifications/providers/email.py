"""
Email provider implementation using SendGrid.
Can be swapped for SMTP or other providers.
"""
from django.conf import settings
from . import BaseNotificationProvider
import logging

logger = logging.getLogger(__name__)


class SendGridEmailProvider(BaseNotificationProvider):
    """
    Sends emails via SendGrid API.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@find-cleaner.com')
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not configured. Email sending will be mocked.")
    
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send email via SendGrid.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: HTML or plain text body
            **kwargs: Optional params like 'from_email', 'reply_to'
        """
        if not self.api_key:
            # Mock mode (for development)
            logger.info(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
            return {'success': True, 'message_id': 'mock-id', 'mocked': True}
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=kwargs.get('from_email', self.from_email),
                to_emails=to,
                subject=subject,
                html_content=body
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id'),
                'status_code': response.status_code
            }
            
        except Exception as e:
            logger.error(f"SendGrid error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class BrevoEmailProvider(BaseNotificationProvider):
    """
    Sends emails via Brevo (formerly Sendinblue) API.
    Free tier: 300 emails/day
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'BREVO_API_KEY', None)
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@find-cleaner.com')
        
        if not self.api_key:
            logger.warning("BREVO_API_KEY not configured. Email sending will be mocked.")
    
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send email via Brevo API.
        """
        if not self.api_key:
            # Mock mode
            logger.info(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
            return {'success': True, 'message_id': 'mock-brevo-id', 'mocked': True}
        
        try:
            import requests
            
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": self.api_key,
                "content-type": "application/json"
            }
            
            payload = {
                "sender": {
                    "name": "find-cleaner.com",
                    "email": kwargs.get('from_email', self.from_email)
                },
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": body
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                'success': True,
                'message_id': data.get('messageId'),
                'status_code': response.status_code
            }
            
        except Exception as e:
            logger.error(f"Brevo error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class SMTPEmailProvider(BaseNotificationProvider):
    """
    Alternative email provider using Django's built-in SMTP.
    """
    
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send email via Django's SMTP backend.
        """
        try:
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message='',  # Plain text fallback
                html_message=body,
                from_email=kwargs.get('from_email', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[to],
                fail_silently=False,
            )
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Factory function to get configured provider
def get_email_provider():
    """
    Returns the configured email provider based on settings.
    """
    provider_name = getattr(settings, 'EMAIL_PROVIDER', 'brevo')
    
    if provider_name == 'brevo':
        return BrevoEmailProvider()
    elif provider_name == 'sendgrid':
        return SendGridEmailProvider()
    elif provider_name == 'smtp':
        return SMTPEmailProvider()
    else:
        logger.warning(f"Unknown email provider: {provider_name}. Using Brevo.")
        return BrevoEmailProvider()
