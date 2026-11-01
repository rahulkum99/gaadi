import logging

logger = logging.getLogger("accounts.audit")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def actor_label(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return "anon"
    return f"{user.pk}:{user.email}"
