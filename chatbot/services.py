import openai
from django.conf import settings
from .models import ChatSession, ChatMessage

# Placeholder for your AI Logic
# You will need to install: pip install openai

class AIService:
    def __init__(self):
        # Ensure you have OPENAI_API_KEY in your settings.py
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.api_key:
            openai.api_key = self.api_key

    def generate_response(self, session_id, user_message_text):
        """
        Core logic to call AI provider and get response.
        """
        # 1. Retrieve or create session
        session = ChatSession.objects.filter(session_id=session_id).first()
        if not session:
            # In a real app, you might want to handle this differently
            raise ValueError("Session not found")

        # 2. Save User Message
        ChatMessage.objects.create(session=session, role='user', content=user_message_text)

        # 3. Build Context (History)
        # Limit to last 10 messages to save tokens
        # Get last 10 messages (newest first), then reverse to chronological order
        history = reversed(session.messages.order_by('-created_at')[:10])
        messages_payload = [
            {"role": "system", "content": "You are TidyLinker Bot, a helpful assistant for a cleaning service platform."}
        ]
        
        for msg in history:
            messages_payload.append({"role": msg.role, "content": msg.content})

        # 4. Call AI (Mocked if no key)
        if not self.api_key:
            ai_response_text = "I am a sophisticated bot, but I need an OPENAI_API_KEY in settings to function really well!"
        else:
            try:
                # Using new OpenAI Client pattern (v1.0+)
                client = openai.OpenAI(api_key=self.api_key)
                completion = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages_payload
                )
                ai_response_text = completion.choices[0].message.content
            except openai.RateLimitError:
                ai_response_text = "I apologize, but I'm currently unable to process requests due to quota limits. Please contact the administrator."
            except openai.APIError as e:
                ai_response_text = "I'm having trouble connecting to my brain right now. Please try again later."
                print(f"OpenAI API Error: {e}") # Log the real error
            except Exception as e:
                ai_response_text = "An unexpected error occurred. Please try again."
                print(f"Chatbot Error: {e}") # Log the real error

        # 5. Save AI Response
        ChatMessage.objects.create(session=session, role='assistant', content=ai_response_text)

        return ai_response_text
