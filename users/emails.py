import re
from djoser.email import BaseEmailMessage
from djoser.conf import settings as djoser_settings
from djoser.utils import encode_uid
from django.contrib.auth.tokens import default_token_generator


def get_display_name(user):
    """
    Get a friendly display name for a user.
    Priority: user.name > parsed email > generic fallback
    """
    # First try user.name
    if hasattr(user, 'name') and user.name and user.name.strip():
        return user.name.strip()
    
    # Fallback to parsing email
    if user.email:
        email_username = user.email.split('@')[0]
        
        # If has separators (dots, underscores), split and capitalize
        if '.' in email_username or '_' in email_username:
            name = email_username.replace('.', ' ').replace('_', ' ').title()
            # Remove any trailing numbers
            name = re.sub(r'\d+$', '', name).strip()
            if name:
                return name
        
        # If no separators, check if it looks name-like
        # If it has numbers mixed in or is too long, use generic greeting
        if re.search(r'\d', email_username) or len(email_username) > 15:
            return "there"  # Results in "Hello there,"
        
        # Simple username without numbers - capitalize it
        return email_username.title()
    
    return "there"


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
            
            # Add friendly display name using smart parser
            context["display_name"] = get_display_name(user)

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
