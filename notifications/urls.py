from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

# Custom URLs for preferences (singleton pattern - no pk required)
preference_list = NotificationPreferenceViewSet.as_view({
    'get': 'list',
    'patch': 'partial_update',
    'put': 'update',
})

preference_reset = NotificationPreferenceViewSet.as_view({
    'post': 'reset',
})

preference_events = NotificationPreferenceViewSet.as_view({
    'get': 'available_events',
})

urlpatterns = [
    path('', include(router.urls)),
    path('preferences/', preference_list, name='preference-detail'),
    path('preferences/reset/', preference_reset, name='preference-reset'),
    path('preferences/available-events/', preference_events, name='preference-events'),
]
