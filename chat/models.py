# chat/models.py
from django.db import models
from django.utils.timezone import now
from users.models import Employer, Cleaner
from job.models import JobBooking  # <— add
from django.contrib.auth import get_user_model

class Chat(models.Model):
    """Conversation between one cleaner and one employer (global/reusable)."""
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name='chats')
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE, related_name='chats')
    created_at = models.DateTimeField(default=now)

    # NEW: lifecycle and linkage
    is_active = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_reason = models.CharField(max_length=200, blank=True)
    last_booking = models.ForeignKey(
        JobBooking, null=True, blank=True, on_delete=models.SET_NULL, related_name='related_chat'
    )

    class Meta:
        unique_together = ('employer', 'cleaner')
        indexes = [
            models.Index(fields=['employer', 'cleaner']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Chat({self.pk}) E:{self.employer_id} ↔ C:{self.cleaner_id}"

    # Helpers
    def activate_for_booking(self, booking: JobBooking):
        self.is_active = True
        self.archived_at = None
        self.archived_reason = ""
        self.last_booking = booking
        self.save(update_fields=['is_active', 'archived_at', 'archived_reason', 'last_booking'])

    def archive(self, reason: str = "no active bookings"):
        from django.utils.timezone import now as _now
        self.is_active = False
        self.archived_at = _now()
        self.archived_reason = reason[:200]
        self.save(update_fields=['is_active', 'archived_at', 'archived_reason'])

    def other_user(self, current_user):
        if current_user == self.employer.user:
            return self.cleaner.user
        elif current_user == self.cleaner.user:
            return self.employer.user
        return None


class Message(models.Model):
    """ Message for a chat """
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=1, choices=[('e', 'Employer'), ('c', 'Cleaner')])
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='messages/', blank=True, null=True)
    sent_at = models.DateTimeField(default=now)
    is_read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False) 

    def __str__(self):
        return f"Message from {self.sender} in chat {self.chat.id}"

    def is_audio_or_video(self):
        if self.file:
            extension = self.file.name.split('.')[-1].lower()
            return extension in ['mp3', 'wav', 'mp4', 'mov', 'avi']
        return False

    class Meta:
        ordering=["-sent_at"]


class FlaggedChat(models.Model):
    """ The FlaggedChat model represents chat messages that have been reported for inappropriate or concerning content"""
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE)
    flagged_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    reason = models.TextField()
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)