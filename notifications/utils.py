from .models import Notification, AlertType, Category
from django.contrib.contenttypes.models import ContentType

def _compose_from_verb(actor, verb: str, target):
    """Return (title, description, category, alert_type) for a given verb/target."""
    name = getattr(actor, 'name', getattr(actor, 'email', 'Someone'))
    t_title = getattr(target, 'title', None) if target else None

    # Defaults
    title = verb.capitalize()
    desc = None
    category = Category.SYSTEM
    alert = AlertType.INFO

    v = verb.lower().strip()
    if 'sent you a message' in v:
        title = 'New message'
        category = Category.MESSAGE
        alert = AlertType.INFO
        # Try to provide a preview from the chat target if no explicit description
        try:
            if target is not None and hasattr(target, 'messages'):
                last = target.messages.order_by('-sent_at').values_list('content', flat=True).first()
                if last:
                    preview = (last[:50] + '...') if len(last) > 50 else last
                    desc = f"{name} sent you a message: {preview}"
        except Exception:
            pass
    elif 'requested to book you for' in v:
        title = 'Booking request'
        category = Category.BOOKING
        alert = AlertType.INFO
        if t_title:
            desc = f"{name} requested to book you for '{t_title}'."
    elif 'confirmed your booking for' in v:
        title = 'Booking confirmed'
        category = Category.BOOKING
        alert = AlertType.SUCCESS
        if t_title:
            desc = f"{name} confirmed your booking for '{t_title}'."
    elif 'accepted your application for' in v:
        title = 'Application accepted'
        category = Category.APPLICATION
        alert = AlertType.SUCCESS
        if t_title:
            desc = f"{name} accepted your application for '{t_title}'."
    elif 'rejected your application for' in v:
        title = 'Application rejected'
        category = Category.APPLICATION
        alert = AlertType.WARNING
    elif 'shortlisted you for the job' in v:
        title = 'Shortlisted'
        category = Category.SHORTLIST
        alert = AlertType.INFO
    elif 'has paid for the job' in v or 'payment' in v:
        # Treat payment as booking confirmation completion
        title = 'Booking confirmed'
        category = Category.BOOKING
        alert = AlertType.SUCCESS
        if t_title:
            desc = f"Payment received for '{t_title}'."

    return title, desc, category, alert


def create_notification(recipient, actor, verb, target=None, description=None, *,
                        title: str | None = None,
                        category: str | None = None,
                        alert_type: str | None = None):
    """Create a notification with sensible defaults.

    - Keeps backward compatibility with existing calls (verb/target -> computed title/description/category/alert_type).
    - Callers may override via explicit title/category/alert_type if desired.
    """
    auto_title, auto_desc, auto_cat, auto_alert = _compose_from_verb(actor, verb, target)
    notification = Notification(
        recipient=recipient,
        actor=actor,
        verb=verb,
        title=title or auto_title,
        description=description or auto_desc,
        category=category or auto_cat,
        alert_type=alert_type or auto_alert,
    )
    if target:
        notification.target = target
    notification.save()
