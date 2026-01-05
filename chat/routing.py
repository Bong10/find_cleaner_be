from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Chat WebSocket - for real-time messaging in a specific chat
    re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Notifications WebSocket - for global real-time notifications
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
