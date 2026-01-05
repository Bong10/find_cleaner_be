from notifications.utils import create_notification
from rest_framework import serializers
from .models import Chat,Message,FlaggedChat
from users.serializers import EmployerRegistrationSerializer, CleanerRegistrationSerializer
class ChatSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
 
    class Meta:
        model = Chat
        fields = ['id', 'employer', 'cleaner', 'created_at', 'last_message', 'unread_count']



    def get_last_message(self, obj):
        last_message = obj.messages.all().order_by('-sent_at').first()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if hasattr(user, 'employer') and obj.employer == user.employer:
            # Unread messages for an employer are sent by the cleaner ('c')
            return obj.messages.filter(sender='c', is_read=False).count()
        elif hasattr(user, 'cleaner') and obj.cleaner == user.cleaner:
            # Unread messages for a cleaner are sent by the employer ('e')
            return obj.messages.filter(sender='e', is_read=False).count()
        return 0

class ChatDetailSerializers(serializers.ModelSerializer):
    employer=EmployerRegistrationSerializer()
    cleaner=CleanerRegistrationSerializer()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    class Meta:
        model = Chat
        fields = ['id', 'employer', 'cleaner', 'created_at', 'last_message', 'unread_count']    

    def get_last_message(self, obj):
        last_message = obj.messages.all().order_by('-sent_at').first()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if hasattr(user, 'employer') and obj.employer == user.employer:
            # Unread messages for an employer are sent by the cleaner ('c')
            return obj.messages.filter(sender='c', is_read=False).count()
        elif hasattr(user, 'cleaner') and obj.cleaner == user.cleaner:
            # Unread messages for a cleaner are sent by the employer ('e')
            return obj.messages.filter(sender='e', is_read=False).count()
        return 0


class MessageSerializer(serializers.ModelSerializer):
    # client should NOT send this; we set it on the server
    sender = serializers.CharField(read_only=True)
    sender_id = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()

    # ensure chat is a valid pk and we can access it in create()
    chat = serializers.PrimaryKeyRelatedField(queryset=Chat.objects.all())

    class Meta:
        model = Message
        fields = ["id", "chat", "content", "sender", "sender_id", "sender_name", "is_read", "sent_at"]
        read_only_fields = ["id", "sender", "sender_id", "sender_name", "is_read", "sent_at"]

    def get_sender_id(self, obj):
        """Return the ID of the employer or cleaner who sent the message."""
        if obj.sender == 'e':
            return obj.chat.employer.id if obj.chat.employer else None
        elif obj.sender == 'c':
            return obj.chat.cleaner.id if obj.chat.cleaner else None
        return None

    def get_sender_name(self, obj):
        """Return the name of the sender."""
        if obj.sender == 'e':
            if obj.chat.employer and obj.chat.employer.user:
                return obj.chat.employer.user.name
        elif obj.sender == 'c':
            if obj.chat.cleaner and obj.chat.cleaner.user:
                return obj.chat.cleaner.user.name
        return None

    def create(self, validated_data):
        request = self.context["request"]
        chat = validated_data["chat"]

        # figure out who is sending
        if hasattr(request.user, "employer") and chat.employer_id == request.user.employer.id:
            sender = "e"
        elif hasattr(request.user, "cleaner") and chat.cleaner_id == request.user.cleaner.id:
            sender = "c"
        else:
            raise serializers.ValidationError({"detail": "You are not a participant of this chat."})

        if not chat.is_active:
            raise serializers.ValidationError({"detail": "This chat is archived. You cannot send new messages."})

        message = Message.objects.create(sender=sender, **validated_data)

        # Create a notification for the recipient
        if sender == 'e':
            recipient = chat.cleaner.user
        else:
            recipient = chat.employer.user

        create_notification(
            recipient=recipient,
            actor=request.user,
            verb="sent you a message",
            target=chat,
            description=message.content[:50] + '...' if len(message.content) > 50 else message.content
        )

        return message


class FlaggedChatSerializer(serializers.ModelSerializer):

    class Meta:
        model=FlaggedChat
        fields = ['id', 'chat', 'flagged_by','reason','resolved','resolution_notes','created_at']
        extra_kwargs = {
            'reason': {'required': True, 'allow_blank': False},
        }
    def validate_reason(self, value):
        """
        Validation for the reason field: Ensures the reason is not empty and has a minimum length.
        """
        if not value.strip():
            raise serializers.ValidationError("Reason cannot be empty.")
        if len(value) < 10:
            raise serializers.ValidationError("Reason must be at least 10 characters long.")
        return value

    def validate(self, attrs):
        """
        General validation to check for specific rules across fields.
        Example: Prevent the same user from flagging the same chat multiple times.
        """
        chat = attrs.get('chat')
        flagged_by = attrs.get('flagged_by')
        if FlaggedChat.objects.filter(chat=chat, flagged_by=flagged_by).exists():
            raise serializers.ValidationError("You have already flagged this chat.")
        return attrs

class FlagChatCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlaggedChat
        fields = ['chat', 'reason']
