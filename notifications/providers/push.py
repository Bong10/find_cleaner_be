"""
Push notification provider using Firebase Cloud Messaging (FCM) V1 API.
"""
from django.conf import settings
from . import BaseNotificationProvider
import logging
import os
import json

logger = logging.getLogger(__name__)


class FCMPushProvider(BaseNotificationProvider):
    """
    Sends push notifications via Firebase Cloud Messaging V1 API.
    Uses service account JSON for authentication (required for new Firebase projects).
    """
    
    def __init__(self):
        self.service_account_path = getattr(settings, 'FCM_SERVICE_ACCOUNT_PATH', None)
        self.project_id = None
        self.access_token = None
        
        if self.service_account_path and os.path.exists(self.service_account_path):
            try:
                with open(self.service_account_path, 'r') as f:
                    service_account = json.load(f)
                    self.project_id = service_account.get('project_id')
            except Exception as e:
                logger.error(f"Failed to load FCM service account: {e}")
        
        if not self.service_account_path:
            logger.warning("FCM_SERVICE_ACCOUNT_PATH not configured. Push notifications will be mocked.")
    
    def _get_access_token(self):
        """
        Get OAuth2 access token for FCM V1 API using service account.
        """
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            credentials.refresh(Request())
            return credentials.token
        except Exception as e:
            logger.error(f"Failed to get FCM access token: {e}")
            return None
    
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send push notification via FCM V1 API.
        
        Args:
            to: Device token (FCM registration token)
            subject: Notification title
            body: Notification body
            **kwargs: Optional data payload, badge count, etc.
        """
        if not self.service_account_path or not self.project_id:
            # Mock mode
            logger.info(f"[MOCK PUSH] To: {to[:20] if len(to) > 20 else to}..., Title: {subject}")
            return {'success': True, 'message_id': 'mock-push-id', 'mocked': True}
        
        try:
            import requests
            
            access_token = self._get_access_token()
            if not access_token:
                raise Exception("Failed to obtain FCM access token")
            
            url = f'https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'message': {
                    'token': to,
                    'notification': {
                        'title': subject,
                        'body': body,
                    },
                    'data': kwargs.get('data', {}),  # Custom data payload
                }
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message_id': response_data.get('name'),
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('error', {}).get('message', 'Unknown FCM error')
                }
            
        except Exception as e:
            logger.error(f"FCM push error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def get_push_provider():
    """
    Returns the configured push notification provider.
    """
    return FCMPushProvider()
