from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer
from .services import AIService
import uuid

class ChatbotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for the AI Chatbot.
    """
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [AllowAny] # Adjust as needed

    def get_queryset(self):
        # Users only see their own sessions
        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(user=self.request.user)
        # For anonymous users, we might rely on session_id passed in query params
        # But for security, let's just return empty or handle via session key
        return ChatSession.objects.none()

    @action(detail=False, methods=['post'])
    def start_session(self, request):
        """
        Initialize a new chat session.
        """
        session_id = str(uuid.uuid4())
        user = request.user if request.user.is_authenticated else None
        session = ChatSession.objects.create(session_id=session_id, user=user)
        return Response({'session_id': session.session_id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """
        Send a message to the bot and get a response.
        Payload: { "session_id": "...", "message": "..." }
        """
        session_id = request.data.get('session_id')
        message_text = request.data.get('message')

        if not session_id or not message_text:
            return Response({"error": "session_id and message are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify session exists
        session = ChatSession.objects.filter(session_id=session_id).first()
        if not session:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # Call AI Service
        ai_service = AIService()
        response_text = ai_service.generate_response(session_id, message_text)

        return Response({
            "response": response_text,
            "session_id": session_id
        })
