# chat/views.py

from django.db.models import Q, Max
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Chat, Message, FlaggedChat
from .serializers import (
    ChatSerializer,
    ChatDetailSerializers,
    MessageSerializer,
    FlaggedChatSerializer,
    FlagChatCreateSerializer,
)
from notifications.tasks import send_notification
from notifications import events


# ---------------------------
# Helpers
# ---------------------------

def _user_is_employer(user):
    return hasattr(user, "employer") and user.employer is not None


def _user_is_cleaner(user):
    return hasattr(user, "cleaner") and user.cleaner is not None


def _ensure_participant(user, chat: Chat):
    """Raise if user is not a participant of the chat."""
    if _user_is_employer(user) and chat.employer_id == user.employer.id:
        return
    if _user_is_cleaner(user) and chat.cleaner_id == user.cleaner.id:
        return
    raise PermissionDenied("You are not a participant of this chat.")


# ---------------------------
# Chats
# ---------------------------

class ChatViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
      - GET  /api/chats/                         -> my active chats (participant only)
      - GET  /api/chats/?include_archived=1      -> include archived
      - GET  /api/chats/{id}/                    -> retrieve (participant only)
      - POST /api/chats/                         -> create (rare; participant only)
      - POST /api/chats/{id}/archive/            -> archive manually (participant only)
      - GET  /api/chats/employer/{employer_id}/  -> all chats for that employer (participant or staff)
      - GET  /api/chats/cleaner/{cleaner_id}/    -> all chats for that cleaner (participant or staff)
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Chat.objects.select_related("employer", "cleaner", "last_booking")

    def get_serializer_class(self):
        # Use detail serializer for GET/RETRIEVE; base serializer for create/update
        if self.action in ["create", "update", "partial_update"]:
            return ChatSerializer
        return ChatDetailSerializers

    def get_queryset(self):
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived") == "1"

        # Admins see all chats
        if user.is_staff:
            queryset = self.queryset
        # Employers see their chats
        elif _user_is_employer(user):
            queryset = self.queryset.filter(employer_id=user.employer.id)
        # Cleaners see their chats
        elif _user_is_cleaner(user):
            queryset = self.queryset.filter(cleaner_id=user.cleaner.id)
        else:
            return Chat.objects.none()

        # Annotate each chat with the timestamp of its last message
        queryset = queryset.annotate(
            last_message_time=Max('messages__sent_at')
        ).order_by('-last_message_time') # Order by the most recent message first

        return queryset if include_archived else queryset.filter(is_active=True)

    def perform_create(self, serializer):
        """
        Allow creation only if the caller is one of the participants.
        (Normally chats are created/activated from the booking flow.)
        """
        user = self.request.user
        employer = serializer.validated_data.get("employer")
        cleaner = serializer.validated_data.get("cleaner")

        if _user_is_employer(user) and employer and employer.id == user.employer.id:
            serializer.save()
            return
        if _user_is_cleaner(user) and cleaner and cleaner.id == user.cleaner.id:
            serializer.save()
            return
        raise PermissionDenied("You can only create a chat you participate in.")

    def retrieve(self, request, *args, **kwargs):
        chat = self.get_object()
        # Allow admins to view any chat
        if not request.user.is_staff:
            _ensure_participant(request.user, chat)
        ser = self.get_serializer(chat)
        return Response(ser.data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        """Manually archive a chat (participant or admin)."""
        chat = self.get_object()
        # Allow admins to archive any chat
        if not request.user.is_staff:
            _ensure_participant(request.user, chat)
        reason = (request.data.get("reason") or "").strip() or "archived by participant"
        # Models should implement this; if not, set fields directly:
        if hasattr(chat, "archive"):
            chat.archive(reason=reason)
        else:
            chat.is_active = False
            if hasattr(chat, "archived_reason"):
                chat.archived_reason = reason
            chat.save(update_fields=["is_active"] + (["archived_reason"] if hasattr(chat, "archived_reason") else []))
        return Response({"detail": "Chat archived."}, status=200)

    @action(detail=False, methods=["get"], url_path=r"employer/(?P<employer_id>[^/.]+)")
    def employer_chats(self, request, employer_id=None):
        """List all chats for a specific employer. Restricted to that employer (or staff)."""
        if not request.user.is_staff:
            if not _user_is_employer(request.user) or str(request.user.employer.id) != str(employer_id):
                raise PermissionDenied("You can only view your own employer chats.")
        include_archived = request.query_params.get("include_archived") == "1"
        qs = self.queryset.filter(employer_id=employer_id)
        if not include_archived:
            qs = qs.filter(is_active=True)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path=r"cleaner/(?P<cleaner_id>[^/.]+)")
    def cleaner_chats(self, request, cleaner_id=None):
        """List all chats for a specific cleaner. Restricted to that cleaner (or staff)."""
        if not request.user.is_staff:
            if not _user_is_cleaner(request.user) or str(request.user.cleaner.id) != str(cleaner_id):
                raise PermissionDenied("You can only view your own cleaner chats.")
        include_archived = request.query_params.get("include_archived") == "1"
        qs = self.queryset.filter(cleaner_id=cleaner_id)
        if not include_archived:
            qs = qs.filter(is_active=True)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)


# ---------------------------
# Messages
# ---------------------------

class MessageViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
      - GET  /api/messages/                              -> my messages across all my chats
      - POST /api/messages/                              -> send message (blocked if chat archived)
      - GET  /api/messages/unread-count/                 -> total unread for my chats
      - GET  /api/messages/chat/{chat_id}/messages/      -> list messages of a chat (participant only)
      - POST /api/messages/{id}/mark-as-read/            -> mark a single message read
      - POST /api/messages/chat/{chat_id}/mark-all-read/ -> mark all messages in chat read
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.select_related("chat").order_by("sent_at")
    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        
        # Admins see all messages
        if u.is_staff:
            return qs
        
        # Employers see their chat messages
        if hasattr(u, "employer"):
            return qs.filter(chat__employer_id=u.employer.id)
        
        # Cleaners see their chat messages
        if hasattr(u, "cleaner"):
            return qs.filter(chat__cleaner_id=u.cleaner.id)
        
        return qs.none()

    def perform_create(self, serializer):
        chat = serializer.validated_data.get("chat")
        if not chat.is_active:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "This chat is archived. You cannot send new messages."})
        message = serializer.save()  # sender is set in serializer.create()
        
        # Determine recipient: if sender is employer, recipient is cleaner, and vice versa
        sender_user = self.request.user
        if message.sender == 'e':  # employer sent the message
            recipient_user = chat.cleaner.user
            sender_name = chat.employer.user.get_full_name() or chat.employer.user.username
            recipient_name = chat.cleaner.user.get_full_name() or chat.cleaner.user.username
        else:  # cleaner sent the message
            recipient_user = chat.employer.user
            sender_name = chat.cleaner.user.get_full_name() or chat.cleaner.user.username
            recipient_name = chat.employer.user.get_full_name() or chat.employer.user.username
        
        # ✅ BROADCAST MESSAGE TO WEBSOCKET GROUP (Real-time delivery)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "chat_message",
                "message_id": message.id,
                "content": message.content,
                "sender_id": sender_user.id,
                "sender_name": sender_name,
                "sender_role": message.sender,
                "sent_at": message.sent_at.isoformat(),
                "is_read": message.is_read
            }
        )
        
        # Multi-channel notification to recipient
        send_notification.delay(
            event_type=events.NEW_MESSAGE,
            user_id=recipient_user.id,
            context={
                'sender_name': sender_name,
                'recipient_name': recipient_name,
                'message_preview': message.content[:100] if len(message.content) > 100 else message.content,
                'chat_id': chat.id,
            }
        )

    @action(detail=False, methods=["get"], url_path=r"chat/(?P<chat_id>\d+)/messages")
    def get_chat_messages(self, request, chat_id=None):
        """Get all messages of a chat, ordered by sent_at (participant or admin)."""
        try:
            chat = Chat.objects.get(pk=chat_id)
        except Chat.DoesNotExist:
            raise NotFound("Chat not found.")
        # Allow admins to view any chat messages
        if not request.user.is_staff:
            _ensure_participant(request.user, chat)

        msgs = self.get_queryset().filter(chat_id=chat_id).order_by("sent_at")
        page = self.paginate_queryset(msgs)
        ser = self.get_serializer(page or msgs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """
        Return the count of unread messages in all chats the current user participates in.
        If your Message model has a 'sender' field, we exclude messages sent by the current user.
        """
        qs = self.get_queryset().filter(is_read=False)

        # If your Message has 'sender' field, try to exclude self-sent messages
        try:
            if _user_is_employer(request.user):
                qs = qs.exclude(sender="e")
            elif _user_is_cleaner(request.user):
                qs = qs.exclude(sender="c")
        except Exception:
            # If no 'sender' field exists, we just count all unread within user's chats.
            pass

        return Response({"unread_count": qs.count()})

    @action(detail=False, methods=["post"], url_path=r"chat/(?P<chat_id>[^/.]+)/mark-all-read")
    def mark_all_read(self, request, chat_id=None):
        """
        Marks all messages in a chat as read for the current user.
        """
        try:
            chat = Chat.objects.get(id=chat_id)
            user = request.user

            # Determine the sender type to filter messages NOT sent by the current user
            if hasattr(user, 'employer') and chat.employer == user.employer:
                sender_to_mark = 'c' # Mark messages from the cleaner
            elif hasattr(user, 'cleaner') and chat.cleaner == user.cleaner:
                sender_to_mark = 'e' # Mark messages from the employer
            else:
                # This case handles if the user is not part of the chat, though permissions should prevent this
                return Response({'detail': 'You are not a participant in this chat.'}, status=status.HTTP_403_FORBIDDEN)

            # Update messages sent by the OTHER party
            messages_to_update = chat.messages.filter(sender=sender_to_mark, is_read=False)
            count = messages_to_update.update(is_read=True)

            return Response({'detail': f'{count} messages marked as read.'}, status=status.HTTP_200_OK)
        except Chat.DoesNotExist:
            return Response({'detail': 'Chat not found.'}, status=status.HTTP_404_NOT_FOUND)


# ---------------------------
# Flagged / Moderation
# ---------------------------

class FlaggedChatViewSet(viewsets.ModelViewSet):
    """
    - POST /api/flagged-chats/           -> flag a chat/message (uses FlagChatCreateSerializer)
    - PATCH/PUT /api/flagged-chats/{id}/ -> resolve / add notes
    - GET /api/flagged-chats/?resolved=true|false
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = FlaggedChat.objects.select_related("chat", "flagged_by")
    serializer_class = FlaggedChatSerializer

    def create(self, request, *args, **kwargs):
        """Flag a chat (or message) and set chat.is_flagged=True."""
        ser = FlagChatCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        chat = ser.validated_data["chat"]
        chat.is_flagged = True
        chat.save(update_fields=["is_flagged"])

        flagged = ser.save(flagged_by=request.user)
        return Response(FlaggedChatSerializer(flagged).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Resolve or add resolution notes to a flagged chat."""
        flagged_chat = self.get_object()
        resolved = request.data.get("resolved", None)
        notes = request.data.get("resolution_notes", None)

        if resolved is not None:
            flagged_chat.resolved = bool(resolved in [True, "true", "True", 1, "1"])
        if notes is not None:
            flagged_chat.resolution_notes = notes

        flagged_chat.save()
        return Response(FlaggedChatSerializer(flagged_chat).data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        """List flagged chats; ?resolved=true|false is optional."""
        resolved = request.query_params.get("resolved")
        qs = self.get_queryset()
        if resolved is not None:
            want = resolved.lower() == "true"
            qs = qs.filter(resolved=want)
        page = self.paginate_queryset(qs)
        ser = FlaggedChatSerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)
