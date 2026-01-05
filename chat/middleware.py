"""
WebSocket JWT Authentication Middleware

Authenticates WebSocket connections using JWT tokens passed as query parameters.
Usage: ws://localhost:8000/ws/chat/1/?token=<jwt_access_token>
"""

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs


@database_sync_to_async
def get_user_from_token(token_string):
    """Validate JWT token and return user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Validate token
        token = AccessToken(token_string)
        user_id = token.payload.get('user_id')
        
        if not user_id:
            return AnonymousUser()
        
        # Get user from database
        user = User.objects.get(id=user_id)
        return user
        
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections using JWT.
    
    Token can be passed via:
    1. Query parameter: ws://host/ws/chat/1/?token=<jwt>
    2. Subprotocol header (for browsers that support it)
    """
    
    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        token = None
        
        # Method 1: Token in query parameter
        if 'token' in query_params:
            token = query_params['token'][0]
        
        # Method 2: Token in subprotocols (Sec-WebSocket-Protocol header)
        # Format: "access_token, <actual_token>"
        subprotocols = scope.get('subprotocols', [])
        for proto in subprotocols:
            if proto.startswith('access_token.'):
                token = proto.replace('access_token.', '')
                break
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


class QueryAuthMiddleware(BaseMiddleware):
    """
    Simpler middleware that only checks query string.
    Use this if you don't need subprotocol auth.
    """
    
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        if 'token' in query_params:
            token = query_params['token'][0]
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
