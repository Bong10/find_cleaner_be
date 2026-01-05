"""
Real-Time Chat WebSocket Consumer

Features:
- JWT Authentication
- Real-time messaging
- Typing indicators
- Read receipts
- Online/offline status
- Message delivery confirmation
- Connection rate limiting
"""

import json
import asyncio
from datetime import datetime
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import Message, Chat
from users.models import User


# Global connection tracking (per worker process)
# Limits connections to prevent file descriptor exhaustion on Windows
_user_connections = defaultdict(set)  # user_id -> set of channel names
_MAX_CONNECTIONS_PER_USER = 3  # Max WebSocket connections per user per endpoint type
_MAX_TOTAL_CONNECTIONS = 200  # Max total connections


def _get_total_connections():
    """Get total active connections."""
    return sum(len(channels) for channels in _user_connections.values())


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    
    Connect: ws://localhost:8000/ws/chat/<chat_id>/?token=<jwt_token>
    
    Message Types (send):
        - message: Send a chat message
        - typing: Indicate typing status
        - read: Mark messages as read
        - ping: Keep connection alive
    
    Message Types (receive):
        - chat_message: New message from other user
        - typing_indicator: Other user typing status
        - read_receipt: Messages marked as read
        - user_status: Online/offline status
        - message_sent: Confirmation of sent message
        - error: Error message
    """
    
    async def connect(self):
        """Handle WebSocket connection with rate limiting."""
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        self.user = self.scope.get('user', AnonymousUser())
        
        # Reject anonymous users
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4001)  # Authentication required
            return
        
        # Connection rate limiting - prevent file descriptor exhaustion
        user_key = f'chat_{self.user.id}'
        user_conns = _user_connections[user_key]
        
        # Check total connections limit
        if _get_total_connections() >= _MAX_TOTAL_CONNECTIONS:
            await self.close(code=4029)  # Too many connections globally
            return
        
        # Check per-user connection limit
        if len(user_conns) >= _MAX_CONNECTIONS_PER_USER:
            # Close oldest connection for this user to allow new one
            if user_conns:
                oldest = next(iter(user_conns))
                user_conns.discard(oldest)
        
        # Track this connection
        _user_connections[user_key].add(self.channel_name)
        
        # Verify user is participant of this chat
        is_participant = await self.verify_chat_participant()
        if not is_participant:
            _user_connections[user_key].discard(self.channel_name)
            await self.close(code=4003)  # Forbidden
            return
        
        # Join chat room group
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        
        # Join personal notification group (for cross-chat notifications)
        self.user_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user is online
        await self.broadcast_user_status(online=True)
        
        # Send unread message count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'chat_id': int(self.chat_id),
            'user_id': self.user.id,
            'unread_count': unread_count
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from connection tracking
        if hasattr(self, 'user') and self.user.is_authenticated:
            user_key = f'chat_{self.user.id}'
            _user_connections[user_key].discard(self.channel_name)
            # Clean up empty sets
            if not _user_connections[user_key]:
                _user_connections.pop(user_key, None)
        
        if hasattr(self, 'chat_group_name'):
            # Notify others that user is offline
            await self.broadcast_user_status(online=False)
            
            # Leave groups
            await self.channel_layer.group_discard(
                self.chat_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            handlers = {
                'message': self.handle_message,
                'typing': self.handle_typing,
                'read': self.handle_read_receipt,
                'ping': self.handle_ping,
            }
            
            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(str(e))

    # ==================== Message Handlers ====================

    async def handle_message(self, data):
        """Handle new chat message."""
        content = data.get('content', '').strip()
        
        if not content:
            await self.send_error("Message content is required")
            return
        
        # Create message in database
        message = await self.create_message(content)
        
        # Broadcast to chat group
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message_id': message['id'],
                'content': message['content'],
                'sender_id': message['sender_id'],
                'sender_name': message['sender_name'],
                'sender_role': message['sender_role'],
                'sent_at': message['sent_at'],
                'is_read': False
            }
        )
        
        # Send notification to other user if offline
        await self.send_push_notification(content)

    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.name or self.user.email,
                'is_typing': is_typing
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt - mark messages as read."""
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            # Mark all unread messages as read
            await self.mark_all_as_read()
        else:
            # Mark specific messages as read
            await self.mark_messages_as_read(message_ids)
        
        # Notify sender that messages were read
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'read_receipt',
                'user_id': self.user.id,
                'message_ids': message_ids,
                'read_at': timezone.now().isoformat()
            }
        )

    async def handle_ping(self, data):
        """Handle ping to keep connection alive."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))

    # ==================== Group Message Handlers ====================

    async def chat_message(self, event):
        """Receive message from group and send to WebSocket."""
        # Don't send own messages back (except for confirmation)
        if event['sender_id'] == self.user.id:
            # Send confirmation instead
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message_id': event['message_id'],
                'sent_at': event['sent_at']
            }))
        else:
            # Send new message from other user
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message_id': event['message_id'],
                'content': event['content'],
                'sender_id': event['sender_id'],
                'sender_name': event['sender_name'],
                'sender_role': event['sender_role'],
                'sent_at': event['sent_at'],
                'is_read': event.get('is_read', False)
            }))

    async def typing_indicator(self, event):
        """Receive typing indicator from group."""
        # Don't send own typing indicator back
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))

    async def read_receipt(self, event):
        """Receive read receipt from group."""
        # Don't send own read receipts back
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'user_id': event['user_id'],
                'message_ids': event['message_ids'],
                'read_at': event['read_at']
            }))

    async def user_status(self, event):
        """Receive user status update from group."""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'online': event['online'],
                'timestamp': event['timestamp']
            }))

    # ==================== Helper Methods ====================

    async def broadcast_user_status(self, online):
        """Broadcast user online/offline status to chat group."""
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'user_name': self.user.name or self.user.email,
                'online': online,
                'timestamp': timezone.now().isoformat()
            }
        )

    async def send_error(self, message):
        """Send error message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))

    async def send_push_notification(self, content):
        """Send push notification to other participant if offline."""
        # This integrates with your existing notification system
        try:
            other_user = await self.get_other_user()
            if other_user:
                from notifications.tasks import send_notification
                from notifications import events
                
                # Queue notification task
                await database_sync_to_async(send_notification.delay)(
                    user_id=other_user.id,
                    event_type=events.NEW_MESSAGE,
                    context={
                        'sender_name': self.user.name or self.user.email,
                        'message_preview': content[:100],
                        'chat_id': self.chat_id
                    }
                )
        except Exception as e:
            # Don't fail message send if notification fails
            pass

    # ==================== Database Operations ====================

    @database_sync_to_async
    def verify_chat_participant(self):
        """Verify current user is a participant in this chat."""
        try:
            chat = Chat.objects.select_related('employer__user', 'cleaner__user').get(id=self.chat_id)
            
            # Store chat info for later use
            self.chat = chat
            
            # Check if user is employer or cleaner in this chat
            if hasattr(self.user, 'employer') and self.user.employer:
                if chat.employer_id == self.user.employer.id:
                    self.sender_role = 'employer'
                    return True
            
            if hasattr(self.user, 'cleaner') and self.user.cleaner:
                if chat.cleaner_id == self.user.cleaner.id:
                    self.sender_role = 'cleaner'
                    return True
            
            return False
            
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, content):
        """Create a new message in the database."""
        sender_char = 'e' if self.sender_role == 'employer' else 'c'
        
        message = Message.objects.create(
            chat_id=self.chat_id,
            sender=sender_char,
            content=content
        )
        
        return {
            'id': message.id,
            'content': message.content,
            'sender_id': self.user.id,
            'sender_name': self.user.name or self.user.email,
            'sender_role': self.sender_role,
            'sent_at': message.sent_at.isoformat()
        }

    @database_sync_to_async
    def mark_all_as_read(self):
        """Mark all unread messages as read."""
        # Only mark messages sent by the OTHER user as read
        sender_to_mark = 'c' if self.sender_role == 'employer' else 'e'
        
        Message.objects.filter(
            chat_id=self.chat_id,
            sender=sender_to_mark,
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """Mark specific messages as read."""
        sender_to_mark = 'c' if self.sender_role == 'employer' else 'e'
        
        Message.objects.filter(
            id__in=message_ids,
            chat_id=self.chat_id,
            sender=sender_to_mark
        ).update(is_read=True)

    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread messages for current user."""
        sender_to_count = 'c' if self.sender_role == 'employer' else 'e'
        
        return Message.objects.filter(
            chat_id=self.chat_id,
            sender=sender_to_count,
            is_read=False
        ).count()

    @database_sync_to_async
    def get_other_user(self):
        """Get the other participant in this chat."""
        try:
            chat = Chat.objects.select_related('employer__user', 'cleaner__user').get(id=self.chat_id)
            
            if self.sender_role == 'employer':
                return chat.cleaner.user
            else:
                return chat.employer.user
        except:
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for global notifications (not chat-specific).
    
    Connect: ws://localhost:8000/ws/notifications/?token=<jwt_token>
    
    Broadcasts:
    - New message notifications (when not in chat)
    - System notifications
    - Status updates
    """
    
    async def connect(self):
        self.user = self.scope.get('user', AnonymousUser())
        
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Connection rate limiting - prevent file descriptor exhaustion
        user_key = f'notif_{self.user.id}'
        user_conns = _user_connections[user_key]
        
        # Check total connections limit
        if _get_total_connections() >= _MAX_TOTAL_CONNECTIONS:
            await self.close(code=4029)  # Too many connections globally
            return
        
        # Check per-user connection limit
        if len(user_conns) >= _MAX_CONNECTIONS_PER_USER:
            # Close oldest connection for this user
            if user_conns:
                oldest = next(iter(user_conns))
                user_conns.discard(oldest)
        
        # Track this connection
        _user_connections[user_key].add(self.channel_name)
        
        # Join user's personal notification group
        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'user_id': self.user.id
        }))

    async def disconnect(self, close_code):
        # Remove from connection tracking
        if hasattr(self, 'user') and self.user.is_authenticated:
            user_key = f'notif_{self.user.id}'
            _user_connections[user_key].discard(self.channel_name)
            if not _user_connections[user_key]:
                _user_connections.pop(user_key, None)
        
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages (ping/pong mainly)."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        except:
            pass

    async def notification(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event.get('title', ''),
            'message': event.get('message', ''),
            'category': event.get('category', 'system'),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))
