"""
Base provider interface for notification channels.
All providers (Email, SMS, Push) should inherit from this.
"""
from abc import ABC, abstractmethod


class BaseNotificationProvider(ABC):
    """
    Abstract base class for all notification providers.
    """
    
    @abstractmethod
    def send(self, to: str, subject: str, body: str, **kwargs):
        """
        Send a notification.
        
        Args:
            to: Recipient (email, phone, device token)
            subject: Subject/Title
            body: Message body
            **kwargs: Provider-specific options
            
        Returns:
            dict: Response with 'success' (bool) and optional 'message_id', 'error'
        """
        pass
