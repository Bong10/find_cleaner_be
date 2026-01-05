from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    """
    Represents a conversation session between a user and the AI.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bot_sessions', null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True, help_text="UUID or unique identifier for guest sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Session {self.session_id} ({self.user})"

class ChatMessage(models.Model):
    """
    Individual messages in a session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'AI Assistant'),
        ('system', 'System'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
