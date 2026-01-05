from rest_framework import serializers
from .models import Notification, Category, NotificationPreference
from .utils import _compose_from_verb
from users.models import User
from job.models import Job
from chat.models import Chat

class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'role')

class TargetSerializer(serializers.RelatedField):
    def to_representation(self, value):
        if isinstance(value, Job):
            return {
                'id': value.job_id,
                'type': 'job',
                'title': value.title,
                'status': value.status,
            }
        if isinstance(value, Chat):
            other = value.other_user(self.context['request'].user)
            return {
                'id': value.id,
                'type': 'chat',
                'title': f"Chat with {getattr(other, 'name', 'Unknown')}"
            }
        # Add other target models here if needed
        return None

class NotificationSerializer(serializers.ModelSerializer):
    # Short, punchy title provided/stored on model
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    actor_name = serializers.CharField(source='actor.name', read_only=True)
    target = TargetSerializer(read_only=True)
    alert_type = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    # Convenience: normalized fields for FE labels
    category_label = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    target_ref = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id',
            'title',
            'description',
            'actor_name',
            'target',
            'target_ref',
            'alert_type',
            'category',
            'category_label',
            'type',
            'severity',
            'is_read',
            'unread',
            'created_at'
        )
        read_only_fields = fields

    def get_is_read(self, obj):
        return not obj.unread

    def get_category_label(self, obj):
        mapping = {
            'message': 'Message',
            'booking': 'Booking',
            'application': 'Application',
            'shortlist': 'Shortlist',
            'payment': 'Payment',
            'review': 'Review',
            'system': 'System',
        }
        cat = getattr(obj, 'category', '') or ''
        return mapping.get(cat, cat.capitalize() if cat else '')

    def get_type(self, obj):
        # Provide the friendly label for the UI Type column
        return self.get_category_label(obj)

    def get_severity(self, obj):
        # mirror alert_type for FE severity styling
        return getattr(obj, 'alert_type', '')

    def to_representation(self, obj):
        data = super().to_representation(obj)
        # Backwards-compat: fill missing fields for legacy rows
        if not data.get('title') or not data['title'].strip():
            title, desc, category, alert = _compose_from_verb(obj.actor, obj.verb, obj.target)
            data['title'] = title
            data['description'] = data.get('description') or (desc or '')
            data['category'] = data.get('category') or category
            data['alert_type'] = data.get('alert_type') or alert
        # Normalize payment-related items to booking confirmed wording
        v = (getattr(obj, 'verb', '') or '').lower()
        if 'payment' in v or 'has paid for the job' in v:
            title, desc, category, alert = _compose_from_verb(obj.actor, obj.verb, obj.target)
            data['title'] = title
            if desc:
                data['description'] = desc
            data['category'] = 'booking'
            data['alert_type'] = 'success'
        return data

    def get_target_ref(self, obj):
        t = getattr(obj, 'target', None)
        if isinstance(t, Job):
            return f"job:{t.job_id}"
        if isinstance(t, Chat):
            return f"chat:{t.id}"
        return None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'email_enabled',
            'sms_enabled',
            'push_enabled',
            'preferences',
            'quiet_hours_start',
            'quiet_hours_end',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']
    
    def validate_preferences(self, value):
        """Validate preferences JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Preferences must be a dictionary")
        
        # Valid event types
        valid_events = [
            'booking_confirmed',
            'booking_created',
            'application_accepted',
            'application_rejected',
            'payment_received',
            'new_message',
            'shortlist_added',
            'booking_completed',
            'new_review',
        ]
        
        # Valid channels
        valid_channels = ['email', 'sms', 'push', 'in_app']
        
        for event, channels in value.items():
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event type: {event}")
            if not isinstance(channels, list):
                raise serializers.ValidationError(f"Channels for {event} must be a list")
            for channel in channels:
                if channel not in valid_channels:
                    raise serializers.ValidationError(f"Invalid channel: {channel}")
        
        return value
