from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer

class NotificationViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the notifications
        for the currently authenticated user.
        """
        return self.request.user.notifications.all()

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Returns the count of unread notifications for the current user.
        """
        count = self.get_queryset().filter(unread=True).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Marks all unread notifications for the current user as read.
        """
        self.get_queryset().filter(unread=True).update(unread=False)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Marks a single notification as read.
        """
        notification = self.get_object()
        notification.unread = False
        notification.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """Delete multiple notifications by ids for the current user.

        Body: {"ids": [1,2,3]}
        """
        ids = request.data.get('ids') or []
        if not isinstance(ids, list):
            return Response({'detail': 'ids must be a list'}, status=400)
        qs = self.get_queryset().filter(id__in=ids)
        deleted, _ = qs.delete()
        return Response({'deleted': deleted}, status=200)

    @action(detail=False, methods=['delete'], url_path='delete-read')
    def delete_read(self, request):
        """Delete all read notifications for current user."""
        qs = self.get_queryset().filter(unread=False)
        deleted, _ = qs.delete()
        return Response({'deleted': deleted}, status=200)

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        """Delete all notifications for current user."""
        qs = self.get_queryset()
        deleted, _ = qs.delete()
        return Response({'deleted': deleted}, status=200)


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user notification preferences.
    
    Endpoints:
    - GET /api/preferences/ - Get current user's preferences (auto-creates if not exists)
    - PATCH /api/preferences/ - Update preferences
    - PUT /api/preferences/ - Replace preferences
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create preferences for current user"""
        pref, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return pref
    
    def list(self, request):
        """GET /api/preferences/ - Return current user's preferences"""
        pref = self.get_object()
        serializer = NotificationPreferenceSerializer(pref)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        """PATCH /api/preferences/ - Partial update"""
        instance = self.get_object()
        serializer = NotificationPreferenceSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /api/preferences/ - Full update"""
        instance = self.get_object()
        serializer = NotificationPreferenceSerializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='reset')
    def reset(self, request):
        """POST /api/preferences/reset/ - Reset to defaults"""
        pref = self.get_object()
        pref.email_enabled = True
        pref.sms_enabled = False
        pref.push_enabled = True
        pref.preferences = {}
        pref.quiet_hours_start = None
        pref.quiet_hours_end = None
        pref.save()
        
        serializer = self.get_serializer(pref)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='available-events')
    def available_events(self, request):
        """GET /api/preferences/available-events/ - List all notification event types"""
        events = [
            {
                'key': 'booking_confirmed',
                'label': 'Booking Confirmed',
                'description': 'When a booking is confirmed',
                'category': 'booking',
            },
            {
                'key': 'booking_created',
                'label': 'New Booking',
                'description': 'When someone creates a new booking',
                'category': 'booking',
            },
            {
                'key': 'application_accepted',
                'label': 'Application Accepted',
                'description': 'When your job application is accepted',
                'category': 'application',
            },
            {
                'key': 'application_rejected',
                'label': 'Application Rejected',
                'description': 'When your job application is rejected',
                'category': 'application',
            },
            {
                'key': 'payment_received',
                'label': 'Payment Received',
                'description': 'When payment is received for a job',
                'category': 'payment',
            },
            {
                'key': 'new_message',
                'label': 'New Message',
                'description': 'When you receive a new chat message',
                'category': 'message',
            },
            {
                'key': 'shortlist_added',
                'label': 'Added to Shortlist',
                'description': 'When you are added to a job shortlist',
                'category': 'shortlist',
            },
            {
                'key': 'booking_completed',
                'label': 'Booking Completed',
                'description': 'When a booking is marked as completed',
                'category': 'booking',
            },
            {
                'key': 'new_review',
                'label': 'New Review',
                'description': 'When someone leaves you a review',
                'category': 'review',
            },
        ]
        return Response({'events': events})

