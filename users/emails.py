from djoser.email import BaseEmailMessage
from djoser.conf import settings as djoser_settings
from djoser.utils import encode_uid
from django.contrib.auth.tokens import default_token_generator


class PasswordResetEmail(BaseEmailMessage):
    """Custom password reset email using Djoser's block-based template system."""

    template_name = "email/password_reset_email.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = context.get("user")

        # Build uid and token
        if user is not None:
            context["uid"] = encode_uid(user.pk)
            context["token"] = default_token_generator.make_token(user)
            
            # Use user's name field directly
            context["display_name"] = user.name if user.name else "there"

        # FORCE frontend domain and protocol from Djoser settings (override parent's values)
        proto = getattr(djoser_settings, "PROTOCOL", "http")
        domain = getattr(djoser_settings, "DOMAIN", "localhost:3000")
        path_template = getattr(djoser_settings, "PASSWORD_RESET_CONFIRM_URL", "reset-password/{uid}/{token}")
        
        # Override context to ensure frontend URL
        context["protocol"] = proto
        context["domain"] = domain
        
        try:
            path = path_template.format(**context)
        except Exception:
            path = f"reset-password/{context.get('uid','')}/{context.get('token','')}"
        
        context["url"] = f"{proto}://{domain}/{path.lstrip('/')}"
        
        # Ensure site_name is always set
        context["site_name"] = getattr(djoser_settings, "SITE_NAME", "Tidy Linker")
        
        return context
