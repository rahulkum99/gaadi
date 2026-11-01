import logging
import time

logger = logging.getLogger("gaadi.request")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            user = getattr(request, "user", None)
            user_label = (
                user.pk if user is not None and user.is_authenticated else "anon"
            )
            logger.info(
                "%s %s %s user=%s ip=%s %sms",
                request.method,
                request.get_full_path(),
                response.status_code,
                user_label,
                _client_ip(request),
                int((time.monotonic() - started) * 1000),
            )
        return response


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
