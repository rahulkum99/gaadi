from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LiveRateMixin:
    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class LoginRateThrottle(LiveRateMixin, AnonRateThrottle):
    scope = "login"


class AnonApiRateThrottle(LiveRateMixin, AnonRateThrottle):
    scope = "anon"


class UserApiRateThrottle(LiveRateMixin, UserRateThrottle):
    scope = "user"
